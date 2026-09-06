import re
from fastapi import HTTPException,Request
NAME_RE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')
def valid_name(name):return bool(NAME_RE.fullmatch(name))
def require_same_origin(request:Request):
 origin=request.headers.get('origin')
 if origin:
  host=request.headers.get('host','')
  if not host or origin.rstrip('/').split('://',1)[-1]!=host: raise HTTPException(403,'origin check failed')
