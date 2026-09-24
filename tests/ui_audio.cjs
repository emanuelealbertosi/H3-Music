const {chromium}=require('C:/Users/emanu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'}),p=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 p.on('pageerror',e=>errors.push(e.message));await p.goto('http://127.0.0.1:8776');await p.locator('#title').waitFor();
 await p.locator('[data-page="library"]').click();await p.locator('[data-detail="24712e7f52c94df7aa0fcde44ff17974"]').click();await p.locator('#use').waitFor();
 await p.locator('#detail-score svg').first().waitFor();await p.locator('#wave').waitFor();
 await p.locator('#use').click();await p.locator('#abc').waitFor();
 const original=await p.locator('#abc').inputValue();if(!original.includes('name="Vocal Melody"'))throw Error('Missing source score');
 await p.locator('#remove-chords').click();const melody=await p.locator('#abc').inputValue();
 if(!melody.includes('name="Vocal Melody"')||melody.split('\n').some(l=>!/^([A-Za-z]:|%)/.test(l)&&l.includes('"')))throw Error('Chord removal corrupted headers or retained chords');
 if(await p.locator('#cot').inputValue()!=='melody')throw Error('Cover mode not set');
 await p.locator('#score-view').click();await p.locator('#score-preview svg').first().waitFor();
 await p.locator('[data-page="library"]').click();const choices=p.locator('[data-compare]');
 if(await choices.count()>=2){await choices.nth(0).click();await choices.nth(1).click();if(await p.locator('#compare audio').count()!==2)throw Error('A/B missing');}
 await p.screenshot({path:'F:/H3-Music/docs/library.png',fullPage:true});
 await p.locator('[data-page="system"]').click();await p.getByText('Pronto',{exact:true}).first().waitFor();await p.screenshot({path:'F:/H3-Music/docs/system.png',fullPage:true});
 fs.writeFileSync('F:/H3-Music/logs/ui-audio-tests.json',JSON.stringify({passed:errors.length===0,errors,checks:['actual generated ABC rendering','session to draft','cover chord removal preserves voice headers','melody mode','A/B players','runtime diagnosis']},null,2));
 await browser.close();if(errors.length)throw Error(errors.join('\n'));console.log('Generated-session UI checks passed');
})().catch(e=>{console.error(e);process.exit(1)});
