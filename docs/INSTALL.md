# Installation

1. Use a supported VPS with systemd and `/dev/net/tun`.
2. Download `install.sh` to a temporary file and inspect it.
3. Run it as root.
4. Read `/root/.mehrvpn1-admin` for the initial admin credential.
5. Put the panel behind HTTPS before exposing it publicly.

The installer keeps source discovery separate from logging, validates the downloaded tree, checks Nginx configuration, and enables the services with systemd.
