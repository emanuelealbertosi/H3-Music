const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const base=process.env.H3_TEST_URL||'http://127.0.0.1:8776';const state=await p.request.get(base+'/api/state').then(r=>r.json());
 state.projects=[];state.jobs=[1,2,3].map(i=>({id:String(i).repeat(32),kind:'generate',status:'completed',favorite:0,created:i,files:[],request:{title:i===3?'Altro brano':'Prova '+i,style:'pop',seed:i,cot:'full',options:{}},result:{duration:8}}));
 const calls=[];let reject=false;
 await p.route('**/files/**',r=>r.fulfill({status:204}));
 await p.route('**/api/**',async r=>{const path=new URL(r.request().url()).pathname;
  if(path==='/api/state')return r.fulfill({json:state});
  if(path==='/api/jobs/delete'){
   const ids=r.request().postDataJSON().ids;calls.push(ids);
   if(reject)return r.fulfill({status:400,json:{error:'Il brano serve ancora a un lavoro in corso.'}});
   state.jobs=state.jobs.filter(j=>!ids.includes(j.id));return r.fulfill({json:{deleted:ids,missing:[],errors:[]}});
  }
  if(r.request().method()!=='GET')throw Error('Unexpected mutation '+path);return r.continue();
 });
 await p.goto(base+'/#library');await p.locator('[data-delete-job]').first().waitFor();
 assert.equal(await p.locator('#library-delete-selected').isDisabled(),true);
 await p.locator('[data-delete-job]').first().click();await p.locator('#library-delete-cancel').click();assert.equal(calls.length,0);
 await p.locator('[data-select-job]').first().check();await p.locator('#search').fill('Altro');
 assert.match(await p.locator('#library-selected-count').innerText(),/^1 /);
 await p.locator('#library-select-all').check();assert.match(await p.locator('#library-selected-count').innerText(),/^2 /);
 await p.locator('#library-delete-selected').click();assert.equal(await p.locator('.delete-job-list li').count(),2);
 reject=true;await p.locator('#library-delete-confirm').click();await p.locator('#library-delete-error').getByText('Il brano serve ancora a un lavoro in corso.').waitFor();assert.equal(state.jobs.length,3);
 reject=false;await p.locator('#library-delete-confirm').click();await p.waitForFunction(()=>!document.querySelector('#modal').open);
 assert.deepEqual(new Set(calls[1]),new Set(['1'.repeat(32),'3'.repeat(32)]));assert.equal(state.jobs.length,1);
 await p.locator('#search').fill('');assert.equal(await p.locator('[data-select-job]').count(),1);assert.match(await p.locator('#library-selected-count').innerText(),/^0 /);
 await p.setViewportSize({width:390,height:844});assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
 fs.mkdirSync('tests/tmp-library-cleanup',{recursive:true});await p.screenshot({path:'tests/tmp-library-cleanup/mobile.png',fullPage:true});
 await p.locator('[data-delete-job]').click();await p.locator('#library-delete-confirm').click();await p.waitForFunction(()=>!document.querySelector('#modal').open);
 assert.equal(await p.locator('[data-select-job]').count(),0);assert.equal(await p.locator('#library-delete-selected').isDisabled(),true);assert.deepEqual(errors,[]);
 console.log('PASS: single deletion, cancellation, selection across filters, select visible, dependency rejection, batch confirmation, empty library, mobile layout');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
