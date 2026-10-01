const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;assert.ok(base,'Use the isolated fixture server');
  const live=await p.request.get(base+'/api/state').then(r=>r.json()),submitted=[],jobs=[],projects=[];
  const source={id:'a'.repeat(32),name:'La canzone originale.wav',duration:200,url:'/imports/'+'a'.repeat(32)+'/audio'};
  let uploads=0;
  await p.route('**/api/**',async route=>{
   const request=route.request(),path=new URL(request.url()).pathname.slice(5);let result;
   if(path==='state')result={...live,projects,jobs};
   else if(path==='imports')result={sources:[source]};
   else if(path==='voices')result={voices:[{name:'campione',label:'La mia voce'}]};
   else if(path==='audio/upload'){uploads++;assert.match(request.headers()['x-filename'],/Nuova/);result=source;}
   else if(path==='projects'&&request.method()==='POST'){
    const body=request.postDataJSON();result={id:'b'.repeat(32),request:body.request,title:body.request.title};projects[0]=result;
   }else if(path==='jobs'&&request.method()==='POST'){
    const body=request.postDataJSON();submitted.push(body);const id=String(submitted.length).repeat(32);
    jobs.unshift({id,project_id:body.project_id,kind:'generate',status:'queued',request:structuredClone(body.request),result:{},created:Date.now()/1000+submitted.length});result={ids:[id]};
   }else return route.continue();
   await route.fulfill({json:result});
  });
  await p.goto(base+'/#studio');await p.locator('#base-enabled').waitFor();
  assert.equal(await p.locator('#base-fields').isVisible(),false);
  assert.equal(await p.locator('#plan').isEnabled(),true);
  await p.locator('#lyrics').fill('[Verse]\nLe parole nuove');
  await p.locator('#base-enabled').check();assert.equal(await p.locator('#base-fields').isVisible(),true);
  assert.equal(await p.locator('#plan').isDisabled(),true);assert.equal(await p.locator('#abc').isDisabled(),true);
  assert.equal(await p.locator('#studio-mix-fields').isVisible(),true);
  await p.locator('#base-source').selectOption(source.id);
  await p.locator('#base-fields details').evaluate(e=>e.open=true);
  await p.locator('#base-start').fill('18.53');await p.locator('#base-end').fill('43.47');
  await p.locator('#generate').click();await p.waitForFunction(()=>document.querySelector('#toast').textContent==='Lavoro accodato');
  assert.equal(submitted[0].kind,'generate');assert.equal(submitted[0].request.base_enabled,true);
  assert.equal(submitted[0].request.base_import_id,source.id);assert.equal(submitted[0].request.base_start,18.53);
  assert.equal(submitted[0].request.base_end,43.47);assert.equal(submitted[0].request.clone_enabled,false);
  assert.equal(submitted[0].request.style,'');assert.equal(submitted[0].request.options.num_inference_steps,48);
  jobs[0].status='completed';jobs[0].result={duration:200,regenerated_vocals:true};
  await p.evaluate(async()=>{while(polling)await new Promise(r=>setTimeout(r,20));await window.eval('refresh()')});
  await p.locator('#studio-result-audio').waitFor();assert.equal(await p.locator('#studio-result-score').isDisabled(),true);
  await p.locator('#clone-enabled').check();await p.locator('#studio-voice').selectOption('campione');
  await p.locator('#studio-result-generate').click();await p.waitForFunction(()=>!document.querySelector('#generate').disabled);
  assert.equal(submitted.length,2);assert.equal(submitted[1].request.clone_enabled,true);assert.equal(submitted[1].request.clone_voice,'campione');
  await p.reload();await p.locator('#base-source').waitFor();await p.waitForFunction(()=>document.querySelector('#base-source').value.length===32);
  assert.equal(await p.locator('#base-enabled').isChecked(),true);assert.equal(await p.locator('#base-start').inputValue(),'18.53');
  await p.locator('#base-upload').setInputFiles({name:'Nuova canzone.wav',mimeType:'audio/wav',buffer:Buffer.from('test')});
  await p.waitForFunction(()=>document.querySelector('#base-start').value==='0');assert.equal(uploads,1);assert.equal(await p.locator('#base-end').inputValue(),'0');
  await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  await p.locator('#base-enabled').uncheck();assert.equal(await p.locator('#plan').isEnabled(),true);assert.equal(await p.locator('#abc').isEnabled(),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: Base originale flag, uploads, saved range, default 48 steps, optional clone, results in Studio, reload, mobile, normal creation preserved');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
