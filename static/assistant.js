'use strict';
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
 const integrated=$('#s-provider').value==='internal';
 $('#internal-assistant').hidden=!integrated;$('#external-assistant').hidden=integrated;
 if(integrated){
  const status=await api('llm/status');if(!$('#assistant-status'))return;
  $('#assistant-status').textContent=status.busy?'L’assistente sta preparando il testo…':status.ready?'Assistente pronto. A riposo non occupa la memoria del modello.':status.error||'Assistente da installare oppure modello GGUF da selezionare.';
 }
}
