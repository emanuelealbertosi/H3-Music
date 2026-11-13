const{chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(process.env.H3_TEST_URL+'/#studio');await p.locator('#lora').waitFor();
 const lyrics='[Verse 1 — Male]\nUna voce\n[Verse 1 — Female]\nUn’altra voce';
 await p.locator('#lyrics').fill(lyrics);await p.locator('#style').fill('Italian duet');
 await p.locator('#lora').selectOption('coro');assert.match(await p.locator('#vocal-role-hint').textContent(),/baritono/);
 await p.locator('#lora').selectOption('particle-female');assert.match(await p.locator('#vocal-role-hint').textContent(),/intero brano/);
 await p.locator('#lora').selectOption('');assert.equal(await p.locator('#vocal-role-hint').isVisible(),true);
 assert.equal(await p.locator('#lyrics').inputValue(),lyrics);assert.equal(await p.locator('#style').inputValue(),'Italian duet');
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 await p.locator('#lyrics').fill('[Verse]\nUna voce');assert.equal(await p.locator('#vocal-role-hint').isVisible(),false);
 assert.deepEqual(errors,[]);console.log('PASS: duet labels, optional adapter conflicts, unchanged lyrics/style, normal songs and mobile');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
