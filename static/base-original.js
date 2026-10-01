'use strict';
function originalBaseHTML(){
 return `<div class="card"><label class="check"><input id="base-enabled" type="checkbox" ${draft.base_enabled?'checked':''}> Base originale</label><p class="hint">Genera un nuovo canto con il testo scritto sopra, mantenendo la musica della canzone caricata.</p><div id="base-fields" style="display:${draft.base_enabled?'block':'none'}"><label class="btn" for="base-upload">＋ Carica la canzone originale</label><input id="base-upload" type="file" accept="audio/*,.wav,.mp3,.flac,.m4a" hidden><p id="base-status" class="hint" role="status"></p><div class="field"><label for="base-source">OPPURE SCEGLI UN BRANO GIÀ CARICATO</label><select id="base-source"><option value="">Scegli la canzone…</option></select></div><div id="base-preview"></div><details><summary>Cambia solo un tratto del canto</summary><div class="row"><div class="field"><label for="base-start">INIZIO (secondi)</label><input id="base-start" type="number" min="0" step="0.01" value="${Number(draft.base_start)||0}"></div><div class="field"><label for="base-end">FINE (0 = fine del brano)</label><input id="base-end" type="number" min="0" step="0.01" value="${Number(draft.base_end)||0}"></div></div><p class="hint">Fino a 4 minuti (240 secondi) di nuovo canto per volta. Fuori dal tratto scelto rimangono anche le voci originali.</p></details><p class="hint">La melodia e il tempo vengono ricavati dalla canzone. Scrivi un testo con una metrica simile; nello stile puoi descrivere la voce desiderata. Se vuoi il tuo timbro, attiva anche Clona.</p></div></div>`;
}
function updateOriginalBaseUI(){
 const enabled=!!draft.base_enabled;
 $('#base-fields').style.display=enabled?'block':'none';
 $('#plan').disabled=enabled;
 for(const id of ['cot','abc','score-import','remove-chords'])$('#'+id).disabled=enabled;
 $('#studio-mix-fields').style.display=enabled||draft.clone_enabled?'block':'none';
 if($('#studio-result-score'))$('#studio-result-score').disabled=enabled;
}
async function bindOriginalBase(){
 const select=$('#base-source'),input=$('#base-upload'),status=$('#base-status');let sources=[];
 $('#base-enabled').onchange=()=>{draft.base_enabled=$('#base-enabled').checked;persist();updateOriginalBaseUI()};
 for(const key of ['start','end'])$('#base-'+key).oninput=e=>{draft['base_'+key]=Number(e.target.value);persist()};
 function selected(){
  draft.base_import_id=select.value;const source=sources.find(s=>s.id===select.value);
  $('#base-preview').innerHTML=source?`<div class="source-card"><strong>${esc(source.name)}</strong><audio controls preload="metadata" src="${esc(source.url)}"></audio><p class="hint">${dur(source.duration)} · originale conservato</p></div>`:'';
  status.textContent=source?.duration>240.5?'Per questo brano scegli un tratto di massimo 4 minuti (240 secondi) nei campi inizio e fine.':'';
  persist();
 }
 async function load(value){const data=await api('imports');if(!select.isConnected)return;sources=data.sources;if(value&&!sources.some(s=>s.id===value))sources.push({id:value,name:'Audio del progetto',url:'/imports/'+encodeURIComponent(value)+'/audio'});select.innerHTML='<option value="">Scegli la canzone…</option>'+sources.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('');select.value=value||'';selected()}
 select.onchange=selected;
 input.onchange=safe(async()=>{
  const file=input.files[0];if(!file)return;input.disabled=true;
  try{const source=await uploadLocalAudio(file,status);if(input.isConnected){draft.base_start=0;draft.base_end=0;$('#base-start').value=0;$('#base-end').value=0;await load(source.id)}}
  finally{input.disabled=false;input.value=''}
 });
 updateOriginalBaseUI();await load(draft.base_import_id);
}
