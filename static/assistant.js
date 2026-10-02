'use strict';
const assistantApiPresets={openai:['OpenAI','https://api.openai.com/v1'],deepseek:['DeepSeek','https://api.deepseek.com'],openrouter:['OpenRouter','https://openrouter.ai/api/v1']};
function assistantRetryHTML(id){
 const selected=state.settings.llm_retries??3;
 return `<div class="field"><label for="${id}">RIPETIZIONI AUTOMATICHE IN CASO DI ERRORE</label><select id="${id}">${Array.from({length:11},(_,n)=>`<option value="${n}" ${n===selected?'selected':''}>${n===0?'Nessuna':n+' '+(n===1?'correzione':'correzioni')}${n===3?' · predefinito':''}</option>`).join('')}</select><p class="hint">Dopo il primo tentativo, riprova soltanto la fase non valida. Con API, le nuove richieste possono consumare altro credito.</p></div>`;
}
function assistantApiHTML(s){
 const preset=Object.keys(assistantApiPresets).find(k=>assistantApiPresets[k][1]===s.llm_api_url)||'custom';
 return `<div id="api-assistant" hidden><div class="field"><label for="s-api-preset">SERVIZIO</label><select id="s-api-preset">${Object.entries(assistantApiPresets).map(([key,[label]])=>`<option value="${key}" ${preset===key?'selected':''}>${label}</option>`).join('')}<option value="custom" ${preset==='custom'?'selected':''}>Personalizzato · compatibile OpenAI</option></select></div><div class="field"><label for="s-api-url">INDIRIZZO API</label><input id="s-api-url" type="url" value="${esc(s.llm_api_url||assistantApiPresets.openai[1])}" placeholder="https://servizio.example/v1"></div><div class="field"><label for="s-api-key">CHIAVE API</label><input id="s-api-key" type="password" autocomplete="new-password" placeholder="${s.llm_api_key_saved?'Chiave salvata · lascia vuoto per conservarla':'Incolla la chiave del servizio'}"><p class="hint" id="api-key-status"></p><label class="check"><input type="checkbox" id="s-api-clear-key"> Rimuovi la chiave salvata quando salvi</label></div><div class="field"><div class="label-row"><label for="s-api-model">MODELLO API</label><button type="button" id="api-models" class="text-btn">Leggi modelli</button></div><input id="s-api-model" list="api-model-list" value="${esc(s.llm_api_model||'')}" placeholder="Scegli dalla lista o inserisci l’identificativo"><datalist id="api-model-list"></datalist><p class="hint">Scegli un modello per testo/chat. Se il servizio non espone una lista, puoi inserire il nome manualmente.</p></div><details><summary>Compatibilità della risposta</summary><div class="field"><label for="s-api-format">FORMATO</label><select id="s-api-format"><option value="auto">Automatico · consigliato</option><option value="json">JSON semplice</option><option value="text">Solo istruzioni nel testo</option></select></div><p class="hint">Automatico usa risposte strutturate quando disponibili. I TAG e la metrica vengono controllati anche con gli altri formati.</p></details><p class="hint" id="api-assistant-status" role="status"></p><p class="note">Il servizio scelto riceve testo, stile, indicazioni e spartito necessari alla richiesta. Non inviamo i file audio. Le API possono consumare credito del tuo account. Non caricano un modello del testo sulla tua GPU; YuE2 continua a generare la musica sul PC.</p></div>`;
}
function updateAssistantApiKeyStatus(){
 if(!$('#s-api-key'))return;
 const saved=state.settings.llm_api_key_saved&&$('#s-api-url').value.trim().replace(/\/+$/,'')===state.settings.llm_api_url;
 $('#s-api-key').placeholder=saved?'Chiave salvata · lascia vuoto per conservarla':'Incolla la chiave del servizio';
 $('#api-key-status').textContent=saved?'Una chiave è salvata per questo indirizzo. Non viene mostrata alla pagina.':'La chiave viene salvata sul computer che esegue H3-Music, separata dai progetti. Cambiando indirizzo viene usata soltanto la chiave di quel servizio.';
}
function bindAssistantApi(){
 $('#s-api-format').value=state.settings.llm_api_format||'auto';updateAssistantApiKeyStatus();
 $('#s-api-preset').onchange=()=>{
  const preset=assistantApiPresets[$('#s-api-preset').value];
  if(preset){$('#s-api-url').value=preset[1];$('#s-api-model').value='';$('#s-api-format').value='auto'}
  $('#s-api-key').value='';$('#s-api-clear-key').checked=false;$('#api-model-list').innerHTML='';$('#api-assistant-status').textContent='';updateAssistantApiKeyStatus();
 };
 $('#s-api-url').oninput=()=>{$('#s-api-preset').value='custom';$('#api-model-list').innerHTML='';updateAssistantApiKeyStatus()};
 $('#api-models').onclick=safe(e=>busy(e.currentTarget,async()=>{
  $('#api-assistant-status').textContent='Lettura dei modelli…';
  try{
   await preferences();const result=await api('llm/models');
   if(!$('#api-model-list'))return;
   $('#api-model-list').innerHTML=result.data.map(model=>`<option value="${esc(model.id)}">`).join('');
   $('#api-assistant-status').textContent=`Connessione riuscita: ${result.data.length} modelli disponibili. Scegli un modello e premi Salva preferenze.`;
  }catch(error){if($('#api-assistant-status'))$('#api-assistant-status').textContent=error.message;throw error}
 }));
}
function bindAssistantModelPicker(){
 $('#assistant-model-browse').onclick=openAssistantModelPicker;
}
function openAssistantModelPicker(){
 const input=$('#s-internal-model'),token=crypto.randomUUID();let controller,sequence=0,folder;
 modal(`<div id="assistant-file-picker" data-token="${token}"><div class="eyebrow">MODELLO DELL’ASSISTENTE</div><h2>Scegli un file GGUF.</h2><p class="hint">Sfoglia le cartelle del computer che esegue H3-Music. Il file viene usato nella sua posizione, senza copiarlo.</p><div id="assistant-file-roots" class="actions"></div><form id="assistant-file-form"><label for="assistant-file-path">CARTELLA</label><div class="assistant-file-path-row"><input id="assistant-file-path" autocomplete="off"><button class="btn" type="submit">Apri</button></div></form><div class="actions"><button class="btn small" id="assistant-file-parent" disabled>← Cartella superiore</button></div><div class="field"><label for="assistant-file-search">CERCA IN QUESTA CARTELLA</label><input id="assistant-file-search" type="search" placeholder="Nome del modello o della cartella"></div><p id="assistant-file-status" class="hint" role="status"></p><div id="assistant-file-list"></div><div class="actions"><button class="btn" id="assistant-file-cancel">Annulla</button></div></div>`);
 const alive=()=>$('#modal').open&&$('#assistant-file-picker')?.dataset.token===token;
 function render(){
  const query=$('#assistant-file-search').value.toLocaleLowerCase(),entries=(folder?.entries||[]).filter(e=>e.name.toLocaleLowerCase().includes(query));
  $('#assistant-file-list').innerHTML=entries.length?entries.map((entry,index)=>`<button type="button" class="assistant-file-entry" data-entry="${index}" title="${esc(entry.path)}"><span>${entry.kind==='directory'?'▤':'♬'}</span><span class="assistant-file-name">${esc(entry.name)}<small>${entry.kind==='directory'?'Apri cartella':`Usa questo modello · ${(entry.bytes/1048576).toLocaleString('it-IT',{maximumFractionDigits:1})} MB`}</small></span><span>›</span></button>`).join(''):'<p class="hint">Nessuna cartella o file GGUF corrispondente.</p>';
  $$('[data-entry]').forEach(button=>button.onclick=()=>{
   const entry=entries[Number(button.dataset.entry)];
   if(entry.kind==='directory')return load(entry.path);
   if(input.isConnected){input.value=entry.path;$('#assistant-status').textContent='Modello selezionato. Premi Salva preferenze per usarlo.'}
   closeModal();
  });
 }
 async function load(path,initial=false){
  const request=++sequence;controller?.abort();controller=new AbortController();const active=controller;
  const timer=setTimeout(()=>active.abort(),12000);$('#assistant-file-status').textContent='Lettura della cartella…';
  try{
   const response=await fetch('/api/llm/files',{method:'POST',headers:{'Content-Type':'application/json','X-H3-Music':'1'},body:JSON.stringify({path,initial}),signal:active.signal});
   const result=await response.json();if(!response.ok)throw Error(result.error||'Cartella non disponibile.');
   if(!alive()||sequence!==request)return;
   folder=result;$('#assistant-file-path').value=folder.path;$('#assistant-file-search').value='';
   $('#assistant-file-parent').disabled=!folder.parent;
   $('#assistant-file-roots').innerHTML=folder.roots.map((r,i)=>`<button type="button" class="btn small" data-file-root="${i}">${esc(r.name)}</button>`).join('');
   $$('[data-file-root]').forEach(button=>button.onclick=()=>load(folder.roots[Number(button.dataset.fileRoot)].path));
   $('#assistant-file-status').textContent=folder.truncated?'Cartella molto grande: sono mostrate le prime 2.000 voci. Apri una sottocartella o inserisci il suo percorso.':'Apri una cartella oppure scegli il modello.';render();
  }catch(error){
   if(alive()&&sequence===request)$('#assistant-file-status').textContent=error.name==='AbortError'?'La cartella non risponde. Scegli un’altra posizione oppure premi Annulla.':error.message;
  }finally{clearTimeout(timer)}
 }
 $('#assistant-file-search').oninput=render;
 $('#assistant-file-form').onsubmit=e=>{e.preventDefault();load($('#assistant-file-path').value)};
 $('#assistant-file-parent').onclick=()=>load(folder.parent);
 $('#assistant-file-cancel').onclick=closeModal;
 const onClose=()=>{if(alive())return;sequence++;controller?.abort();$('#modal').removeEventListener('close',onClose)};
 $('#modal').addEventListener('close',onClose);
 load(input.value,true);
}
async function assistantPreferences(){
 if(!$('#s-provider'))return;
 const provider=$('#s-provider').value,integrated=provider==='internal';
 $('#internal-assistant').hidden=!integrated;$('#external-assistant').hidden=provider!=='lmstudio';$('#api-assistant').hidden=provider!=='api';
 if(integrated){
  const status=await api('llm/status');if(!$('#assistant-status'))return;
  $('#assistant-status').textContent=status.busy?'L’assistente sta preparando il testo…':status.ready?'Assistente pronto. A riposo non occupa la memoria del modello.':status.error||'Assistente da installare oppure modello GGUF da selezionare.';
 }
}
