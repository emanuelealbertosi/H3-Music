const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 const base=process.env.H3_TEST_URL,live=await p.request.get(base+'/api/state').then(r=>r.json());
 let settings={...live.settings},jobs=[],prepareCount=0,jobReads=0,automatic=false,browseCalls=0;
 const id='c'.repeat(32),source='d'.repeat(32),abc='X:1\nM:4/4\nL:1/8\nK:C\nC2 D2 z2 |';
 await p.route('**/api/**',async route=>{const req=route.request(),path=new URL(req.url()).pathname.slice(5);let result;
  if(path==='state')result={...live,settings,jobs,projects:[]};
  else if(path==='settings'){settings={...settings,...req.postDataJSON()};result={ok:true}}
  else if(path==='llm/status')result={ready:true,busy:false,loaded:false,backends:['cpu','cuda']};
  else if(path==='llm/browse'){browseCalls++;result={path:browseCalls===1?'F:\\Modelli è\\Qwen.gguf':''}}
  else if(path==='voices')result={voices:[]};
  else if(path==='imports')result={sources:[{id:source,name:'Originale.mp3',duration:30,url:'/imports/'+source+'/audio'}]};
  else if(path==='lyrics/context'){
   const body=req.postDataJSON();
   if(automatic&&body.prepare){prepareCount++;assert.equal(body.request.base_import_id,source);assert.equal(body.request.base_start,4);assert.equal(body.request.base_end,20);result={job_id:'transcription',source:'originale'}}
   else result={abc,source:'melodia originale'};
  }else if(path==='jobs/transcription'){jobReads++;result={status:jobReads===1?'queued':'completed'}}
  else if(path==='jobs/'+id)result={...jobs.find(j=>j.id===id),files:[],log:'',abc:''};
  else if(req.method()==='POST')throw Error('Unexpected mutation '+path);
  else return route.continue();await route.fulfill({json:result});
 });
 await p.goto(base+'/#system');await p.locator('#s-provider').waitFor();
 assert.equal(await p.locator('#s-provider').inputValue(),'lmstudio');
 await p.locator('#s-provider').selectOption('internal');await p.locator('#assistant-status').waitFor();
 assert.equal(await p.locator('#external-assistant').isVisible(),false);
 assert.equal(await p.locator('#s-llm-device').inputValue(),'cpu');
 await p.locator('#s-llm-device').selectOption('cuda');await p.locator('#assistant-model-browse').click();
 await p.waitForFunction(()=>document.querySelector('#s-internal-model').value==='F:\\Modelli è\\Qwen.gguf');
 assert.match(await p.locator('#assistant-status').innerText(),/Salva preferenze/);
 await p.locator('#assistant-model-browse').click();await p.waitForFunction(()=>!document.querySelector('#assistant-model-browse').disabled);
 assert.equal(await p.locator('#s-internal-model').inputValue(),'F:\\Modelli è\\Qwen.gguf');assert.equal(browseCalls,2);
 await p.locator('#preferences').click();await p.waitForFunction(()=>document.querySelector('#toast').textContent==='Preferenze salvate');
 assert.equal(settings.llm_provider,'internal');assert.equal(settings.llm_device,'cuda');assert.equal(settings.backend,'cpu');assert.equal(settings.llm_context,16384);
 await p.locator('[data-page="studio"]').click();await p.locator('#base-enabled').check();await p.locator('#base-source').selectOption(source);
 await p.locator('#base-fields details').evaluate(e=>e.open=true);await p.locator('#base-start').fill('4');await p.locator('#base-end').fill('20');automatic=true;
 await p.locator('#lyrics-meter').click();await p.locator('#meter-mode').waitFor();assert.equal(prepareCount,1);assert.equal(jobReads,2);
 assert.equal(await p.locator('#abc').inputValue(),'');assert.match(await p.locator('#modal-content').innerText(),/scarica alla fine/);
 await p.locator('#modal .close').click();
 const failed={id,kind:'generate',status:'running',created:Date.now()/1000,request:{title:'Dragon Ball GT',base_enabled:true},error:'',result:{}};jobs=[failed];
 const refresh=()=>p.evaluate(async()=>{while(polling)await new Promise(r=>setTimeout(r,20));await refresh()});
 await refresh();failed.status='failed';failed.error='Il nuovo canto cambia troppo ritmo rispetto alla base.';await refresh();await p.locator('#job-error-popup').waitFor();
 assert.match(await p.locator('#job-error-popup').innerText(),/controllo di sincronia/);
 await p.waitForTimeout(9500);assert.equal(await p.locator('#job-error-popup').isVisible(),true);
 await p.locator('#job-error-dismiss').click();await refresh();assert.equal(await p.locator('#modal').evaluate(e=>e.open),false);
 await p.reload();await p.locator('#generate').waitFor();assert.equal(await p.locator('#modal').evaluate(e=>e.open),false);
 // A short operation may start and fail entirely between two refreshes.
 jobs.unshift({...failed,id:'e'.repeat(32),error:'Memoria insufficiente per allocare il modello.'});
 await refresh();await p.locator('#job-error-popup').waitFor();assert.match(await p.locator('#job-error-popup').innerText(),/esaurito la memoria/);
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 await p.locator('#job-error-dismiss').click();
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 assert.deepEqual(errors,[]);console.log('PASS: internal/external assistant preferences, independent CPU/GPU choice, automatic ABC before adaptation, selected range, unchanged draft, persistent failure popup, explicit acknowledgement, reload/mobile');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
