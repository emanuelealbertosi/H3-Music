"""Verified, staged model file updates; reusable from the installer and tests."""
import hashlib, pathlib, shutil, tempfile

def matches(path,entry):
 path=pathlib.Path(path)
 if not path.is_file() or path.stat().st_size!=entry['size']:return False
 if entry.get('lfs'):
  with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==entry['lfs']['oid']
 digest=hashlib.sha1(f"blob {entry['size']}\0".encode())
 with path.open('rb') as f:
  while block:=f.read(1024*1024):digest.update(block)
 return digest.hexdigest()==entry['oid']

def update_files(root,folder,repo,revision,entries,download):
 root=pathlib.Path(root);folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True)
 temp=folder.parent/'.install-temp';temp.mkdir(parents=True,exist_ok=True)
 pending=[]
 with tempfile.TemporaryDirectory(prefix='transcription-update-',dir=temp) as staging:
  staging=pathlib.Path(staging)
  for entry in entries:
   if entry['type']!='file':continue
   relative=pathlib.PurePosixPath(entry['path'])
   if relative.is_absolute() or '..' in relative.parts or '\\' in entry['path'] or ':' in entry['path']:raise ValueError('Percorso modello non valido.')
   target=folder/relative
   if not target.resolve().is_relative_to(folder.resolve()):raise ValueError('Percorso modello esterno alla cartella.')
   if matches(target,entry):continue
   candidate=staging/relative;candidate.parent.mkdir(parents=True,exist_ok=True)
   download(f'https://huggingface.co/{repo}/resolve/{revision}/{relative.as_posix()}',candidate)
   if not matches(candidate,entry):raise ValueError('Verifica del file fallita: '+entry['path'])
   pending.append((target,candidate,relative))
  if not pending:return None
  # All downloads are validated before touching any installed file.
  backups=folder.parent/'.backups';backups.mkdir(exist_ok=True)
  backup=pathlib.Path(tempfile.mkdtemp(prefix='transcription-',dir=backups));changed=[]
  try:
   for target,candidate,relative in pending:
    existed=target.exists();saved=backup/relative
    if existed:saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
    target.parent.mkdir(parents=True,exist_ok=True)
    candidate.replace(target);changed.append((target,saved,existed))
  except BaseException:
   for target,saved,existed in reversed(changed):
    if existed:shutil.copy2(saved,target)
    else:target.unlink(missing_ok=True)
   raise
  print('UPDATED',folder.name,len(changed),'files; backup:',backup,flush=True)
  return backup
