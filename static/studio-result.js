'use strict';

// Keep this panel separate from the progress strip: polling must not recreate
// the audio element or overwrite changes made while a song is generating.
function studioResult(){
 const root=$('#studio-result');if(!root)return;
 const jobs=state.jobs.filter(j=>j.status==='completed'&&['generate','plan'].includes(j.kind)&&((pid&&j.project_id===pid)||j.id===studioResultSource));
 if(!jobs.length){root.replaceChildren();delete root.dataset.ids;return}
 const ids=jobs.map(j=>j.id).join(','),previous=$('#studio-result-version')?.value;
 const changed=root.dataset.ids!==ids,playing=$('#studio-result-audio')&&!$('#studio-result-audio').paused;
 const selected=jobs.find(j=>j.id===previous);
 const job=selected&&(!changed||playing)?selected:jobs[0];
 if(!$('#studio-result-version')){
  root.innerHTML=`<section class="card studio-result-card" aria-label="Risultato nello Studio"><div class="studio-result-heading"><div><div class="eyebrow">IL TUO RISULTATO</div><h2 id="studio-result-title"></h2></div><div class="field"><label for="studio-result-version">VERSIONE DA ASCOLTARE O MODIFICARE</label><select id="studio-result-version"></select></div></div><div id="studio-result-player"></div><p class="hint">Modifica testo e stile qui sotto oppure usa lo spartito di questa versione per lavorare sulla melodia. Ogni nuova generazione conserva il brano precedente.</p><div class="actions"><button class="btn" id="studio-result-edit">Modifica testo e stile</button><button class="btn" id="studio-result-score">Usa lo spartito del brano</button><button class="btn primary" id="studio-result-generate">Genera nuova versione</button><button class="text-btn" id="studio-result-detail">Dettagli ed esportazione →</button></div><p class="hint" id="studio-result-warning"></p></section>`;
  $('#studio-result-version').onchange=()=>renderStudioResult(jobsForStudioResult($('#studio-result-version').value));
  $('#studio-result-edit').onclick=()=>{$('#style').scrollIntoView({behavior:'smooth',block:'center'});$('#style').focus({preventScroll:true})};
  $('#studio-result-generate').onclick=()=>$('#generate').click();
  $('#studio-result-detail').onclick=safe(()=>detail($('#studio-result-version').value));
  $('#studio-result-score').onclick=safe(e=>busy(e.currentTarget,async()=>{
   const id=$('#studio-result-version').value,container=root,project=pid;
   const j=await api('jobs/'+id);
   if(!container.isConnected||pid!==project||$('#studio-result-version')?.value!==id)return;
   if(!j.abc)throw Error('Questa versione non contiene uno spartito ABC.');
   $('#abc').value=j.abc;if($('#cot').value==='off')$('#cot').value=j.request.cot==='melody'?'melody':'full';
   $('#score-details').open=true;read();$('#abc').scrollIntoView({behavior:'smooth',block:'center'});$('#abc').focus({preventScroll:true});
   toast('Spartito caricato nella bozza. Puoi modificarlo e generare una nuova versione.');
  }));
 }
 if(changed){$('#studio-result-version').innerHTML=jobs.map((j,i)=>`<option value="${esc(j.id)}">${esc(j.request.title)} · ${date(j.created)}${i===0?' · più recente':''}</option>`).join('');root.dataset.ids=ids}
 $('#studio-result-version').value=job.id;renderStudioResult(job);
}

function jobsForStudioResult(id){return state.jobs.find(j=>j.id===id)}

function renderStudioResult(job){
 if(!job)return;
 const player=$('#studio-result-player');if(player.dataset.job===job.id)return;
 player.dataset.job=job.id;
 $('#studio-result-title').textContent=job.request.title;
 player.innerHTML=job.kind==='generate'?`<audio id="studio-result-audio" controls preload="metadata" aria-label="Ascolta il brano creato" src="/files/${encodeURIComponent(job.id)}/audio.wav"></audio>`:'<p class="note green">Spartito pronto. Usa lo spartito del brano per modificarlo e generare la canzone.</p>';
 $('#studio-result-generate').textContent=job.kind==='plan'?'Genera il brano':'Genera nuova versione';
 $('#studio-result-warning').textContent=job.result.audio_truncated||job.result.abc_truncated?'Limite token raggiunto: controlla il finale prima di creare una nuova versione.':'';
}
