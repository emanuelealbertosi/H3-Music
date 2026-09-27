const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));const base='http://127.0.0.1:8777';
 await p.goto(base);await p.locator('#clone-enabled').check();await p.locator('#studio-mix-auto').waitFor();assert(await p.locator('#studio-mix-auto').isChecked());
 await p.locator('#studio-mix-balance').fill('-3');await p.locator('#studio-mix-ambience').fill('25');await p.reload();await p.locator('#studio-mix-balance').waitFor();assert.equal(await p.locator('#studio-mix-balance').inputValue(),'-3');
 await p.locator('[data-page="voice"]').click();await p.locator('#song-mix-balance').fill('-2');await p.locator('[data-page="studio"]').click();await p.locator('[data-page="voice"]').click();assert.equal(await p.locator('#song-mix-balance').inputValue(),'-2');
 await p.locator('[data-page="library"]').click();await p.locator('[data-detail="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]').click();await p.locator('.mix-session summary').click();
 await p.locator('#session-mix-balance').fill('-4');await p.locator('#session-mix-ambience').fill('30');
 await p.screenshot({path:'tests/tmp-mix-ui/desktop.png',fullPage:true});await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);await p.screenshot({path:'tests/tmp-mix-ui/mobile.png',fullPage:true});
 const response=p.waitForResponse(r=>r.url().endsWith('/api/jobs')&&r.request().method()==='POST');await p.locator('#remix-run').click();const r=await response;assert.equal(r.status(),200);const id=(await r.json()).ids[0];
 const job=await p.request.get(base+'/api/jobs/'+id).then(r=>r.json());assert.equal(job.kind,'remix');assert.equal(job.request.mix.voice_db,-4);assert.equal(job.request.mix.ambience,30);
 const retry=await p.request.post(base+'/api/jobs/retry',{headers:{'X-H3-Music':'1'},data:{id}});assert.equal(retry.status(),200);const rid=(await retry.json()).ids[0];const retried=await p.request.get(base+'/api/jobs/'+rid).then(r=>r.json());assert.deepEqual(retried.request,job.request);
 const cancel=await p.request.post(base+'/api/jobs/cancel',{headers:{'X-H3-Music':'1'},data:{id}});assert.equal(cancel.status(),200);
 assert.deepEqual(errors,[]);console.log('PASS: persisted mix controls, session remix, request snapshot, retry/cancel, desktop/mobile, no JS errors');
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
