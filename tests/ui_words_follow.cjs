const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],submitted=[];
  p.on('pageerror',e=>errors.push(e.message));
  const base=process.env.H3_TEST_URL;assert.ok(base,'Use isolated fixture');
  await p.route('**/api/jobs',async route=>{
   if(route.request().method()!=='POST')return route.continue();
   submitted.push(route.request().postDataJSON());await route.fulfill({json:{ids:[]}});
  });
  await p.goto(base+'/#studio');const flag=p.locator('#words-follow-score');await flag.waitFor();
  assert.equal(await flag.isChecked(),true);
  const lyrics='[Verse]\nLa voce seguirà\n[Chorus]\nLe note resteranno';
  const abc='X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\n% verse\nC8|\n% chorus\nD8|';
  await p.locator('#style').fill('Italian acoustic pop');await p.locator('#lyrics').fill(lyrics);
  await p.locator('#score-details').evaluate(e=>e.open=true);await p.locator('#abc').fill(abc);
  await flag.uncheck();await p.locator('#generate').click();await p.waitForFunction(()=>!document.querySelector('#generate').disabled);
  assert.equal(submitted[0].request.words_follow_score,false);
  await p.reload();await flag.waitFor();assert.equal(await flag.isChecked(),false);
  await flag.check();await p.locator('#generate').click();await p.waitForFunction(()=>!document.querySelector('#generate').disabled);
  assert.equal(submitted[1].request.words_follow_score,true);
  assert.equal(submitted[1].request.lyrics,lyrics);assert.equal(submitted[1].request.abc,abc);
  assert.equal(submitted[1].request.style,'Italian acoustic pop');
  await p.reload();await flag.waitFor();assert.equal(await flag.isChecked(),true);
  const hint=await p.evaluate(()=>lyricScheduleHint({result:{words_follow_score:{status:'enabled',sections:[{},{}],unmatched_blocks:1,unmatched_labels:['Verse 2']}}}));
  assert.match(hint,/2 sezioni/);assert.match(hint,/Verse 2/);
  await p.setViewportSize({width:390,height:844});assert.equal(await flag.isVisible(),true);
  assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
  assert.deepEqual(errors,[]);console.log('PASS: score-follow flag optional, saved/reloaded, prompts intact, actual status and unmatched tags, mobile');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
