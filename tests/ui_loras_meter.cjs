const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const base=process.env.H3_TEST_URL,live=await p.request.get(base+'/api/state').then(r=>r.json()),abc='X:1\nM:4/4\nL:1/8\nK:C\nC2-C2 D2 z2|';let calls=0,mutations=0;
 await p.route('**/api/**',async route=>{const req=route.request(),path=new URL(req.url()).pathname.slice(5);let result;
  if(path==='state')result={...live,projects:[],jobs:[]};
  else if(path==='voices')result={voices:[]};
  else if(path==='imports')result={sources:[]};
  else if(path==='lyrics/context')result={abc:req.postDataJSON().request.abc,source:'spartito della bozza'};
  else if(path==='lyrics/adapt'){const body=req.postDataJSON();assert.equal(body.request.lora,'notte');assert.equal(body.phrases.length,1);assert.equal(body.phrases[0].notes.length,2);assert.equal(body.phrases[0].notes[0].duration,.5);assert.equal(body.mode,'translate');calls++;result={request:{...body.request,lyrics:'[Verse]\nCanto'},lines:[{id:1,syllables_min:2,syllables_max:2,target_min:2,target_max:2,fits:true}],warnings:['Conteggi stimati']}}
  else if(req.method()==='POST'){mutations++;throw Error('Unexpected mutation '+path)}
  else return route.continue();await route.fulfill({json:result});
 });
 await p.goto(base+'/#studio');await p.locator('#lora').waitFor();assert.equal(await p.locator('#lora').inputValue(),'');assert.equal(await p.locator('#lora option').count(),5);
 await p.locator('#lora').selectOption('notte');await p.locator('#title').fill('Originale');await p.locator('#style').fill('rock');await p.locator('#lyrics').fill('[Verse]\nForeign words');await p.locator('#score-details').evaluate(e=>e.open=true);await p.locator('#abc').fill(abc);
 await p.locator('#lyrics-meter').click();await p.locator('#meter-mode').selectOption('translate');await p.locator('#meter-instruction').fill('Mantieni il significato');await p.locator('#meter-run').click();await p.locator('#meter-apply').waitFor();assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nForeign words');await p.locator('#meter-apply').click();assert.equal(await p.locator('#lyrics').inputValue(),'[Verse]\nCanto');assert.equal(await p.locator('#abc').inputValue(),abc);assert.equal(await p.locator('#style').inputValue(),'rock');assert.equal(await p.locator('#lora').inputValue(),'notte');assert.equal(calls,1);assert.equal(mutations,0);
 const repeat=await p.evaluate(()=>meterPhrases('X:1\nM:4/4\nL:1/8\nK:C\n|: C D :|').flatMap(p=>p.notes).length);assert.equal(repeat,4);
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 assert.deepEqual(errors,[]);console.log('PASS: optional LoRA default/selection, meter ties/repeats, translation proposal/review, lyrics-only application, preserved melody/settings, mobile');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
