# MehrVPN1

MehrVPN1 is an OpenVPN-native web control panel for Debian 12/13 and Ubuntu 22.04/24.04. It provisions a real OpenVPN server, Easy-RSA PKI, client certificates, inline `.ovpn` profiles, revocation/CRL handling, traffic/status visibility, systemd services, Nginx and optional Let's Encrypt HTTPS.

## One-command installation

Run as root on a fresh VPS with `/dev/net/tun` available:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/a47555291-collab/mehrvpn1/main/install.sh)
```

The installer asks for a panel domain. If a domain is supplied and its DNS already points to the VPS, it configures Nginx + Let's Encrypt HTTPS. If the domain is left empty, the panel is available over the VPS public IP using HTTP and the installer automatically generates the OpenVPN endpoint from the public IPv4 address.

## What is actually installed

- OpenVPN server on UDP/1194
- Easy-RSA CA, server certificate, DH parameters and `tls-crypt`
- Client certificate creation from the web panel
- Inline `.ovpn` downloads containing CA, client certificate, private key and TLS key
- Certificate revocation and CRL regeneration
- OpenVPN status and connected-client visibility
- SQLite metadata database
- FastAPI web panel behind Nginx
- Privileged Unix-socket agent with an explicit action allowlist
- systemd units for the panel, agent and OpenVPN
- IPv4 forwarding and MASQUERADE for the VPN subnet
- Automatic admin credential generation at `/root/.mehrvpn1-admin`

## Security model

The web process does not run as root. Operations that need root privileges are sent to a local Unix socket owned by `root:mehrvpn`; the agent accepts only fixed OpenVPN operations and never executes arbitrary commands received from HTTP.

## Important production note

The repository contains the complete deployment path, but a genuine production release still needs a real VPS end-to-end test: installer run, OpenVPN service health, client profile generation, an actual OpenVPN client connection, Internet/NAT verification, and revoke/CRL verification. Passing CI alone does not prove a VPN works on every VPS provider.

## Repository

See the project on GitHub: https://github.com/a47555291-collab/mehrvpn1
