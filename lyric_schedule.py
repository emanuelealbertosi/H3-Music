"""Score-clock lyric sections for native YuE2 attention; no lyrics rewriting.

Inspired by HOT-Step C6 / YuE2 Studio's MIT implementation. Unsupported ABC
features disable scheduling with a recorded reason instead of guessing timings.
"""
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
import math
import re

BIAS = -4.0
TAG = re.compile(r'^[ \t]*\[([^\]\r\n]+)\][ \t]*\r?$', re.M)
ALIASES = {'strofa':'verse','ritornello':'chorus','ponte':'bridge','introduzione':'intro'}


def kind(label):
 label=label.lower().replace('_','-').replace('–','-').replace('—','-').strip()
 found=re.search(r'\b(pre[ -]?chorus|verse|chorus|bridge|intro|outro|interlude|strofa|ritornello|ponte|introduzione)\b',label)
 value=found[0] if found else label
 return ALIASES.get(value,value.replace('pre chorus','pre-chorus').replace('prechorus','pre-chorus'))


def instrumental(label):
 return bool(re.search(r'\b(instrumental|strumentale|solo|break|interlude)\b',label,re.I))


def lyric_blocks(lyrics):
 tags=list(TAG.finditer(lyrics));blocks=[]
 for i,tag in enumerate(tags):
  end=tags[i+1].start() if i+1<len(tags) else len(lyrics)
  # Do not swallow a preceding blank line into the next heading's byte range.
  start=lyrics.rfind('\n',0,tag.start())+1
  body=lyrics[tag.end():end]
  blocks.append({'label':tag[1],'start':start,'end':len(lyrics[:end].rstrip()),
                 'sung':any(c.isalnum() for c in body) and not instrumental(tag[1])})
 return blocks


def score_sections(score):
 """Read the timed Vocal part of YuE2 ABC, using exact rational durations."""
 voices={};current='default';markers=[];vocal_names=[]
 defaults={'unit':Fraction(1,8),'meter':Fraction(1),'whole_seconds':None}
 notes={};tuplets={};body=False
 def state():
  if current not in voices:
   voices[current]=dict(defaults,time=Fraction(0));notes[current]=[]
  return voices[current]
 def field(key,value):
  nonlocal current
  if key=='V':
   m=re.match(r'\s*(\S+)',value)
   if not m:raise ValueError('Voce ABC senza nome.')
   current=m[1];state()
   if re.search(r'vocal|voice|voce|cant',value,re.I) and current not in vocal_names:vocal_names.append(current)
   return
  if key not in ('L','M','Q'):return
  if key=='Q':
   m=re.search(r'(?:(\d+/\d+)\s*=\s*)?(\d+(?:\.\d+)?)\s*$',value)
   if not m:raise ValueError('Tempo ABC non supportato.')
   beat=Fraction(m[1] or '1/4');bpm=Fraction(m[2])
   if beat<=0 or bpm<=0:raise ValueError('Tempo ABC non valido.')
   target,value='whole_seconds',60/(beat*bpm)
  else:
   target='unit' if key=='L' else 'meter'
   value=Fraction({'C':'4/4','C|':'2/2'}.get(value.strip(),value.strip()))
   if value<=0:raise ValueError('Durata ABC non valida.')
  if not body or key=='Q':
   defaults[target]=value
   for v in voices.values():v[target]=value
  else:state()[target]=value
 def length(text):
  if not text:return Fraction(1)
  if '/' not in text:return Fraction(int(text))
  parts=text.split('/')
  if len(parts)==2:return Fraction(int(parts[0] or 1),int(parts[1] or 2))
  if any(parts[1:]):raise ValueError('Lunghezza ABC non supportata.')
  return Fraction(int(parts[0] or 1),2**(len(parts)-1))
 for raw in score.replace('\r','').splitlines():
  line=raw.strip()
  if not line:continue
  if line.startswith('%'):
   label=line.lstrip('%').strip()
   if re.search(r'\b(verse|chorus|bridge|intro|outro|interlude|strofa|ritornello|ponte)\b',label,re.I):
    markers.append((label,{k:v['time'] for k,v in voices.items()}))
   continue
  m=re.match(r'^([A-Za-z]):(.*)$',line)
  if m:field(m[1],m[2].strip());continue
  body=True;pos=0
  while pos<len(line):
   rest=line[pos:]
   if rest[0]=='%':break
   inline=re.match(r'^\[([VLMQ]):([^\]]+)\]',rest)
   if inline:field(inline[1],inline[2]);pos+=len(inline[0]);continue
   decoration=re.match(r'^(?:"(?:\\.|[^"\\])*"|![^!]*!|\+[^+]*\+)',rest)
   if decoration:pos+=len(decoration[0]);continue
   grace=re.match(r'^\{[^}]*\}',rest)
   if grace:pos+=len(grace[0]);continue
   tuplet=re.match(r'^\((\d+)(?::(\d*))?(?::(\d+))?',rest)
   if tuplet:
    p=int(tuplet[1]);q=int(tuplet[2] or (3 if p in (2,4,8) else 2));r=int(tuplet[3] or p)
    if not 1<=p<=16 or not 1<=q<=16 or not 1<=r<=32:raise ValueError('Gruppo ABC non supportato.')
    tuplets[current]=[Fraction(q,p),r];pos+=len(tuplet[0]);continue
   if rest.startswith(('|:',':|','::')) or rest[0] in '<>':raise ValueError('Ripetizioni o ritmi spezzati ABC non supportati dalla sincronizzazione.')
   token=re.match(r"^(?:[=_^]{0,2}[A-Ga-g][,']*|[zxZX]|\[[=_^A-Ga-g,' ]+\])([0-9]*(?:/[0-9]*)*)",rest)
   if token:
    v=state();start=v['time'];whole=v['whole_seconds']
    if whole is None:raise ValueError('Manca il tempo Q: nello spartito.')
    factor=length(token[1]);measure=rest[0] in 'ZX'
    if measure and '/' in token[1]:raise ValueError('Pausa di misura ABC non valida.')
    duration=(v['meter'] if measure else v['unit'])*factor*whole
    if current in tuplets and not measure:
     multiplier,count=tuplets[current];duration*=multiplier
     if count==1:del tuplets[current]
     else:tuplets[current][1]-=1
    if duration<=0 or duration>36000:raise ValueError('Durata ABC fuori intervallo.')
    v['time']+=duration
    if rest[0] not in 'zxZX':notes[current].append((start,v['time']))
    pos+=len(token[0]);continue
   if rest[0].isspace() or rest[0] in '|[]()-{}~.HLMOPSTuv':pos+=1;continue
   raise ValueError('Simbolo ABC non supportato dalla sincronizzazione: '+rest[0])
 candidates=[v for v in vocal_names if notes.get(v)]
 if not candidates:
  candidates=[v for v in notes if notes[v]]
  if len(candidates)!=1:raise ValueError('Parte vocale ABC non identificabile.')
 vocal=candidates[0];result=[]
 for index,(label,times) in enumerate(markers):
  start=times.get(vocal,Fraction(0));end=markers[index+1][1].get(vocal,Fraction(0)) if index+1<len(markers) else math.inf
  first=next((a for a,b in notes[vocal] if a>=start and a<end),None)
  if first is not None:result.append({'label':label,'start':round(float(first),6)})
 return result


