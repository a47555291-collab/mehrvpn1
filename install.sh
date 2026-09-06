#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
APP=mehrvpn1
ROOT=/opt/$APP
DATA=/var/lib/$APP
RUN=/run/$APP
REPO_TARBALL='https://github.com/a47555291-collab/mehrvpn1/archive/refs/heads/main.tar.gz'

log(){ printf '[%s] %s\n' "$APP" "$*" >&2; }
die(){ log "ERROR: $*"; exit 1; }
trap 'die "installation failed at line $LINENO"' ERR

[[ $EUID -eq 0 ]] || die 'Run this installer as root.'
[[ -c /dev/net/tun ]] || die '/dev/net/tun is missing. Enable TUN in your VPS.'
. /etc/os-release
case "$ID:$VERSION_ID" in
  ubuntu:22.04|ubuntu:24.04|debian:12|debian:13) ;;
  *) die "Unsupported OS: $ID $VERSION_ID" ;;
esac

DOMAIN="${MEHRVPN1_DOMAIN:-}"
EMAIL="${MEHRVPN1_EMAIL:-}"
if [[ -z "$DOMAIN" ]]; then
  read -r -p 'Panel domain (leave empty for IP/HTTP): ' DOMAIN
fi
if [[ -n "$DOMAIN" && -z "$EMAIL" ]]; then
  read -r -p 'LetsEncrypt email: ' EMAIL
fi
VPN_REMOTE="${MEHRVPN1_VPN_REMOTE:-$DOMAIN}"
if [[ -z "$VPN_REMOTE" ]]; then
  VPN_REMOTE="$(curl -4fsS --max-time 10 https://api.ipify.org || true)"
fi
[[ -n "$VPN_REMOTE" ]] || die 'Could not determine server public IPv4. Set MEHRVPN1_VPN_REMOTE=... and retry.'

export DEBIAN_FRONTEND=noninteractive
log 'Installing system packages...'
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx openvpn easy-rsa iptables iptables-persistent curl ca-certificates openssl
if [[ -n "$DOMAIN" ]]; then
  apt-get install -y certbot python3-certbot-nginx
fi

id mehrvpn >/dev/null 2>&1 || useradd --system --home /var/lib/mehrvpn1 --shell /usr/sbin/nologin mehrvpn
install -d -o mehrvpn -g mehrvpn -m 0750 "$DATA" "$DATA/clients"
install -d -o root -g mehrvpn -m 0770 "$RUN"

SRC=$(mktemp -d /tmp/mehrvpn1.XXXXXX)
trap 'rm -rf "$SRC"' EXIT
log 'Downloading repository...'
curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 "$REPO_TARBALL" -o "$SRC/source.tar.gz"
tar -xzf "$SRC/source.tar.gz" -C "$SRC"
SRC_TREE=$(find "$SRC" -mindepth 1 -maxdepth 1 -type d -name 'mehrvpn1-*' -print -quit)
[[ -n "$SRC_TREE" && -d "$SRC_TREE/panel" && -f "$SRC_TREE/requirements.txt" ]] || die 'Downloaded repository is invalid.'
rm -rf "$ROOT"
install -d "$ROOT"
cp -a "$SRC_TREE/." "$ROOT/"
chown -R root:root "$ROOT"
chmod 0755 "$ROOT/install.sh" "$ROOT/scripts/provision-openvpn.sh"

log 'Installing Python dependencies...'
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install --upgrade pip >/dev/null
"$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"

log 'Provisioning OpenVPN...'
VPN_REMOTE="$VPN_REMOTE" "$ROOT/scripts/provision-openvpn.sh"

log 'Creating admin account...'
if [[ ! -f /root/.mehrvpn1-admin ]]; then
  ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9_@#%+=' | head -c 24)"
  [[ ${#ADMIN_PASSWORD} -ge 16 ]] || ADMIN_PASSWORD="$(openssl rand -hex 16)"
  export MEHRVPN1_SESSION_SECURE=false
  "$ROOT/.venv/bin/python" - <<PY
import time
from panel.db import init_db, db
from panel.auth import hash_password
init_db()
with db() as c:
    if not c.execute('SELECT 1 FROM users WHERE username=?', ('admin',)).fetchone():
        c.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)', ('admin', hash_password('''$ADMIN_PASSWORD'''), 'admin', int(time.time())))
PY
  umask 077
  printf 'username=admin\npassword=%s\n' "$ADMIN_PASSWORD" > /root/.mehrvpn1-admin
fi

log 'Installing systemd services...'
cp "$ROOT/systemd/mehrvpn1-web.service" /etc/systemd/system/
cp "$ROOT/systemd/mehrvpn1-agent.service" /etc/systemd/system/

log 'Configuring nginx...'
cat > /etc/nginx/sites-available/mehrvpn1 <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN:-_};
    client_max_body_size 2m;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
ln -sfn /etc/nginx/sites-available/mehrvpn1 /etc/nginx/sites-enabled/mehrvpn1
rm -f /etc/nginx/sites-enabled/default
nginx -t

systemctl daemon-reload
systemctl enable --now mehrvpn1-agent.service
systemctl enable --now mehrvpn1-web.service
systemctl restart mehrvpn1-web.service
systemctl restart nginx

if [[ -n "$DOMAIN" ]]; then
  log 'Requesting HTTPS certificate...'
  certbot --nginx --non-interactive --agree-tos --redirect -m "$EMAIL" -d "$DOMAIN"
  systemctl reload nginx
fi

if [[ -f /root/.mehrvpn1-admin ]]; then
  ADMIN_PASSWORD="$(sed -n 's/^password=//p' /root/.mehrvpn1-admin)"
else
  ADMIN_PASSWORD='see /root/.mehrvpn1-admin'
fi
if [[ -n "$DOMAIN" ]]; then
  PANEL_URL="https://$DOMAIN/"
else
  SERVER_IP="$VPN_REMOTE"
  PANEL_URL="http://$SERVER_IP/"
fi

curl -fsS --max-time 10 http://127.0.0.1:8000/api/health >/dev/null
systemctl is-active --quiet openvpn-server@server.service
systemctl is-active --quiet mehrvpn1-agent.service
systemctl is-active --quiet mehrvpn1-web.service
systemctl is-active --quiet nginx

cat >&2 <<EOF

============================================================
 MehrVPN1 installed successfully
============================================================
 Panel:    $PANEL_URL
 Username: admin
 Password: $ADMIN_PASSWORD
 OpenVPN:  $VPN_REMOTE:1194/udp
 Services: web ✓  agent ✓  openvpn ✓  nginx ✓

Credentials are also stored in /root/.mehrvpn1-admin
============================================================
EOF
