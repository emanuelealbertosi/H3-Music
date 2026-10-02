'use strict';
async function prepareMeterContext(snapshot){
 const token=crypto.randomUUID();
 modal(`<div class="eyebrow">PREPARAZIONE DELLA MELODIA</div><h2>Prima le note, poi le parole.</h2><p id="meter-preparing" data-token="${token}" role="status">Cerco lo spartito del tratto selezionato…</p><p class="hint">Se manca, trascrivo la canzone originale. Il risultato resta nella libreria. Puoi chiudere questa finestra e riaprire l’adattamento quando la trascrizione è terminata.</p>`);
 const current=()=>$('#modal').open&&$('#meter-preparing')?.dataset.token===token;
 try{
  let context=await api('lyrics/context',{request:snapshot,prepare:true});
  while(context.job_id){
   if(!current())return null;
   const job=await api('jobs/'+context.job_id);
   if(!current())return null;
   if(job.status==='completed'){
    context=await api('lyrics/context',{request:snapshot});break;
   }
   if(['failed','cancelled','interrupted'].includes(job.status))throw Error(job.error||'La trascrizione non è stata completata. Controlla il lavoro nella libreria e riprova.');
   $('#meter-preparing').textContent=job.status==='queued'?'Trascrizione accodata. Attendo il termine dei lavori precedenti…':'Sto trascrivendo la melodia originale per ricavare pause e durate…';
   await new Promise(resolve=>setTimeout(resolve,1500));
  }
  return current()?context:null;
 }catch(error){if(current())closeModal();throw error}
}
