#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

VPN_REMOTE="${VPN_REMOTE:-${1:-}}"
VPN_PORT="${VPN_PORT:-1194}"
VPN_NET="${VPN_NET:-10.8.0.0 255.255.255.0}"
PKI=/etc/openvpn/easy-rsa
SERVER=/etc/openvpn/server
EASYRSA=/usr/share/easy-rsa/easyrsa

[[ $EUID -eq 0 ]] || { echo 'run as root' >&2; exit 1; }
[[ -x "$EASYRSA" ]] || { echo 'easy-rsa is not installed' >&2; exit 1; }
[[ -n "$VPN_REMOTE" ]] || VPN_REMOTE="$(curl -4fsS --max-time 10 https://api.ipify.org || true)"
[[ -n "$VPN_REMOTE" ]] || { echo 'cannot determine public IPv4; set VPN_REMOTE=...' >&2; exit 1; }

install -d -m 0755 "$PKI" "$SERVER"
if [[ ! -f "$PKI/pki/ca.crt" ]]; then
  cd "$PKI"
  "$EASYRSA" init-pki
  EASYRSA_BATCH=1 EASYRSA_REQ_CN='MehrVPN1 CA' "$EASYRSA" build-ca nopass
  EASYRSA_BATCH=1 "$EASYRSA" build-server-full server nopass
  EASYRSA_BATCH=1 "$EASYRSA" gen-dh
  EASYRSA_BATCH=1 "$EASYRSA" gen-crl
fi
[[ -f "$SERVER/ta.key" ]] || openvpn --genkey secret "$SERVER/ta.key"
cp -f "$PKI/pki/ca.crt" "$SERVER/ca.crt"
cp -f "$PKI/pki/issued/server.crt" "$SERVER/server.crt"
cp -f "$PKI/pki/private/server.key" "$SERVER/server.key"
cp -f "$PKI/pki/dh.pem" "$SERVER/dh.pem"
cp -f "$PKI/pki/crl.pem" "$SERVER/crl.pem"
chown root:root "$SERVER"/*.crt "$SERVER"/*.key "$SERVER"/dh.pem "$SERVER"/ta.key
chmod 0644 "$SERVER/ca.crt" "$SERVER/server.crt" "$SERVER/dh.pem" "$SERVER/crl.pem"
chmod 0600 "$SERVER/server.key" "$SERVER/ta.key"
chown root:mehrvpn "$SERVER/crl.pem"; chmod 0640 "$SERVER/crl.pem"
cat > "$SERVER/server.conf" <<EOF
port ${VPN_PORT}
proto udp
dev tun
user nobody
group nogroup
persist-key
persist-tun
topology subnet
server ${VPN_NET}
ifconfig-pool-persist /var/lib/openvpn/ipp.txt
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
push "dhcp-option DNS 1.0.0.1"
keepalive 10 120
ca ${SERVER}/ca.crt
cert ${SERVER}/server.crt
key ${SERVER}/server.key
dh ${SERVER}/dh.pem
tls-crypt ${SERVER}/ta.key
crl-verify ${SERVER}/crl.pem
auth SHA256
cipher AES-256-GCM
data-ciphers AES-256-GCM:AES-128-GCM
status ${SERVER}/status.log 10
status-version 3
verb 3
explicit-exit-notify 1
EOF
chmod 0644 "$SERVER/server.conf"
cat > /etc/sysctl.d/99-mehrvpn1.conf <<EOF
net.ipv4.ip_forward=1
EOF
sysctl --system >/dev/null
WAN_IF="$(ip -4 route show default | awk 'NR==1{print $5}')"
[[ -n "$WAN_IF" ]] || { echo 'cannot detect default network interface' >&2; exit 1; }
iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o "$WAN_IF" -j MASQUERADE 2>/dev/null || iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o "$WAN_IF" -j MASQUERADE
iptables -C FORWARD -s 10.8.0.0/24 -o "$WAN_IF" -j ACCEPT 2>/dev/null || iptables -A FORWARD -s 10.8.0.0/24 -o "$WAN_IF" -j ACCEPT
iptables -C FORWARD -d 10.8.0.0/24 -m conntrack --ctstate RELATED,ESTABLISHED -i "$WAN_IF" -j ACCEPT 2>/dev/null || iptables -A FORWARD -d 10.8.0.0/24 -m conntrack --ctstate RELATED,ESTABLISHED -i "$WAN_IF" -j ACCEPT
systemctl enable --now openvpn-server@server.service
systemctl restart openvpn-server@server.service
systemctl is-active --quiet openvpn-server@server.service
printf 'OpenVPN ready: %s:%s/udp\n' "$VPN_REMOTE" "$VPN_PORT"
