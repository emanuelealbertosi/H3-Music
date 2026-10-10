const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],submitted=[];
  page.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;assert.ok(base,'Use isolated fixture server');
  // Real project saves and validation; only enqueue is intercepted (no fake model generation).
  await page.route('**/api/jobs',async route=>{
   if(route.request().method()!=='POST')return route.continue();
   submitted.push(route.request().postDataJSON());await route.fulfill({json:{ids:[]}});
  });
  await page.goto(base+'/#studio');const duration=page.locator('#max-duration');await duration.waitFor();
  assert.equal(await duration.inputValue(),'');
  assert.equal(await page.locator('[data-option="max_duration"]').count(),1);
  await page.locator('#title').fill('Durata facoltativa');
  const lyrics='[Verse]\nLa luce entra nella mia stanza';const style='Italian pop, piano';
  await page.locator('#lyrics').fill(lyrics);await page.locator('#style').fill(style);
  await duration.fill('180');await page.locator('#quality').selectOption('48');
  await page.locator('#generate').click();await page.waitForFunction(()=>document.querySelector('#toast').textContent==='Lavoro accodato');
  assert.equal(submitted[0].request.options.max_duration,180);
  assert.equal(submitted[0].request.options.num_inference_steps,48);
  assert.equal(submitted[0].request.style,style);assert.equal(submitted[0].request.lyrics,lyrics);
  await page.reload();await duration.waitFor();assert.equal(await duration.inputValue(),'180');
  const projectId=await page.locator('#projects').inputValue();assert.ok(projectId);
  const saved=await page.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(saved.projects.find(p=>p.id===projectId).request.options.max_duration,180);
  await page.locator('#new').click();await page.waitForFunction(()=>document.querySelector('#projects').value==='');
  assert.equal(await duration.inputValue(),'');
  await page.locator('#projects').selectOption(projectId);await page.waitForFunction(()=>document.querySelector('#max-duration').value==='180');
  await duration.fill('');await page.locator('#generate').click();await page.waitForFunction(()=>!document.querySelector('#generate').disabled);
  assert.equal(submitted.length,2);assert.equal('max_duration' in submitted[1].request.options,false);
  await duration.fill('240');await page.locator('#reset-options').evaluate(e=>e.closest('details').open=true);
  await page.locator('#reset-options').click();assert.equal(await duration.inputValue(),'');
  await page.setViewportSize({width:390,height:844});assert.equal(await duration.isVisible(),true);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);
  console.log('PASS: optional duration, request parameter, prompt preservation, saved projects, reload, reset, legacy generation, mobile');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
