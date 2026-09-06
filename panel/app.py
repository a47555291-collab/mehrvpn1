import json
import os
import socket
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auth import create_session, delete_session, get_session, hash_password, verify_password
from .config import CLIENT_DIR, SESSION_TTL, SOCKET_PATH, COOKIE_SECURE
from .db import db, init_db
from .security import require_same_origin, valid_name

app = FastAPI(title="MehrVPN1", docs_url=None, redoc_url=None)
STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    quota_gb: float = Field(default=0, ge=0, le=100000)
    expires_at: int | None = Field(default=None, ge=0)


def agent_call(payload):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(30)
    try:
        s.connect(str(SOCKET_PATH))
        s.sendall(json.dumps(payload).encode())
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if len(chunk) < 65536:
                break
        result = json.loads(b"".join(chunks) or b"{}")
    except OSError as e:
        raise HTTPException(503, f"privileged agent unavailable: {e}")
    finally:
        s.close()
    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "agent operation failed"))
    return result


@app.on_event("startup")
def startup():
    init_db()
    CLIENT_DIR.mkdir(parents=True, exist_ok=True)


def current_user(request: Request):
    row = get_session(request.cookies.get("mehrvpn_session"))
    if not row:
        raise HTTPException(401, "authentication required")
    return row


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/api/health")
def health():
    return {"ok": True, "service": "mehrvpn1"}


@app.post("/api/auth/login")
def login(data: Login, request: Request, response: Response):
    require_same_origin(request)
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (data.username,)).fetchone()
    if not row or not verify_password(row["password_hash"], data.password):
        raise HTTPException(401, "invalid credentials")
    token = create_session(row["id"], SESSION_TTL)
    response.set_cookie("mehrvpn_session", token, max_age=SESSION_TTL, httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/")
    return {"ok": True, "username": row["username"], "role": row["role"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    require_same_origin(request)
    token = request.cookies.get("mehrvpn_session")
    if token:
        delete_session(token)
    response.delete_cookie("mehrvpn_session", path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return dict(user)


@app.get("/api/server/status")
def server_status(user=Depends(current_user)):
    return agent_call({"action": "openvpn-status"})["data"]


@app.get("/api/clients")
def clients(user=Depends(current_user)):
    with db() as c:
        rows = c.execute("SELECT id,name,common_name,quota_bytes,used_bytes,expires_at,revoked,created_at FROM clients ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/clients")
def create_client(data: ClientCreate, request: Request, user=Depends(current_user)):
    require_same_origin(request)
    if not valid_name(data.name):
        raise HTTPException(400, "invalid client name")
    with db() as c:
        if c.execute("SELECT 1 FROM clients WHERE name=?", (data.name,)).fetchone():
            raise HTTPException(409, "client already exists")
    result = agent_call({"action": "client-create", "name": data.name})
    now = int(time.time())
    with db() as c:
        c.execute("INSERT INTO clients(name,common_name,quota_bytes,expires_at,created_at) VALUES(?,?,?,?,?)", (data.name, data.name, int(data.quota_gb * 1024**3), data.expires_at, now))
    return {"ok": True, "name": data.name, "profile": result["profile"]}


@app.get("/api/clients/{client_id}/download")
def download_client(client_id: int, user=Depends(current_user)):
    with db() as c:
        row = c.execute("SELECT name,revoked FROM clients WHERE id=?", (client_id,)).fetchone()
    if not row:
        raise HTTPException(404, "client not found")
    if row["revoked"]:
        raise HTTPException(409, "client is revoked")
    path = CLIENT_DIR / f"{row['name']}.ovpn"
    if not path.exists():
        raise HTTPException(404, "profile not found")
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="application/x-openvpn-profile", headers={"Content-Disposition": f"attachment; filename={row['name']}.ovpn"})


@app.post("/api/clients/{client_id}/revoke")
def revoke(client_id: int, request: Request, user=Depends(current_user)):
    require_same_origin(request)
    with db() as c:
        row = c.execute("SELECT name,revoked FROM clients WHERE id=?", (client_id,)).fetchone()
    if not row:
        raise HTTPException(404, "client not found")
    if not row["revoked"]:
        agent_call({"action": "client-revoke", "name": row["name"]})
        with db() as c:
            c.execute("UPDATE clients SET revoked=1 WHERE id=?", (client_id,))
    return {"ok": True}
