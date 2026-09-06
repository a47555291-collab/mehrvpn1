#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
APP=mehrvpn1; ROOT=/opt/$APP; DATA=/var/lib/$APP; RUN=/run/$APP
log(){ printf '[%s] %s\n' "$APP" "$*" >&2; }; die(){ log "ERROR: $*"; exit 1; }
[[ $EUID -eq 0 ]]||die 'Run as root.'; [[ -c /dev/net/tun ]]||die '/dev/net/tun is missing.'
. /etc/os-release
case "$ID:$VERSION_ID" in ubuntu:22.04|ubuntu:24.04|debian:12|debian:13) ;; *) die "Unsupported OS: $ID $VERSION_ID";; esac
export DEBIAN_FRONTEND=noninteractive
apt-get update; apt-get install -y python3 python3-venv python3-pip nginx openvpn curl ca-certificates openssl
id mehrvpn >/dev/null 2>&1||useradd --system --home /var/lib/mehrvpn1 --shell /usr/sbin/nologin mehrvpn
install -d -o mehrvpn -g mehrvpn -m 0750 "$DATA/clients"; install -d -o root -g mehrvpn -m 0770 "$RUN"
SRC=$(mktemp -d /tmp/mehrvpn1.XXXXXX); trap 'rm -rf "$SRC"' EXIT
log 'Downloading source...'
curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 'https://github.com/a47555291-collab/mehrvpn1/archive/refs/heads/main.tar.gz' -o "$SRC/source.tar.gz"
tar -xzf "$SRC/source.tar.gz" -C "$SRC"
SRC_TREE=$(find "$SRC" -mindepth 1 -maxdepth 1 -type d -name 'mehrvpn1-*' -print -quit)
[[ -n "$SRC_TREE" && -d "$SRC_TREE/panel" ]]||die 'Downloaded source is invalid.'
rm -rf "$ROOT"; mkdir -p "$ROOT"; cp -a "$SRC_TREE/." "$ROOT/"; chown -R root:root "$ROOT"
python3 -m venv "$ROOT/.venv"; "$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements.txt"
cp "$ROOT/systemd/mehrvpn1-web.service" /etc/systemd/system/; cp "$ROOT/systemd/mehrvpn1-agent.service" /etc/systemd/system/
cp "$ROOT/nginx/mehrvpn1.conf" /etc/nginx/sites-available/mehrvpn1; ln -sfn /etc/nginx/sites-available/mehrvpn1 /etc/nginx/sites-enabled/mehrvpn1; rm -f /etc/nginx/sites-enabled/default
if [[ ! -f /root/.mehrvpn1-admin ]];then P=$(openssl rand -base64 24); "$ROOT/.venv/bin/python" - <<PY
import time
from panel.db import init_db,db
from panel.auth import hash_password
init_db()
with db() as c:c.execute('insert into users(username,password_hash,role,created_at) values(?,?,?,?)',('admin',hash_password('''$P'''),'admin',int(time.time())))
PY
 umask 077;printf 'username=admin\npassword=%s\n' "$P" >/root/.mehrvpn1-admin;fi
nginx -t;systemctl daemon-reload;systemctl enable --now mehrvpn1-agent.service;systemctl enable --now mehrvpn1-web.service;systemctl reload nginx
log 'MehrVPN1 installed.';log 'Credentials: /root/.mehrvpn1-admin'
