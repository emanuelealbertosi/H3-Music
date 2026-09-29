"""Delete explicitly selected results, keeping projects and imported audio."""
import json
import os
import re
import shutil
import stat


def checked_folder(app,ident):
 root=app.OUT.resolve()
 if root.parent!=app.DATA.resolve() or app.OUT.is_symlink() or app.OUT.is_junction():
  raise ValueError('Cartella dei risultati non valida.')
 folder=app.OUT/ident
 if folder.is_symlink() or folder.is_junction():raise ValueError('La cartella del risultato è un collegamento.')
 if folder.resolve().parent!=root:raise ValueError('Percorso del risultato non valido.')
 if not folder.exists() and not folder.is_symlink():return folder
 # Refuse links/junctions, including nested ones, before removing any file.
 for current,dirs,files in os.walk(folder,followlinks=False):
  for path in [type(folder)(current)]+[type(folder)(current)/name for name in dirs+files]:
   info=path.lstat()
   if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
    raise ValueError('Il risultato contiene un collegamento: rimuovilo manualmente prima di eliminare la sessione.')
 return folder


def delete(app,ids):
 if not isinstance(ids,list) or not 1<=len(ids)<=300 or any(not isinstance(i,str) or not re.fullmatch('[a-f0-9]{32}',i) for i in ids):
  raise ValueError('Seleziona da 1 a 300 risultati validi.')
 selected=set(ids)
 with app.LOCK:
  rows={r['id']:r for r in app.db('SELECT id,kind,status,request FROM jobs')}
  active={'queued','running','cancelling'}
  for ident in selected:
   if ident in rows and (rows[ident]['status'] in active or ident in app.ACTIVE):
    raise ValueError('Termina o annulla prima i lavori selezionati.')
  for ident,row in rows.items():
   # Completed legacy voice results still use the parent's separated stems.
   protected=row['status'] in active or (row['kind']=='voice' and row['status']=='completed' and ident not in selected)
   if not protected:continue
   seen={ident};source=json.loads(row['request']).get('source_id')
   while source in rows and source not in seen:
    if source in selected:
     title=json.loads(row['request']).get('title','un altro risultato')
     raise ValueError('Il brano serve ancora a «'+title+'». Attendi il lavoro in corso oppure seleziona anche il cambio voce collegato.')
    seen.add(source);source=json.loads(rows[source]['request']).get('source_id')
  folders={ident:checked_folder(app,ident) for ident in selected if ident in rows}
  deleted=[];errors=[]
  # Dependents first: if deleting a voice fails, keep its parent's stems.
  ordered=[];pending=set(folders)
  while pending:
   referenced={json.loads(rows[i]['request']).get('source_id') for i in pending}
   leaves=pending-referenced
   if not leaves:raise ValueError('Dipendenze circolari fra risultati: cancellazione annullata.')
   ordered.extend(sorted(leaves));pending-=leaves
  failed=set()
  for ident in ordered:
   if ident in failed:
    errors.append({'id':ident,'error':'Conservato perché un risultato collegato non è stato eliminato.'});continue
   try:
    folder=folders[ident]
    if folder.exists():shutil.rmtree(folder)
    app.db('DELETE FROM jobs WHERE id=?',(ident,));deleted.append(ident)
   except OSError:
    errors.append({'id':ident,'error':'File occupati o non accessibili. Chiudi eventuali player esterni e riprova.'})
    source=json.loads(rows[ident]['request']).get('source_id');seen=set()
    while source in rows and source not in seen:
     seen.add(source);failed.add(source);source=json.loads(rows[source]['request']).get('source_id')
  return {'deleted':deleted,'missing':sorted(selected-rows.keys()),'errors':errors}
