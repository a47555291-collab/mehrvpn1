const $=x=>document.querySelector(x);
async function api(u,o={}){const r=await fetch(u,{...o,headers:{'Content-Type':'application/json',...(o.headers||{})}});if(!r.ok)throw Error(await r.text());return r.json()}
function esc(s){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function date(v){return v?new Date(v*1000).toLocaleString():'Unlimited'}
async function load(){
  const [a,s]=await Promise.all([api('/api/clients'),api('/api/server/status')]);
  $('#status').textContent=`OpenVPN: ${s.service} · connected: ${s.clients.length}`;
  $('#t').innerHTML=a.map(x=>`<tr><td>${esc(x.name)}</td><td>${x.quota_bytes?(x.quota_bytes/1073741824).toFixed(2)+' GB':'Unlimited'}</td><td>${(x.used_bytes/1073741824).toFixed(2)} GB</td><td>${date(x.expires_at)}</td><td>${x.revoked?'Revoked':'Active'}</td><td>${x.revoked?'':'<a class="download" href="/api/clients/'+x.id+'/download">.ovpn</a> <button data-id="'+x.id+'" class="r">Revoke</button>'}</td></tr>`).join('');
  document.querySelectorAll('.r').forEach(b=>b.onclick=async()=>{if(confirm('Revoke this client?')){await api('/api/clients/'+b.dataset.id+'/revoke',{method:'POST'});load()}})
}
$('#l').onclick=async()=>{try{await api('/api/auth/login',{method:'POST',body:JSON.stringify({username:$('#u').value,password:$('#p').value})});$('#login').hidden=true;$('#app').hidden=false;load()}catch(e){$('#m').textContent='Login failed'}};
$('#r').onclick=load;
$('#o').onclick=async()=>{await api('/api/auth/logout',{method:'POST'});location.reload()};
$('#a').onclick=async()=>{const n=prompt('Client name (letters, numbers, . _ -)');if(!n)return;const days=prompt('Validity in days (0 = unlimited)','30');try{const expires=Number(days)>0?Math.floor(Date.now()/1000)+Number(days)*86400:null;await api('/api/clients',{method:'POST',body:JSON.stringify({name:n,expires_at:expires})});load()}catch(e){alert(e.message)}};
(async()=>{try{await api('/api/me');$('#login').hidden=true;$('#app').hidden=false;load()}catch{}})();
