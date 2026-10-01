const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}), errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;
  assert.ok(base&&process.env.H3_MODEL_DESTINATION,'Use an isolated fixture server.');
  await p.goto(base+'/#system');
  await p.locator('#model-current').waitFor();
  await p.waitForFunction(()=>document.querySelector('#model-current').textContent!=='Verifica…');
  const before=await p.request.get(base+'/api/state').then(r=>r.json());
  const source=await p.request.get(base+'/api/models/location').then(r=>r.json());
  await p.locator('#model-path').fill(process.env.H3_MODEL_DESTINATION);
  const moved=p.waitForResponse(r=>r.url().endsWith('/api/models/location')&&r.request().method()==='POST');
  await p.locator('#model-apply').click();assert.equal((await moved).status(),200);
  await p.getByText('Cartella aggiornata. La nuova posizione è attiva.',{exact:true}).waitFor();
  const after=await p.request.get(base+'/api/state').then(r=>r.json());
  assert.deepEqual(after.settings,before.settings);
  assert.equal(after.runtime.ready,before.runtime.ready);assert.equal(after.runtime.ready,true);
  assert.equal(after.runtime.sep,true);assert.equal(after.runtime.voice,true);
  assert.equal(await p.locator('#model-current').textContent(),process.env.H3_MODEL_DESTINATION);
  // An invalid second move must keep the already active location.
  await p.locator('#model-path').fill('relative-folder');
  await p.locator('#model-apply').click();await p.getByText(/Indica un percorso completo/).waitFor();
  const active=await p.request.get(base+'/api/models/location').then(r=>r.json());
  assert.equal(active.path,process.env.H3_MODEL_DESTINATION);
  // Return to the original store, whose repository metadata is still there.
  await p.locator('#model-path').fill(source.path);
  await p.locator('#model-apply').click();
  await p.waitForFunction(path=>document.querySelector('#model-current').textContent===path,source.path);
  await p.setViewportSize({width:390,height:844});
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  console.log('PASS: model folder transfer, readiness, all audio modules, preferences, invalid path, return to default, mobile, no JS errors');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
