import hashlib,secrets,time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from .db import db
PH=PasswordHasher()
def hash_password(password): return PH.hash(password)
def verify_password(stored,password):
 try:return PH.verify(stored,password)
 except VerifyMismatchError:return False
def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()
def create_session(user_id,ttl):
 token=secrets.token_urlsafe(32); now=int(time.time())
 with db() as c:
  c.execute('DELETE FROM sessions WHERE expires_at<?',(now,)); c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token_hash(token),user_id,now+ttl,now))
 return token
def get_session(token):
 if not token:return None
 with db() as c:return c.execute('SELECT u.id,u.username,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?',(token_hash(token),int(time.time()))).fetchone()
def delete_session(token):
 with db() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(token_hash(token),))
