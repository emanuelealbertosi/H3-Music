"""Explicit, machine-local allowlist for a private Tailscale Serve origin."""
import json
import re
from urllib.parse import urlsplit


def validate_origin(value):
 if not isinstance(value,str):raise ValueError('Indirizzo remoto non valido.')
 url=urlsplit(value)
 if (url.scheme!='https' or url.username or url.password or url.path or url.query or url.fragment
     or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.ts\.net',url.hostname or '')
     or value!='https://'+url.netloc or url.netloc!=url.netloc.lower()):
  raise ValueError('Usa l’indirizzo HTTPS esatto del PC nella rete Tailscale, senza percorsi.')
 if url.port is not None and not 1<=url.port<=65535:raise ValueError('Porta remota non valida.')
 return value


def configured_origin(data):
 try:
  value=json.loads((data/'remote-access.json').read_text(encoding='utf-8'))['origin']
  return validate_origin(value)
 except (OSError,ValueError,KeyError,TypeError):return None


def allowed_hosts(data,port):
 hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
 origin=configured_origin(data)
 if origin:hosts.add(urlsplit(origin).netloc)
 return hosts


def allowed_origins(data,port):
 origins={f'http://127.0.0.1:{port}',f'http://localhost:{port}'}
 origin=configured_origin(data)
 if origin:origins.add(origin)
 return origins
