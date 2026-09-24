import pathlib,json,urllib.request,subprocess,hashlib,re,time
root=pathlib.Path(__file__).resolve().parents[1];base='http://127.0.0.1:8776/api/'
def call(p,d=None):
 req=urllib.request.Request(base+p,data=json.dumps(d,ensure_ascii=False).encode() if d else None,headers={'Content-Type':'application/json','X-H3-Music':'1'})
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
id='24712e7f52c94df7aa0fcde44ff17974';j=call('jobs/'+id);assert j['status']=='completed'
source=root/'data/outputs'/id/'audio.wav';before=hashlib.sha256(source.read_bytes()).hexdigest();exports=[]
for fmt in ['wav','flac','mp3','ogg']:
 d={'id':id,'format':fmt,'start':1,'end':8,'gain':-1,'fade':.2,'normalize':True}
 out=call('export',d);file=root/'data/outputs'/id/out['name']
 probe=subprocess.run([str(root/'runtime/ffprobe.exe'),'-v','error','-select_streams','a:0','-show_entries','stream=sample_rate,channels,bits_per_raw_sample:format=duration','-of','json',str(file)],capture_output=True,text=True,creationflags=0x08000000)
 assert probe.returncode==0;info=json.loads(probe.stdout);assert 6.9<float(info['format']['duration'])<7.2;assert int(info['streams'][0]['sample_rate'])==48000;assert info['streams'][0]['channels']==2
 if fmt=='wav':assert info['streams'][0]['bits_per_raw_sample']=='24'
 exports.append({'format':fmt,'name':out['name'],'info':info})
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
score='\n'.join(line if re.match(r'^[A-Za-z]:|^%',line) else re.sub(r'"[^"\r\n]*"','',line) for line in j['abc'].splitlines())
assert 'name="Vocal Melody"' in score
request=j['request']|{'title':'Prima luce · jazz cover','style':'English, jazz funk, warm relaxed lead vocal, Rhodes piano, round bass, brushed drums, mellow live band feel, 100 BPM','abc':score,'cot':'melody'}
p=call('projects',{'request':request});jobs=call('jobs',{'project_id':p['id'],'kind':'generate'})
(root/'logs/audio-tests.json').write_text(json.dumps({'export_checks':True,'source_preserved':True,'exports':exports,'cover_job':jobs['ids'][0]},indent=2),encoding='utf-8')
print('Four export formats passed; cover queued '+jobs['ids'][0],flush=True)
