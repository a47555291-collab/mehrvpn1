import json
import os
import re
import socket
import subprocess
from pathlib import Path

from .config import CLIENT_DIR, OPENVPN_DIR, PKI_DIR, SOCKET_PATH, VPN_PORT, VPN_PROTO, VPN_REMOTE

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
EASYRSA = os.getenv("MEHRVPN1_EASYRSA", "/usr/share/easy-rsa/easyrsa")
SERVICE = "openvpn-server@server.service"


def _run(args, timeout=60, env=None):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "command failed").strip()[-4000:])
    return p.stdout


def _easyrsa(args, timeout=180):
    env = os.environ.copy()
    env["EASYRSA_BATCH"] = "1"
    env["EASYRSA_PKI"] = str(PKI_DIR)
    env["EASYRSA_REQ_CN"] = "MehrVPN1 CA"
    return _run([EASYRSA, *args], timeout=timeout, env=env)


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def create_client(name):
    if not NAME_RE.fullmatch(name):
        raise ValueError("invalid client name")
    cert = PKI_DIR / "issued" / f"{name}.crt"
    key = PKI_DIR / "private" / f"{name}.key"
    if not cert.exists() or not key.exists():
        _easyrsa(["build-client-full", name, "nopass"])
    ca = _read(PKI_DIR / "ca.crt")
    crt = _read(cert)
    key_text = _read(key)
    tls = _read(OPENVPN_DIR / "ta.key")
    remote = VPN_REMOTE or "YOUR_SERVER_HOSTNAME_OR_IP"
    profile = "\n".join([
        "client", "dev tun", "proto " + VPN_PROTO, f"remote {remote} {VPN_PORT}",
        "resolv-retry infinite", "nobind", "persist-key", "persist-tun",
        "remote-cert-tls server", "auth-nocache", "verb 3", "",
        "<ca>", ca.strip(), "</ca>", "<cert>", crt.strip(), "</cert>",
        "<key>", key_text.strip(), "</key>", "<tls-crypt>", tls.strip(), "</tls-crypt>", "",
    ])
    CLIENT_DIR.mkdir(parents=True, exist_ok=True)
    path = CLIENT_DIR / f"{name}.ovpn"
    path.write_text(profile, encoding="utf-8")
    os.chmod(path, 0o640)
    return profile


def revoke_client(name):
    if not NAME_RE.fullmatch(name):
        raise ValueError("invalid client name")
    _easyrsa(["revoke", name], timeout=180)
    _easyrsa(["gen-crl"], timeout=180)
    crl = PKI_DIR / "crl.pem"
    if crl.exists():
        _run(["/bin/chown", "root:mehrvpn", str(crl)])
        _run(["/bin/chmod", "0640", str(crl)])
    _run(["/bin/systemctl", "restart", SERVICE], timeout=60)
    try:
        (CLIENT_DIR / f"{name}.ovpn").unlink()
    except FileNotFoundError:
        pass


def status():
    active = subprocess.run(["/bin/systemctl", "is-active", SERVICE], capture_output=True, text=True).stdout.strip()
    enabled = subprocess.run(["/bin/systemctl", "is-enabled", SERVICE], capture_output=True, text=True).stdout.strip()
    candidates = [Path("/run/openvpn/server.status"), OPENVPN_DIR / "status.log"]
    status_file = next((p for p in candidates if p.exists()), None)
    clients = []
    if status_file:
        for line in status_file.read_text(errors="replace").splitlines():
            if line.startswith("CLIENT_LIST,"):
                parts = line.split(",")
                if len(parts) >= 8:
                    clients.append({"name": parts[1], "remote": parts[2], "virtual_ip": parts[3], "bytes_received": parts[5], "bytes_sent": parts[6], "connected_since": parts[7]})
    return {"service": active, "enabled": enabled, "clients": clients}


def serve():
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        SOCKET_PATH.unlink()
    except FileNotFoundError:
        pass
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(SOCKET_PATH))
    os.chmod(SOCKET_PATH, 0o660)
    s.listen(16)
    while True:
        c, _ = s.accept()
        try:
            q = json.loads(c.recv(8192))
            action = q.get("action")
            if action == "openvpn-status": out = {"ok": True, "data": status()}
            elif action == "openvpn-restart": _run(["/bin/systemctl", "restart", SERVICE], timeout=60); out = {"ok": True}
            elif action == "client-create": out = {"ok": True, "profile": create_client(q.get("name", ""))}
            elif action == "client-revoke": revoke_client(q.get("name", "")); out = {"ok": True}
            else: raise ValueError("unsupported action")
        except Exception as e:
            out = {"ok": False, "error": str(e)}
        c.sendall(json.dumps(out).encode())
        c.close()


if __name__ == "__main__":
    serve()
