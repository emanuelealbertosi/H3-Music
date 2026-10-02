'use strict';
function meterPhrases(abc){
 if(!window.ABCJS)throw Error('Il lettore dello spartito non è disponibile.');
 const tune=ABCJS.parseOnly(abc)[0];if(!tune)throw Error('Spartito ABC non valido.');
 const audio=tune.setUpAudio({chordsOff:true}),tracks=audio.tracks||[];
 const vocal=tracks.find(t=>t.some(e=>e.cmd==='text'&&/vocal|voce|cant/i.test(e.text||'')))||tracks.find(t=>t.some(e=>e.cmd==='note'));
 if(!vocal)throw Error('La melodia non contiene note.');
 const meter=tune.lines.find(l=>l.staff)?.staff[0]?.meter?.value?.[0],bar=meter?Number(meter.num)/Number(meter.den):1;
 const events=vocal.filter(e=>e.cmd==='note').sort((a,b)=>a.start-b.start),notes=[];
 for(const e of events){const previous=notes.at(-1);if(previous&&Math.abs(previous.start-e.start)<1e-6){previous.duration=Math.max(previous.duration,e.duration);continue}notes.push({start:e.start,duration:e.duration,strong:Math.abs(e.start/bar-Math.round(e.start/bar))<1e-5})}
 const phrases=[];let phrase=[];
 for(const note of notes){const previous=phrase.at(-1);if(previous&&(note.start-previous.start-previous.duration>=.1249||phrase.length>=16)){phrases.push({notes:phrase});phrase=[]}phrase.push(note)}
 if(phrase.length)phrases.push({notes:phrase});
 if(!phrases.length)throw Error('Lo spartito non contiene una linea cantabile.');return joinMeterFragments(phrases,bar);
}
function joinMeterFragments(phrases,bar){
 // Tiny rests and the note-count cap can leave isolated 1–4 note fragments.
 // Join only nearby units; keep long pauses and every original note intact.
 const units=phrases.map(p=>({notes:[...p.notes]})),maxGap=Math.min(.25,bar/4);
 for(let i=0;i<units.length;i++){
  if(units[i].notes.length>=5)continue;
  const gap=(a,b)=>b.notes[0].start-a.notes.at(-1).start-a.notes.at(-1).duration;
  const candidates=[];
  if(i>0&&units[i-1].notes.length+units[i].notes.length<=32&&gap(units[i-1],units[i])<=maxGap+1e-5)candidates.push({left:i-1,gap:gap(units[i-1],units[i])});
  if(i+1<units.length&&units[i].notes.length+units[i+1].notes.length<=32&&gap(units[i],units[i+1])<=maxGap+1e-5)candidates.push({left:i,gap:gap(units[i],units[i+1])});
  candidates.sort((a,b)=>a.gap-b.gap||a.left-b.left);
  if(candidates.length){const left=candidates[0].left;units[left].notes.push(...units[left+1].notes);units.splice(left+1,1);i=Math.max(-1,left-1)}
 }
 return units;
}
async function metricAssistant(){
 read();const snapshot=structuredClone(draft),stamp=JSON.stringify(snapshot);
 const context=await prepareMeterContext(snapshot);if(!context)return;
 const phrases=meterPhrases(context.abc);
 modal(`<div class="eyebrow">TESTO SULLA TUA MELODIA</div><h2>Adatta il testo al canto.</h2><p class="subtle">${phrases.length} frasi musicali · ${esc(context.source)}. L’assistente adatta il testo conservando significato e struttura, con versi collegati e un italiano naturale, seguendo pause e accenti musicali. La verifica finale resta all’ascolto.</p><div class="field"><label for="meter-mode">COSA VUOI FARE?</label><select id="meter-mode"><option value="adapt">Migliora / adatta il testo attuale</option><option value="translate">Traduci e adatta un testo straniero</option><option value="create">Crea un nuovo testo sulla melodia</option></select></div><div class="field"><label for="meter-instruction">TEMA E INDICAZIONI</label><textarea id="meter-instruction" placeholder="Facoltativo: indica il tono o le modifiche desiderate. L’assistente cura già italiano, significato, metrica e TAG."></textarea></div><p class="hint">${state.settings.llm_provider==='internal'?'L’assistente integrato carica il modello su richiesta e lo scarica alla fine, prima della generazione audio.':state.settings.llm_provider==='api'?'Usa il servizio API scelto in Sistema. Testo e spartito necessari vengono inviati al servizio e possono consumare credito; la GPU resta disponibile per la musica.':'Richiede un modello istruito in LM Studio. Puoi caricarlo sulla CPU per lasciare la GPU libera a YuE2; con un modello sulla GPU, scaricalo da LM Studio prima di generare musica.'} I TAG del testo attuale vengono conservati.</p><button id="meter-run" class="btn primary">Prepara il testo</button><p id="meter-working" class="hint" role="status"></p><div id="meter-result"></div>`);
 $('#meter-mode').onchange=()=>{$('#meter-instruction').placeholder=$('#meter-mode').value==='create'?'Descrivi il tema e il tono del nuovo testo.':'Facoltativo: indica il tono o le modifiche desiderate. L’assistente cura già italiano, significato, metrica e TAG.'};
 $('#meter-run').onclick=safe(e=>busy(e.currentTarget,async()=>{
  clearModalError();$('#meter-result').innerHTML='';
  $('#meter-working').textContent='Scrittura e revisione del testo in corso, anche per più gruppi di frasi. Attendi la proposta…';
  try{
   const r=await api('lyrics/adapt',{request:snapshot,mode:$('#meter-mode').value,instruction:$('#meter-instruction').value,phrases});
   $('#meter-result').innerHTML=`<div class="suggestion"><h3>Proposta da verificare</h3><textarea id="meter-proposal" readonly>${esc(r.request.lyrics)}</textarea>${r.warnings.map(w=>`<p class="hint">${esc(w)}</p>`).join('')}<details><summary>Controllo delle frasi · ${r.lines.filter(l=>l.fits).length} su ${r.lines.length} nella metrica stimata</summary><table><thead><tr><th>Frase</th><th>Sillabe stimate</th><th>Melodia</th><th>Esito</th></tr></thead><tbody>${r.lines.map(l=>`<tr><td>${l.id}</td><td>${l.syllables_min}–${l.syllables_max}</td><td>${l.target_min}–${l.target_max}</td><td>${l.fits?'Compatibile':'Da rivedere'}</td></tr>`).join('')}</tbody></table></details><button id="meter-apply" class="btn primary">Applica solo il testo alla bozza</button></div>`;
   $('#meter-apply').onclick=safe(()=>{read();if(JSON.stringify(draft)!==stamp)throw Error('La bozza è cambiata nel frattempo: riapri l’adattamento per conservare le tue modifiche.');draft.lyrics=r.request.lyrics;persist();closeModal();studio();toast('Testo applicato; la melodia è conservata')});
  }finally{if($('#meter-working'))$('#meter-working').textContent=''}
 }));
}
