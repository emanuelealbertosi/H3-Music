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
 if(!phrases.length)throw Error('Lo spartito non contiene una linea cantabile.');return phrases;
}
async function metricAssistant(){
 read();const snapshot=structuredClone(draft),stamp=JSON.stringify(snapshot);
 const context=await api('lyrics/context',{request:snapshot}),phrases=meterPhrases(context.abc);
 modal(`<div class="eyebrow">TESTO SULLA TUA MELODIA</div><h2>Adatta il testo al canto.</h2><p class="subtle">${phrases.length} frasi musicali · ${esc(context.source)}. L’assistente propone parole in italiano rispettando pause, lunghezze e accenti musicali. La verifica finale resta all’ascolto.</p><div class="field"><label for="meter-mode">COSA VUOI FARE?</label><select id="meter-mode"><option value="adapt">Migliora / adatta il testo attuale</option><option value="translate">Traduci e adatta un testo straniero</option><option value="create">Crea un nuovo testo sulla melodia</option></select></div><div class="field"><label for="meter-instruction">TEMA E INDICAZIONI</label><textarea id="meter-instruction" placeholder="Mantieni il significato, usa un italiano naturale e un ritornello facile da cantare…"></textarea></div><p class="hint">Richiede un modello istruito in LM Studio. Puoi caricarlo sulla CPU per lasciare la GPU libera a YuE2; con un modello sulla GPU, scaricalo da LM Studio prima di generare musica.</p><button id="meter-run" class="btn primary">Prepara il testo</button><p id="meter-working" class="hint" role="status"></p><div id="meter-result"></div>`);
 $('#meter-run').onclick=safe(e=>busy(e.currentTarget,async()=>{
  $('#meter-working').textContent='Adattamento in corso, anche per più gruppi di frasi. Attendi la proposta…';
  try{
   const r=await api('lyrics/adapt',{request:snapshot,mode:$('#meter-mode').value,instruction:$('#meter-instruction').value,phrases});
   $('#meter-result').innerHTML=`<div class="suggestion"><h3>Proposta da verificare</h3><textarea id="meter-proposal" readonly>${esc(r.request.lyrics)}</textarea>${r.warnings.map(w=>`<p class="hint">${esc(w)}</p>`).join('')}<details><summary>Controllo delle frasi · ${r.lines.filter(l=>l.fits).length} su ${r.lines.length} nella metrica stimata</summary><table><thead><tr><th>Frase</th><th>Sillabe stimate</th><th>Melodia</th><th>Esito</th></tr></thead><tbody>${r.lines.map(l=>`<tr><td>${l.id}</td><td>${l.syllables_min}–${l.syllables_max}</td><td>${l.target_min}–${l.target_max}</td><td>${l.fits?'Compatibile':'Da rivedere'}</td></tr>`).join('')}</tbody></table></details><button id="meter-apply" class="btn primary">Applica solo il testo alla bozza</button></div>`;
   $('#meter-apply').onclick=safe(()=>{read();if(JSON.stringify(draft)!==stamp)throw Error('La bozza è cambiata nel frattempo: riapri l’adattamento per conservare le tue modifiche.');draft.lyrics=r.request.lyrics;persist();closeModal();studio();toast('Testo applicato; la melodia è conservata')});
  }finally{if($('#meter-working'))$('#meter-working').textContent=''}
 }));
}
