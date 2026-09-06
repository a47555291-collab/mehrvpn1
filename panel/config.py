from pathlib import Path
import os
APP_DIR=Path('/opt/mehrvpn1')
DATA_DIR=Path(os.getenv('MEHRVPN_DATA_DIR',APP_DIR/'data'))
DB_PATH=DATA_DIR/'mehrvpn.db'
SOCKET_PATH=Path('/run/mehrvpn1/agent.sock')
CLIENT_DIR=DATA_DIR/'clients'
SESSION_TTL=int(os.getenv('MEHRVPN_SESSION_TTL','43200'))
COOKIE_SECURE=os.getenv('MEHRVPN_COOKIE_SECURE','1')!='0'
