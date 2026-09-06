# Architecture

Browser -> Nginx -> FastAPI -> SQLite. Privileged OpenVPN service operations are isolated behind a Unix-domain agent with a fixed action allow-list.

This repository is intentionally a fresh foundation. Full PKI automation, live accounting, quota enforcement, ACME TLS, encrypted backup/restore, and VPS E2E tests are planned next and are not falsely advertised as complete here.
