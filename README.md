# MehrVPN1

Fresh OpenVPN management panel foundation for Linux VPS servers.

## Features
- FastAPI web panel
- Argon2 password hashing and hashed sessions
- SQLite persistence
- Secure client-name validation
- Unix-socket privileged agent with an explicit allow-list
- systemd and Nginx integration
- One-command installer for Ubuntu 22.04/24.04 and Debian 12/13
- Automated tests and GitHub Actions CI

## Install
```bash
curl -fsSL https://raw.githubusercontent.com/a47555291-collab/mehrvpn1/main/install.sh -o /tmp/mehrvpn1-install.sh
less /tmp/mehrvpn1-install.sh
sudo bash /tmp/mehrvpn1-install.sh
```

This is a fresh implementation, not a patch of the old repository.
