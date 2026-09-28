const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');

(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL||'http://127.0.0.1:8776';
  const live=await p.request.get(base+'/api/state').then(r=>r.json());
  const request={title:'Una nuova canzone',style:'Italian pop',lyrics:'[Verse]\nLa prima luce',abc:'',notes:'',cot:'full',seed:42,options:{},clone_enabled:false,voice_steps:30};
  const project='a'.repeat(32),jobs=[],projects=[{id:project,title:request.title,request}],submitted=[];
  const abc='X:1\nT:Una nuova canzone\n\nK:C\nCDEF |';
  const wav=Buffer.alloc(44+48000*2*8);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(48000,24);wav.writeUInt32LE(96000,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(wav.length-44,40);
  await p.route('**/files/**',r=>r.fulfill({contentType:'audio/wav',body:wav}));
  await p.route('**/api/**',async route=>{
   const req=route.request(),path=new URL(req.url()).pathname.slice(5);
   let result;
   if(path==='state')result={...live,projects,jobs};
   else if(path==='voices')result={voices:[]};
   else if(path==='projects'&&req.method()==='POST'){
    const body=req.postDataJSON(),id=body.id||'b'.repeat(32);result={id,title:body.request.title,request:body.request};
    const old=projects.findIndex(x=>x.id===id);if(old<0)projects.push(result);else projects[old]=result;
   }else if(path==='jobs'&&req.method()==='POST'){
    const body=req.postDataJSON();submitted.push(body);
    const j={id:String(submitted.length).repeat(32),project_id:body.project_id,kind:body.kind,status:'queued',request:structuredClone(body.request),result:{},created:Date.now()/1000+submitted.length,files:[]};jobs.unshift(j);result={ids:[j.id]};
   }else if(path.startsWith('jobs/'))result={...jobs.find(j=>j.id===path.slice(5)),abc,files:[],log:''};
   else if(req.method()==='GET')return route.continue();
   else throw Error('Unexpected API write: '+path);
   await route.fulfill({json:result});
  });
  await p.addInitScript(({project,request})=>{if(!localStorage.getItem('h3-music-draft'))localStorage.setItem('h3-music-draft',JSON.stringify({id:project,request}))},{project,request});
  const refresh=()=>p.evaluate(async()=>{while(polling)await new Promise(r=>setTimeout(r,20));await window.eval('refresh()')});
  await p.goto(base);await p.locator('#generate').waitFor();assert.equal(await p.locator('#studio-result-audio').count(),0);
  await p.locator('#generate').click();await p.waitForFunction(()=>document.querySelector('#toast').textContent==='Lavoro accodato');
  const first=jobs[0];first.status='running';first.progress={pct:50,stage:'Sintesi',elapsed_s:12};await refresh();assert.match(await p.locator('#active-strip').innerText(),/In corso/);
  await p.locator('#lyrics').fill('[Verse]\nParole modificate durante la generazione');
  first.status='completed';first.result={duration:8};await refresh();await p.locator('#studio-result-audio').waitFor();
  assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nParole modificate durante la generazione');
  assert.equal(await p.locator('#active-strip').innerText(),'');
  await p.locator('#studio-result-score').click();await p.waitForFunction(abc=>document.querySelector('#abc').value===abc,abc);
  assert.match(await p.locator('#lyrics').inputValue(),/Parole modificate/);
  await p.evaluate(async()=>{window.savedPlayer=document.querySelector('#studio-result-audio');savedPlayer.loop=true;await savedPlayer.play();savedPlayer.currentTime=2});
  await p.waitForFunction(()=>!savedPlayer.seeking);const playback=await p.evaluate(()=>savedPlayer.currentTime);await refresh();assert.equal(await p.evaluate(()=>savedPlayer===document.querySelector('#studio-result-audio')&&!savedPlayer.paused),true);assert.ok(await p.evaluate(()=>savedPlayer.currentTime)>=playback);
  await p.locator('#studio-result-generate').click();await p.waitForFunction(()=>!document.querySelector('#generate').disabled);
  assert.equal(submitted.length,2);assert.equal(submitted[1].request.abc,abc);assert.match(submitted[1].request.lyrics,/Parole modificate/);
  const second=jobs[0];second.status='completed';second.result={duration:8};await refresh();
  assert.equal(await p.locator('#studio-result-version').inputValue(),first.id);
  await p.evaluate(()=>savedPlayer.pause());await p.locator('#studio-result-version').selectOption(second.id);await refresh();
  assert.match(await p.locator('#studio-result-audio').getAttribute('src'),new RegExp(second.id));
  await p.locator('#studio-result-version').selectOption(first.id);await refresh();assert.equal(await p.locator('#studio-result-version').inputValue(),first.id);
  jobs.unshift({...second,id:'f'.repeat(32),project_id:'unrelated',request:{...request,title:'Altro progetto'}});await refresh();assert.equal(await p.locator('#studio-result-version option').count(),2);
  await p.reload();await p.locator('#studio-result-audio').waitFor();assert.equal(await p.locator('#studio-result-version').inputValue(),second.id);
  await p.locator('[data-page="library"]').click();await p.locator('[data-page="studio"]').click();await p.locator('#studio-result-audio').waitFor();
  fs.mkdirSync('tests/tmp-studio-result',{recursive:true});await p.screenshot({path:'tests/tmp-studio-result/desktop.png',fullPage:true});
  await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);await p.screenshot({path:'tests/tmp-studio-result/mobile.png',fullPage:true});
  await p.locator('#new').click();await p.waitForFunction(()=>document.querySelector('#title').value==='');assert.equal(await p.locator('#studio-result-audio').count(),0);
  await p.locator('#projects').selectOption(project);await p.locator('#studio-result-audio').waitFor();
  jobs.unshift({...second,id:'e'.repeat(32),kind:'plan'});await refresh();assert.equal(await p.locator('#studio-result-audio').count(),0);assert.match(await p.locator('#studio-result-player').innerText(),/Spartito pronto/);
  await p.evaluate(id=>detail(id),second.id);await p.locator('#use').click();await p.locator('#studio-result-audio').waitFor();
  assert.equal(await p.locator('#projects').inputValue(),'');assert.equal(await p.locator('#studio-result-version').inputValue(),second.id);
  await p.reload();await p.locator('#studio-result-audio').waitFor();assert.equal(await p.locator('#studio-result-version').inputValue(),second.id);
  await p.locator('#new').click();await p.waitForFunction(()=>document.querySelector('#title').value==='');assert.equal(await p.locator('#studio-result-audio').count(),0);
  assert.deepEqual(errors,[]);
  console.log('PASS: generation completion, preserved edits/playback, ABC reuse, regeneration payload, variants, project isolation, reload/navigation, new project, plan, desktop/mobile');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
