const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;assert.ok(base);
  const live=await p.request.get(base+'/api/state').then(r=>r.json());
  const source={id:'a'.repeat(32),name:'Canzone.wav',duration:30,bytes:1000,url:'/imports/'+'a'.repeat(32)+'/audio'};
  const abc='X:1\nT:Trascrizione\nM:4/4\nL:1/8\nQ:1/4=100\nK:C\nCDEF G2G2|AGFE D2C2|';
  const jobs=[],submitted=[];let currentAbc='';
  await p.route('**/api/**',async route=>{
   const request=route.request(),path=new URL(request.url()).pathname.slice(5);let result;
   if(path==='state')result={...live,projects:[],jobs,runtime:{...live.runtime,transcription:{ready:true}}};
   else if(path==='imports')result={sources:[source]};
   else if(path==='voices')result={voices:[]};
   else if(path==='jobs'&&request.method()==='POST'){
    const body=request.postDataJSON();submitted.push(body);
    const j={id:'b'.repeat(32),kind:'transcribe',status:'queued',request:{...body.request,source_name:source.name,end:30},result:{},created:Date.now()/1000};
    jobs.unshift(j);result={ids:[j.id]};
   }else if(path.startsWith('jobs/'))result={...jobs[0],abc:currentAbc,files:[{name:'transcription.mid',url:'/files/'+jobs[0].id+'/transcription.mid'}],annotations:{},log:''};
   else return route.continue();
   await route.fulfill({json:result});
  });
  const refresh=()=>p.evaluate(async()=>{while(polling)await new Promise(r=>setTimeout(r,20));await refresh()});
  await p.goto(base+'/#transcribe');await p.locator('#tr-source').selectOption(source.id);
  await p.locator('#tr-mode').selectOption('melody');await p.locator('#transcribe-run').click();
  await p.locator('#trans-progress').waitFor();assert.equal(await p.locator('#trans-cover').count(),0);
  jobs[0].status='running';await refresh();assert.equal(await p.locator('#trans-cover').count(),0);
  jobs[0].status='completed';jobs[0].result={abc_error:'Interval is shorter than the ABC subbeat grid',vocal_notes:20,elapsed_seconds:2};
  await refresh();await p.locator('#trans-score-unavailable').waitFor();
  assert.equal(await p.locator('#modal .note.green').count(),0);
  assert.equal(await p.locator('#trans-cover').count(),0);
  currentAbc=abc;jobs[0].result={abc_error:null,abc_measures:2,vocal_notes:20,elapsed_seconds:2};await refresh();
  await p.locator('#trans-score svg').first().waitFor();
  assert.equal(await p.locator('#trans-score-unavailable').count(),0);
  await p.getByText('Codice ABC',{exact:true}).click();assert.equal(await p.locator('#trans-abc').textContent(),abc);
  assert.equal(await p.locator('#trans-cover').textContent(),'Apri in Studio');
  await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await p.locator('#trans-cover').click();await p.locator('#abc').waitFor();
  assert.equal(await p.locator('#abc').inputValue(),abc);assert.equal(await p.locator('#cot').inputValue(),'melody');
  assert.equal(submitted.length,1);assert.equal(submitted[0].kind,'transcribe');
  assert.deepEqual(errors,[]);
  console.log('PASS: transcription completion, partial result warning, recovered ABC, score, Studio import, melody mode, mobile');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
