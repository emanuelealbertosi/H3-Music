'use strict';
const librarySelection=new Set();
const trashIcon='<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';

function librarySelectionHTML(){return `<div class="library-selection"><label class="check"><input type="checkbox" id="library-select-all"> Seleziona tutti i risultati visibili</label><span id="library-selected-count" aria-live="polite"></span><button class="text-btn" id="library-clear-selection">Deseleziona</button><button class="btn danger" id="library-delete-selected" disabled>${trashIcon} Elimina selezionati</button></div>`}
function libraryItemActions(j){return `<div class="track-selection"><label class="check"><input type="checkbox" data-select-job="${j.id}" aria-label="Seleziona ${esc(j.request.title)}" ${librarySelection.has(j.id)?'checked':''}> Seleziona</label><button class="btn small danger" data-delete-job="${j.id}" aria-label="Elimina ${esc(j.request.title)}" title="Elimina risultato">${trashIcon}</button></div>`}
function bindLibrarySelection(){
 const visible=$$('[data-select-job]');
 for(const id of librarySelection)if(!state.jobs.some(j=>j.id===id))librarySelection.delete(id);
 const update=()=>{
  const total=visible.filter(e=>librarySelection.has(e.dataset.selectJob)).length;
  $('#library-select-all').checked=visible.length>0&&total===visible.length;
  $('#library-select-all').indeterminate=total>0&&total<visible.length;
  $('#library-select-all').disabled=!visible.length;
  $('#library-selected-count').textContent=librarySelection.size+' selezionati';
  $('#library-delete-selected').disabled=!librarySelection.size;
  $('#library-clear-selection').disabled=!librarySelection.size;
  visible.forEach(e=>{e.checked=librarySelection.has(e.dataset.selectJob);e.closest('.track-card').classList.toggle('selected',e.checked)});
 };
 visible.forEach(e=>e.onchange=()=>{e.checked?librarySelection.add(e.dataset.selectJob):librarySelection.delete(e.dataset.selectJob);update()});
 $('#library-select-all').onchange=e=>{visible.forEach(v=>e.target.checked?librarySelection.add(v.dataset.selectJob):librarySelection.delete(v.dataset.selectJob));update()};
 $('#library-clear-selection').onclick=()=>{librarySelection.clear();update()};
 $('#library-delete-selected').onclick=()=>confirmLibraryDeletion([...librarySelection]);
 $$('[data-delete-job]').forEach(b=>b.onclick=()=>confirmLibraryDeletion([b.dataset.deleteJob]));
 update();
}
function confirmLibraryDeletion(ids){
 const jobs=ids.map(id=>state.jobs.find(j=>j.id===id)).filter(Boolean);if(!jobs.length)return;
 modal(`<h2>Eliminare ${jobs.length===1?'questo risultato':jobs.length+' risultati'}?</h2><p>Verranno eliminati definitivamente i file di queste sessioni: audio, spartiti, tracce separate ed esportazioni. Questa operazione libera spazio su disco e non può essere annullata.</p><p class="hint">I progetti salvati, i file importati e i campioni vocali vengono conservati.</p><ul class="delete-job-list">${jobs.map(j=>`<li>${esc(j.request.title)}</li>`).join('')}</ul><p id="library-delete-error" class="status-error" role="alert"></p><div class="actions"><button id="library-delete-cancel" class="btn">Annulla</button><button id="library-delete-confirm" class="btn danger">${trashIcon} Elimina definitivamente</button></div>`);
 $('#library-delete-cancel').onclick=closeModal;
 $('#library-delete-confirm').onclick=safe(e=>busy(e.currentTarget,async()=>{
  try{
   const selected=new Set(jobs.map(j=>j.id));$$('audio').forEach(a=>{if(selected.has((a.getAttribute('src')||'').split('/')[2])){a.pause();a.removeAttribute('src');a.load()}});
   const result=await api('jobs/delete',{ids:jobs.map(j=>j.id)}),removed=new Set([...result.deleted,...result.missing]);
   for(const id of removed)librarySelection.delete(id);
   comparison=comparison.filter(id=>!removed.has(id));
   if(removed.has(studioResultSource)){studioResultSource=null;const saved=JSON.parse(localStorage.getItem('h3-music-draft')||'null');if(saved){saved.resultSource=null;localStorage.setItem('h3-music-draft',JSON.stringify(saved))}}
   state.jobs=state.jobs.filter(j=>!removed.has(j.id));
   while(polling)await new Promise(r=>setTimeout(r,30));await refresh();
   if(page==='library'){tracks();compare()}
   if(result.errors.length){$('#library-delete-error').textContent=`Eliminati: ${result.deleted.length}. `+result.errors.map(x=>x.error).join(' ');return}
   closeModal();toast(result.deleted.length+' risultati eliminati');
  }catch(error){if($('#library-delete-error'))$('#library-delete-error').textContent=error.message;else throw error}
 }));
}
