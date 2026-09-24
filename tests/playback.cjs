const {chromium}=require('C:/Users/emanu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');
(async()=>{const b=await chromium.launch({headless:true,channel:'msedge'}),p=await b.newPage({viewport:{width:1440,height:1050}});await p.goto('http://127.0.0.1:8776/#library');await p.locator('#tracks audio').first().waitFor();await p.waitForFunction(()=>[...document.querySelectorAll('#tracks audio')].every(a=>Number.isFinite(a.duration)&&a.duration>1));
await p.locator('[data-compare]').nth(0).click();await p.locator('[data-compare]').nth(1).click();await p.waitForFunction(()=>[...document.querySelectorAll('#compare audio')].every(a=>Number.isFinite(a.duration)));
await p.locator('#compare audio').nth(0).evaluate(a=>a.play());await p.waitForFunction(()=>document.querySelector('#compare audio').currentTime>.1);
await p.locator('#compare audio').nth(1).evaluate(a=>a.play());await p.waitForFunction(()=>{const a=document.querySelectorAll('#compare audio');return a[0].paused&&!a[1].paused});
const durations=await p.locator('#compare audio').evaluateAll(els=>els.map(a=>a.duration));await p.locator('#compare audio').nth(1).evaluate(a=>a.pause());
await p.screenshot({path:'F:/H3-Music/docs/library.png',fullPage:true});fs.writeFileSync('F:/H3-Music/logs/playback-tests.json',JSON.stringify({passed:true,durations,checks:['metadata','audio playback','exclusive A/B playback']},null,2));await b.close();console.log('Playback passed',durations)})().catch(e=>{console.error(e);process.exit(1)});
