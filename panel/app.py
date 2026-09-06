import os,time
from fastapi import FastAPI,Request,Response,HTTPException,Depends
from fastapi.responses import HTMLResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .config import SESSION_TTL,COOKIE_SECURE,CLIENT_DIR
from .db import db,init_db
from .auth import hash_password,verify_password,create_session,get_session,delete_session
from .security import valid_name,require_same_origin
app=FastAPI(title='MehrVPN1',docs_url=None,redoc_url=None)
STATIC=os.path.join(os.path.dirname(__file__),'static'); app.mount('/static',StaticFiles(directory=STATIC),name='static')
class Login(BaseModel): username:str=Field(min_length=1,max_length=64); password:str=Field(min_length=8,max_length=256)
class ClientCreate(BaseModel): name:str=Field(min_length=1,max_length=64); quota_gb:float=Field(default=0,ge=0,le=100000); expires_at:int|None=None
@app.on_event('startup')
def startup():init_db();CLIENT_DIR.mkdir(parents=True,exist_ok=True)
def current_user(request:Request):
 row=get_session(request.cookies.get('mehrvpn_session'))
 if not row:raise HTTPException(401,'authentication required')
 return row
@app.get('/',response_class=HTMLResponse)
def index():return FileResponse(os.path.join(STATIC,'index.html'))
@app.get('/api/health')
def health():return {'ok':True,'service':'mehrvpn1'}
@app.post('/api/auth/login')
def login(data:Login,request:Request,response:Response):
 require_same_origin(request)
 with db() as c:row=c.execute('SELECT * FROM users WHERE username=?',(data.username,)).fetchone()
 if not row or not verify_password(row['password_hash'],data.password):raise HTTPException(401,'invalid credentials')
 token=create_session(row['id'],SESSION_TTL);response.set_cookie('mehrvpn_session',token,max_age=SESSION_TTL,httponly=True,secure=COOKIE_SECURE,samesite='lax',path='/');return {'ok':True,'username':row['username'],'role':row['role']}
@app.post('/api/auth/logout')
def logout(request:Request,response:Response):
 require_same_origin(request);token=request.cookies.get('mehrvpn_session')
 if token:delete_session(token)
 response.delete_cookie('mehrvpn_session',path='/');return {'ok':True}
@app.get('/api/me')
def me(user=Depends(current_user)):return dict(user)
@app.get('/api/clients')
def clients(user=Depends(current_user)):
 with db() as c:rows=c.execute('SELECT id,name,common_name,quota_bytes,used_bytes,expires_at,revoked,created_at FROM clients ORDER BY id DESC').fetchall()
 return [dict(r) for r in rows]
@app.post('/api/clients')
def create_client(data:ClientCreate,request:Request,user=Depends(current_user)):
 require_same_origin(request)
 if not valid_name(data.name):raise HTTPException(400,'invalid client name')
 with db() as c:
  if c.execute('SELECT 1 FROM clients WHERE name=?',(data.name,)).fetchone():raise HTTPException(409,'client already exists')
  c.execute('INSERT INTO clients(name,common_name,quota_bytes,expires_at,created_at) VALUES(?,?,?,?,?)',(data.name,data.name,int(data.quota_gb*1024**3),data.expires_at,int(time.time())))
 return {'ok':True,'name':data.name}
@app.post('/api/clients/{client_id}/revoke')
def revoke(client_id:int,request:Request,user=Depends(current_user)):
 require_same_origin(request)
 with db() as c:cur=c.execute('UPDATE clients SET revoked=1 WHERE id=?',(client_id,))
 if not cur.rowcount:raise HTTPException(404,'client not found')
 return {'ok':True}
