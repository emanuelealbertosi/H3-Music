'use strict';
function voiceQualityHTML(prefix,steps=30){
 return `<div class="field"><label for="${prefix}-quality">QUALITÀ DELLA CONVERSIONE VOCALE</label><select id="${prefix}-quality">${[[30,'Minima'],[50,'Media'],[100,'Alta']].map(([n,label])=>`<option value="${n}" ${n===Number(steps)?'selected':''}>${label} · ${n} passaggi</option>`).join('')}</select><p class="hint">Più passaggi richiedono più tempo e possono migliorare la voce, senza garantire l’eliminazione degli artefatti. La scelta si applica alla prossima conversione.</p></div>`;
}
function mixControlsHTML(prefix,values={}){
 const v={automatic:true,voice_db:0,compression:true,ambience:0,...values};
 return `<fieldset class="mix-controls"><legend>Voce e musica</legend><label class="check"><input id="${prefix}-auto" type="checkbox" ${v.automatic?'checked':''}> Bilanciamento automatico dall’originale</label><p class="hint">Adegua la voce al volume del canto di partenza. Gli strumenti conservano il loro rapporto.</p><div class="field"><label for="${prefix}-balance">PIÙ MUSICA ← → PIÙ VOCE · <output id="${prefix}-value">${Number(v.voice_db).toFixed(1)} dB</output></label><input id="${prefix}-balance" type="range" min="-12" max="12" step="0.5" value="${Number(v.voice_db)||0}"></div><label class="check"><input id="${prefix}-compress" type="checkbox" ${v.compression?'checked':''}> Addolcisci gli sbalzi della voce</label><div class="field"><label for="${prefix}-ambience">AMBIENTE · <output id="${prefix}-room-value">${Number(v.ambience)||0}%</output></label><input id="${prefix}-ambience" type="range" min="0" max="100" step="5" value="${Number(v.ambience)||0}"></div><p class="hint">0 = voce asciutta. Aggiunge un ambiente leggero; non copia gli effetti originali e non corregge pronuncia o artefatti della conversione.</p></fieldset>`;
}
function bindMixControls(prefix,values,onChange){
 function changed(){const v={automatic:$('#'+prefix+'-auto').checked,voice_db:+$('#'+prefix+'-balance').value,compression:$('#'+prefix+'-compress').checked,ambience:+$('#'+prefix+'-ambience').value};$('#'+prefix+'-value').textContent=v.voice_db.toFixed(1)+' dB';$('#'+prefix+'-room-value').textContent=v.ambience+'%';onChange(v)}
 for(const suffix of ['auto','balance','compress','ambience'])$('#'+prefix+'-'+suffix).oninput=changed;
}
function mixSessionHTML(j){
 const before=j.files.find(f=>f.name==='mix-before.wav');
 return `<details class="mix-session"><summary>Regola voce e musica</summary>${mixControlsHTML('session-mix',j.request.mix)}<p class="hint">Salva una nuova versione usando le tracce già pronte. La voce non viene riconvertita e la musica non viene rigenerata. Le regolazioni si sentono dopo il salvataggio.</p><button id="remix-run" class="btn primary">Salva un nuovo mix</button>${before?`<p class="hint">Confronta con il mix precedente:</p><audio controls preload="none" src="${esc(before.url)}"></audio>`:''}</details>`;
}
function bindMixSession(j){
 let mix={automatic:true,voice_db:0,compression:true,ambience:0,...j.request.mix};bindMixControls('session-mix',mix,value=>{mix=value});
 $('#remix-run').onclick=safe(e=>busy(e.currentTarget,async()=>{await api('jobs',{kind:'remix',request:{source_id:j.id,mix}});await refresh();closeModal();toast('Nuovo mix accodato');show('queue')}));
}
async function uploadLocalAudio(file,status){
 if(!file)throw Error('Scegli un file audio.');
 if(file.size>256*1024*1024)throw Error('Il file supera 256 MB.');
 if(status)status.textContent='Caricamento e verifica del file…';
 const response=await fetch('/api/audio/upload',{method:'POST',headers:{'X-H3-Music':'1','X-Filename':encodeURIComponent(file.name),'Content-Type':'application/octet-stream'},body:file});
 const result=await response.json();if(!response.ok)throw Error(result.error||'Caricamento non riuscito.');return result;
}
function voicePickerHTML(prefix,selected=''){
 return `<div class="field"><label for="${prefix}-voice">LA TUA VOCE</label><select id="${prefix}-voice"><option value="">Scegli un campione…</option>${selected?`<option selected value="${esc(selected)}">Voce salvata</option>`:''}</select></div><label class="btn" for="${prefix}-upload">＋ Carica un campione di voce</label><input id="${prefix}-upload" type="file" accept="audio/*,.wav,.mp3,.flac,.m4a" hidden><p class="hint">Bastano 10–30 secondi di una sola voce, pulita e senza musica. Il campione resta disponibile per i prossimi brani.</p><p id="${prefix}-status" class="hint" role="status"></p><audio id="${prefix}-preview" controls preload="none" hidden></audio>`;
}
async function bindVoicePicker(prefix,selected,onChange){
 const select=$('#'+prefix+'-voice'),input=$('#'+prefix+'-upload'),status=$('#'+prefix+'-status'),preview=$('#'+prefix+'-preview');
 function changed(){
  onChange(select.value);
  if(select.value){preview.src='/api/voice-audio?name='+encodeURIComponent(select.value);preview.hidden=false}
  else{preview.pause();preview.removeAttribute('src');preview.hidden=true}
 }
 async function load(value){
  const data=await api('voices');if(!select.isConnected)return;
  select.innerHTML='<option value="">Scegli un campione…</option>'+data.voices.map(v=>`<option value="${esc(v.name)}">${esc(v.label||v.name)}</option>`).join('');select.value=value;changed();
 }
 select.onchange=changed;
 input.onchange=safe(async()=>{
  const file=input.files[0];if(!file)return;input.disabled=true;
  try{
   const source=await uploadLocalAudio(file,status);
   const voice=await api('voices/import',{source_id:source.id,name:file.name.replace(/\.[^.]+$/,'')});
   if(!input.isConnected)return;
   await load(voice.name);status.textContent='Voce pronta: '+(voice.label||voice.name);toast('Campione di voce salvato');
  }catch(e){if(status.isConnected)status.textContent=e.message;throw e}
  finally{input.disabled=false;input.value=''}
 });
 await load(selected||'');
}
function studioVoiceHTML(){
 return `<div class="card"><div class="card-title"><h2>La voce del brano</h2></div><label class="check"><input id="clone-enabled" type="checkbox" ${draft.clone_enabled?'checked':''}> Clona · usa la mia voce</label><p class="hint">Genera il brano e applica automaticamente il timbro del campione scelto, conservando la base del brano.</p><div id="studio-voice-fields" style="display:${draft.clone_enabled?'block':'none'}">${voicePickerHTML('studio',draft.clone_voice||'')}${voiceQualityHTML('studio',draft.voice_steps)}</div><div id="studio-mix-fields" style="display:${draft.clone_enabled||draft.base_enabled?'block':'none'}">${mixControlsHTML('studio-mix',draft.mix)}</div><button class="text-btn" id="existing-song">Vuoi cambiare la voce di una canzone esistente? →</button></div>`;
}
function bindStudioVoice(){
 $('#studio-quality').onchange=e=>{draft.voice_steps=+e.target.value;persist()};
 bindMixControls('studio-mix',draft.mix,value=>{draft.mix=value;persist()});
 $('#clone-enabled').onchange=()=>{draft.clone_enabled=$('#clone-enabled').checked;$('#studio-voice-fields').style.display=draft.clone_enabled?'block':'none';persist();updateOriginalBaseUI()};
 $('#existing-song').onclick=()=>show('voice');
 bindVoicePicker('studio',draft.clone_voice||'',value=>{draft.clone_voice=value;persist()}).catch(e=>toast(e.message,true));
}
let voiceSong={import_id:'',clone_voice:'',title:''};
try{voiceSong={...voiceSong,...JSON.parse(localStorage.getItem('h3-voice-song')||'{}')}}catch{}
function persistVoiceSong(){localStorage.setItem('h3-voice-song',JSON.stringify(voiceSong))}
async function voicePage(){
 $('#page').innerHTML=head('LA CANZONE RESTA, LA VOCE CAMBIA','La tua voce, sulla sua musica.','Carica una canzone e un campione della tua voce. L’app prepara il risultato completo.')+`<div class="grid"><section><div class="card"><div class="card-title"><h2>01 · La canzone originale</h2></div><label class="audio-drop" for="song-upload"><span class="upload-symbol">↥</span><strong>Carica la canzone</strong><span>MP3, WAV, FLAC o M4A</span><small>Fino a 256 MB e 30 minuti</small><input id="song-upload" type="file" accept="audio/*,.wav,.mp3,.flac,.m4a"></label><p id="song-status" class="hint" role="status"></p><div class="field"><label for="song-source">OPPURE SCEGLI UN AUDIO GIÀ CARICATO</label><select id="song-source"><option value="">Scegli una canzone…</option></select></div><div id="song-preview"></div><button class="btn primary wide" id="song-instrumental" style="margin-top:18px" disabled>Salva solo la musica</button><p class="hint">Rimuove la voce e salva la base in Libreria, pronta da esportare. Non serve un campione vocale.</p></div><div class="card"><div class="card-title"><h2>02 · Il timbro da usare</h2></div>${voicePickerHTML('replacement',voiceSong.clone_voice)}${voiceQualityHTML('song',voiceSong.voice_steps)}${mixControlsHTML('song-mix',voiceSong.mix)}<div class="field" style="margin-top:20px"><label for="song-title">TITOLO DEL RISULTATO</label><input id="song-title" maxlength="120" value="${esc(voiceSong.title)}" placeholder="La canzone con la mia voce"></div><button class="btn primary wide" id="song-run" disabled>Cambia la voce · mantieni la base</button></div></section><aside><div class="card transcription-story"><div class="eyebrow">TUTTO IN UN PASSAGGIO</div><h2>La base originale.<br>Il tuo timbro.</h2><p>Separiamo la parte cantata, la convertiamo verso il tuo campione e la uniamo alla base della registrazione.</p><p>La musica non viene rigenerata. La registrazione caricata resta intatta.</p><p class="hint">Possono restare residui della voce originale o artefatti di separazione. Parole, melodia, tempi e pronuncia derivano dal canto originale: il campione modifica soprattutto il timbro.</p></div><div class="card"><p class="hint">Segui le fasi in Coda. Quando finisce, il risultato completo è in Libreria, pronto da ascoltare ed esportare.</p><button class="btn" id="song-queue">Apri la coda</button></div></aside></div>`;
 $('#song-quality').onchange=e=>{voiceSong.voice_steps=+e.target.value;persistVoiceSong()};
 bindMixControls('song-mix',voiceSong.mix,value=>{voiceSong.mix=value;persistVoiceSong()});
 const input=$('#song-upload'),status=$('#song-status'),select=$('#song-source'),run=$('#song-run');let sources=[];
 function canRun(){if(run.isConnected){run.disabled=!voiceSong.import_id||!voiceSong.clone_voice;$('#song-instrumental').disabled=!voiceSong.import_id}}
 function selected(){
  voiceSong.import_id=select.value;const source=sources.find(s=>s.id===select.value);
  $('#song-preview').innerHTML=source?`<div class="source-card"><strong>${esc(source.name)}</strong><audio controls preload="metadata" src="${esc(source.url)}"></audio><p class="hint">${dur(source.duration)} · originale conservato</p></div>`:'';
  if(source&&!voiceSong.title){voiceSong.title=source.name;$('#song-title').value=voiceSong.title}
  persistVoiceSong();canRun();
 }
 async function loadSources(value){const data=await api('imports');if(!select.isConnected)return;sources=data.sources;select.innerHTML='<option value="">Scegli una canzone…</option>'+sources.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join('');select.value=value;selected()}
 select.onchange=selected;
 input.onchange=safe(async()=>{const file=input.files[0];if(!file)return;input.disabled=true;try{const source=await uploadLocalAudio(file,status);if(input.isConnected){await loadSources(source.id);status.textContent='Canzone pronta.'}}catch(e){if(status.isConnected)status.textContent=e.message;throw e}finally{input.disabled=false;input.value=''}});
 $('#song-title').oninput=e=>{voiceSong.title=e.target.value;persistVoiceSong()};$('#song-queue').onclick=()=>show('queue');
 $('#song-instrumental').onclick=safe(e=>busy(e.currentTarget,async()=>{await api('jobs',{kind:'instrumental',request:{import_id:voiceSong.import_id,title:(voiceSong.title||'Brano')+' · solo musica'}});await refresh();toast('Base strumentale accodata');show('queue')}));
 run.onclick=safe(e=>busy(e.currentTarget,async()=>{await api('jobs',{kind:'clone',request:{...voiceSong}});await refresh();toast('Cambio voce accodato: pensiamo a tutto noi');show('queue')}));
 await Promise.all([loadSources(voiceSong.import_id),bindVoicePicker('replacement',voiceSong.clone_voice,value=>{voiceSong.clone_voice=value;persistVoiceSong();canRun()})]);
}