def schedule(score,lyrics):
 try:sections=score_sections(score)
 except (ValueError,ZeroDivisionError,OverflowError) as e:return {'status':'unsupported_score','reason':str(e),'sections':[]}
 blocks=lyric_blocks(lyrics);rows=[];next_block=0;matched=set()
 for section in sections:
  if instrumental(section['label']):continue
  index=next((i for i in range(next_block,len(blocks)) if blocks[i]['sung'] and kind(blocks[i]['label'])==kind(section['label'])),None)
  if index is None:continue
  block=blocks[index];next_block=index+1
  matched.add(index)
  rows.append({'label':block['label'],'start':section['start'],
               'byte_start':len(lyrics[:block['start']].encode('utf-8')),
               'byte_end':len(lyrics[:block['end']].encode('utf-8'))})
 if len(rows)>128 or any(not 0<=s['start']<=900 for s in rows):
  return {'status':'unsupported_score','reason':'Sezioni fuori dai limiti di durata supportati.','sections':[]}
 return {'status':'enabled' if rows else 'missing_sections','bias':BIAS,'sections':rows,
         'unmatched_blocks':sum(b['sung'] for b in blocks)-len(rows),
         'unmatched_labels':[b['label'] for i,b in enumerate(blocks) if b['sung'] and i not in matched]}


@lru_cache(maxsize=8)
def _supports(path,size,mtime):
 try:return b'h3_lyric_schedule_file' in Path(path).read_bytes()
 except OSError:return False


def supported(engine):
 try:
  p=Path(engine);s=p.stat();return _supports(str(p),s.st_size,s.st_mtime_ns)
 except OSError:return False


def prepare(app,req,folder,kind='generate'):
 report={'status':'disabled','sections':[]}
 if req.get('words_follow_score',False):
  if kind=='plan' or not req.get('abc'):report['status']='no_score'
  elif req.get('options',{}).get('cfg_scale',1)!=1:report['status']='cfg_not_one'
  else:
   report=schedule(req['abc'],req['lyrics'])
   if report['sections'] and not supported(app.ENGINE):report['status']='unsupported_engine'
 app.write_json(folder/'lyric-schedule.json',report)
 if report['status']!='enabled':return {}
 path=folder/'lyric-schedule.tsv'
 path.write_text(''.join(f"{s['start']:.6f}\t{s['byte_start']}\t{s['byte_end']}\n" for s in report['sections']),encoding='utf-8',newline='\n')
 return {'h3_lyric_schedule_file':str(path)}
