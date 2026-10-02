const {chromium}=require('playwright'),assert=require('node:assert/strict'),http=require('node:http');
(async()=>{
 const calls=[];let authFailure=false;
 const provider=http.createServer(async(req,res)=>{
  let text='';for await(const chunk of req)text+=chunk;
  const body=text?JSON.parse(text):null;calls.push({path:req.url,auth:req.headers.authorization,body});
  res.setHeader('Content-Type','application/json');
  if(authFailure){res.statusCode=401;res.end(JSON.stringify({error:{message:'Invalid credentials'}}));return}
  if(req.url==='/v1/models'){res.end(JSON.stringify({data:[{id:'fake-chat'},{id:'other-chat'}]}));return}
  const meter=body.messages.find(m=>m.content.includes('"phrases":'));
  const content=meter?JSON.stringify({lines:[{id:1,section:'Verse',text:'Canto'}]}):JSON.stringify({lyrics:'[Verse]\nCanto'});
  res.end(JSON.stringify({choices:[{message:{content},finish_reason:'stop'}]}));
 });
 await new Promise(r=>provider.listen(0,'127.0.0.1',r));
 const endpoint='http://127.0.0.1:'+provider.address().port+'/v1';
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;
  await p.route('**/api/system',route=>route.fulfill({json:{ready:true,backend:'cpu',backends:['cpu','cuda'],memory:{},cuda:{},gpu:'',version:'test',transcription:{}}}));
  await p.goto(base+'/#system');await p.locator('#s-provider').selectOption('api');
  assert.equal(await p.locator('#api-assistant').isVisible(),true);assert.equal(await p.locator('#external-assistant').isVisible(),false);assert.equal(await p.locator('#internal-assistant').isVisible(),false);
  await p.locator('#s-api-preset').selectOption('deepseek');assert.equal(await p.locator('#s-api-url').inputValue(),'https://api.deepseek.com');
  await p.locator('#s-api-preset').selectOption('openrouter');assert.equal(await p.locator('#s-api-url').inputValue(),'https://openrouter.ai/api/v1');
  await p.locator('#s-api-url').fill(endpoint);await p.locator('#s-api-key').fill('fake-ui-secret');
  await p.locator('#api-models').click();await p.waitForFunction(()=>document.querySelector('#api-assistant-status').textContent.includes('2 modelli'));
  assert.equal(calls[0].auth,'Bearer fake-ui-secret');assert.equal(await p.locator('#s-api-key').inputValue(),'');
  const publicState=await p.request.get(base+'/api/state').then(r=>r.json());
  assert.equal(publicState.settings.llm_api_key_saved,true);assert.equal(JSON.stringify(publicState).includes('fake-ui-secret'),false);
  assert.equal(publicState.settings.backend,'cpu');assert.equal(publicState.settings.model,'q4');
  await p.locator('#s-api-model').fill('fake-chat');await p.locator('#preferences').click();
  await p.waitForFunction(()=>document.querySelector('#toast').textContent==='Preferenze salvate');
  await p.reload();await p.locator('#s-api-model').waitFor();assert.equal(await p.locator('#s-api-model').inputValue(),'fake-chat');assert.equal(await p.locator('#s-api-key').inputValue(),'');
  await p.locator('[data-page="studio"]').click();await p.locator('#lyrics').fill('[Verse]\nWords');
  await p.locator('#abc').evaluate(e=>{e.value='X:1\nM:4/4\nL:1/8\nK:C\nC D |';e.dispatchEvent(new Event('input',{bubbles:true}))});
  await p.locator('#assist').click();await p.locator('#instruction').fill('Adatta queste parole');await p.locator('#ai-run').click();await p.locator('#ai-apply').waitFor();
  assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nWords');await p.locator('#ai-apply').click();assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nCanto');
  await p.locator('#lyrics-meter').click();await p.locator('#meter-mode').waitFor();assert.match(await p.locator('#modal-content').innerText(),/servizio API/);await p.locator('#meter-run').click();await p.locator('#meter-apply').waitFor();await p.locator('#modal .close').click();
  assert.equal(calls.filter(c=>c.path==='/v1/chat/completions').length,2);assert.ok(calls.every(c=>c.auth==='Bearer fake-ui-secret'));
  // Failure stays in the dialog's top layer after the background toast expires.
  authFailure=true;await p.locator('#lyrics-meter').click();await p.locator('#meter-mode').waitFor();await p.locator('#meter-run').click();
  await p.locator('#modal-error').waitFor();assert.match(await p.locator('#modal-error').innerText(),/Chiave API/);
  await p.locator('#error-popup').waitFor();assert.equal(await p.locator('#error-popup').evaluate(e=>e.open),true);
  assert.equal(await p.locator('#error-popup-message').evaluate(e=>{const r=e.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return hit===e||e.contains(hit)}),true);
  assert.equal(await p.locator('#error-popup').evaluate(e=>getComputedStyle(e).filter),'none');
  await p.screenshot({path:require('node:path').join(process.env.H3_TEST_OUTPUT||require('node:os').tmpdir(),'h3-api-error-popup.png')});
  await p.waitForTimeout(9500);assert.equal(await p.locator('#modal-error').isVisible(),true);assert.equal(await p.locator('#modal').evaluate(e=>e.open),true);
  assert.equal(await p.locator('#meter-proposal').count(),0);assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nCanto');
  await p.locator('#error-popup-dismiss').click();assert.equal(await p.locator('#modal-error').isVisible(),true);
  authFailure=false;await p.locator('#meter-run').click();await p.locator('#meter-apply').waitFor();assert.equal(await p.locator('#modal-error').count(),0);await p.locator('#modal .close').click();
  authFailure=true;await p.locator('#assist').click();await p.locator('#instruction').fill('Riprova');await p.locator('#ai-run').click();await p.locator('#modal-error').waitFor();assert.match(await p.locator('#modal-error').innerText(),/Chiave API/);await p.locator('#error-popup-dismiss').click();await p.locator('#modal .close').click();
  await p.locator('[data-page="system"]').click();authFailure=true;await p.locator('#api-models').click();await p.waitForFunction(()=>document.querySelector('#api-assistant-status').textContent.includes('Chiave API'));
  await p.locator('#s-api-clear-key').check();await p.locator('#preferences').click();
  await p.waitForFunction(()=>document.querySelector('#api-key-status').textContent.includes('viene salvata'));
  assert.equal((await p.request.get(base+'/api/state').then(r=>r.json())).settings.llm_api_key_saved,false);
  await p.locator('#s-provider').selectOption('lmstudio');assert.equal(await p.locator('#external-assistant').isVisible(),true);assert.equal(await p.locator('#api-assistant').isVisible(),false);
  await p.locator('#s-provider').selectOption('api');await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);console.log('PASS: API presets, real local HTTP provider, key privacy/save/remove, models, assistant and metric proposals, persistent preferences, errors, local provider and mobile');
 }finally{await browser.close();await new Promise(r=>provider.close(r))}
})().catch(e=>{console.error(e);process.exit(1)});
