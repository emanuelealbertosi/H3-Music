"""Enable/disable only H3-Music's private Serve endpoint; never reset Serve."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from remote_access import validate_origin


def endpoint_available(config,authority,target):
 port=authority.rsplit(':',1)[1]
 others=[key for key in config.get('Web',{}) if key.endswith(':'+port) and key!=authority]
 web=config.get('Web',{}).get(authority)
 tcp=config.get('TCP',{}).get(port)
 expected={'Handlers':{'/':{'Proxy':target}}}
 if others or (web is not None and web!=expected) or (tcp is not None and (tcp!={'HTTPS':True} or web!=expected)):
  raise ValueError('Porta Tailscale già usata da un altro servizio. Scegli una porta diversa con --port.')
 if config.get('AllowFunnel',{}).get(authority):
  raise ValueError('Questa porta usa Funnel pubblico: scegli un’altra porta per l’accesso privato.')


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--disable',action='store_true')
 parser.add_argument('--port',type=int,default=8776)
 args=parser.parse_args()
 if not 1<=args.port<=65535:raise ValueError('Porta non valida.')
 executable=shutil.which('tailscale') or str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Tailscale/tailscale.exe')
 def run(*cmd):
  result=subprocess.run([executable,*cmd],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=0x08000000 if os.name=='nt' else 0)
  if result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'Comando Tailscale non riuscito.')
  return result.stdout
 data=Path(os.environ.get('H3_MUSIC_DATA',str(ROOT/'data')));data.mkdir(parents=True,exist_ok=True)
 path=data/'remote-access.json'
 config=json.loads(run('serve','status','--json') or '{}') or {}
 status=json.loads(run('status','--json'))
 if status.get('BackendState')!='Running':raise RuntimeError('Connetti Tailscale prima di continuare.')
 dns=status['Self']['DNSName'].rstrip('.')
 local_port=int(os.environ.get('H3_MUSIC_PORT','8776'))
 target=f'http://127.0.0.1:{local_port}'
 if args.disable:
  if not path.exists():print('Accesso remoto H3-Music già disattivato.');return
  record=json.loads(path.read_text(encoding='utf-8'))
  origin=validate_origin(record['origin'])
  from urllib.parse import urlsplit
  url=urlsplit(origin);authority=url.netloc;port=url.port or 443
  if url.hostname!=dns:raise ValueError('La configurazione salvata appartiene a un altro PC Tailscale.')
  endpoint_available(config,authority,target)
  if str(port) in config.get('TCP',{}):run('serve',f'--https={port}','off')
  path.unlink();print('Accesso remoto H3-Music disattivato. Gli altri servizi restano attivi.');return
 origin=validate_origin(f'https://{dns}:{args.port}');authority=f'{dns}:{args.port}'
 endpoint_available(config,authority,target)
 if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('origin')!=origin:
  raise ValueError('Disattiva il precedente accesso remoto prima di cambiare porta.')
 backup=data/'remote-access-backups';backup.mkdir(exist_ok=True)
 (backup/f'serve-{time.time_ns()}.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
 old=path.read_bytes() if path.exists() else None
 pending=path.with_suffix('.tmp');pending.write_text(json.dumps({'origin':origin},indent=2),encoding='utf-8');pending.replace(path)
 try:output=run('serve','--bg',f'--https={args.port}',target)
 except Exception:
  if old is None:path.unlink(missing_ok=True)
  else:path.write_bytes(old)
  raise
 print(output.strip())
 print('\nH3-Music: '+origin)
 print('Accesso privato dalla rete Tailscale. Tieni il PC acceso e H3-Music avviata.')


if __name__=='__main__':
 try:main()
 except Exception as error:print('Errore: '+str(error),file=sys.stderr);sys.exit(1)
