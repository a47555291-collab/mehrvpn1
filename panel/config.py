import os
from pathlib import Path

ROOT = Path(os.getenv("MEHRVPN1_ROOT", "/opt/mehrvpn1"))
DATA = Path(os.getenv("MEHRVPN1_DATA", "/var/lib/mehrvpn1"))
CLIENT_DIR = DATA / "clients"
SOCKET_PATH = Path(os.getenv("MEHRVPN1_SOCKET", "/run/mehrvpn1/agent.sock"))
SESSION_TTL = int(os.getenv("MEHRVPN1_SESSION_TTL", "43200"))
COOKIE_SECURE = os.getenv("MEHRVPN1_SESSION_SECURE", "true").lower() in {"1", "true", "yes"}
OPENVPN_DIR = Path(os.getenv("MEHRVPN1_OPENVPN_DIR", "/etc/openvpn/server"))
PKI_DIR = Path(os.getenv("MEHRVPN1_PKI_DIR", "/etc/openvpn/easy-rsa/pki"))
VPN_SUBNET = os.getenv("MEHRVPN1_VPN_SUBNET", "10.8.0.0/24")
VPN_PORT = int(os.getenv("MEHRVPN1_VPN_PORT", "1194"))
VPN_PROTO = os.getenv("MEHRVPN1_VPN_PROTO", "udp")
VPN_REMOTE = os.getenv("MEHRVPN1_VPN_REMOTE", "")
