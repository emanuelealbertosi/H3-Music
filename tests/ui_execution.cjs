const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
 const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 const base=process.env.H3_TEST_URL||'http://127.0.0.1:8777';
 await p.goto(base);await p.locator('#title').waitFor();
 await p.locator('#title').fill('Regressione interfaccia');
 await p.locator('#save').click();await p.getByText('Progetto salvato',{exact:true}).first().waitFor();
 for(const page of ['library','queue','transcribe','guide','system']){
  await p.locator(`[data-page="${page}"]`).click();
  if(page==='system')await p.locator('#s-backend').waitFor();
 }
 assert.equal(await p.locator('#s-backend').inputValue(),'cpu');
 assert.deepEqual(await p.locator('#s-backend option').evaluateAll(es=>es.map(e=>e.value)),['cpu','cuda']);
 await p.getByText(/Per preparare o aggiornare la GPU/).waitFor();
 await p.locator('#s-threads').fill('6');await p.locator('#s-quality').selectOption('q4');
 await p.locator('#preferences').click();await p.getByText('Preferenze salvate',{exact:true}).first().waitFor();
 const state=await p.request.get(base+'/api/state').then(r=>r.json());
 assert.equal(state.settings.backend,'cpu');assert.equal(state.settings.threads,6);assert.equal(state.settings.model,'q4');
 if(state.runtime.available_models?.bf16){
  await p.locator('#s-quality').selectOption('bf16');
  const saved=p.waitForResponse(r=>r.url().endsWith('/api/settings')&&r.request().method()==='POST');
  await p.locator('#preferences').click();assert.equal((await saved).status(),200);
  const bf=await p.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(bf.settings.model,'bf16');assert.equal(bf.runtime.model_variant,'bf16');assert.equal(bf.runtime.ready,true);
 }
 await p.locator('[data-page="studio"]').click();assert.equal(await p.locator('#title').inputValue(),'Regressione interfaccia');
 await p.locator('#score-details summary').click();
 await p.locator('#abc').fill('X:1\nT:Test\nM:4/4\nL:1/8\nQ:1/4=100\nK:C\nCDEF G2G2|AGFE D2C2|');
 await p.locator('#score-view').click();await p.locator('#score-preview svg').first().waitFor();
 assert.match(await p.locator('#score-midi a').getAttribute('href'),/^data:audio\/midi/);
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 assert.deepEqual(errors,[]);console.log('PASS: CPU default, explicit GPU option, BF16 when installed, preferences, navigation, project save, draft, score, MIDI, mobile, no JS errors');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
