import json,os,socket,subprocess
from .config import SOCKET_PATH
ALLOWED={'openvpn-status':['/bin/systemctl','is-active','openvpn-server@server.service'],'openvpn-restart':['/bin/systemctl','restart','openvpn-server@server.service']}
def serve():
 SOCKET_PATH.parent.mkdir(parents=True,exist_ok=True)
 try:SOCKET_PATH.unlink()
 except FileNotFoundError:pass
 s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.bind(str(SOCKET_PATH));os.chmod(SOCKET_PATH,0o660);s.listen(16)
 while True:
  c,_=s.accept()
  try:
   q=json.loads(c.recv(4096));a=q.get('action')
   if a not in ALLOWED:raise ValueError('unsupported action')
   p=subprocess.run(ALLOWED[a],capture_output=True,text=True,timeout=20);out={'ok':p.returncode==0,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:],'code':p.returncode}
  except Exception as e:out={'ok':False,'error':str(e)}
  c.sendall(json.dumps(out).encode());c.close()
if __name__=='__main__':serve()
