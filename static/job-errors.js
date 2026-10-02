'use strict';
let knownJobStatuses=new Map(),jobErrorsStarted=false,currentErrorJob=null;
const acknowledgedJobErrors=new Set();
try{JSON.parse(localStorage.getItem('h3-job-errors-read')||'[]').forEach(id=>acknowledgedJobErrors.add(id))}catch{}
function jobErrorExplanation(job){
 const error=job.error||'Il motore si è fermato senza completare il lavoro.';
 if(job.request?.base_enabled&&/ritmo|riallinear|ritardo|melodia originale|canto non corrisponde/.test(error))return {cause:'Il canto è stato generato, ma non ha superato il controllo di sincronia con la base originale. Il mix finale non è stato pubblicato.',action:'Puoi controllare il canto nei file della sessione, adattare il testo alla melodia oppure provare una nuova variante. La base originale e la bozza sono conservate.',detail:error};
 if(/Memoria|memoria|allocat|out of memory/i.test(error))return {cause:'Il motore ha esaurito la memoria disponibile durante il lavoro.',action:'Libera memoria e riprova; puoi scegliere un modello musicale più leggero in Sistema. Con l’assistente integrato, il modello del testo viene scaricato automaticamente prima dell’audio.',detail:error};
 return {cause:error,action:'Apri i dettagli della sessione per controllare il registro e i file già prodotti. La bozza rimane disponibile.',detail:''};
}
function showJobError(job){
 const explanation=jobErrorExplanation(job);currentErrorJob=job.id;
 modal(`<div id="job-error-popup" role="alert"><div class="eyebrow">LAVORO NON COMPLETATO</div><h2>${esc(job.request?.title||'Elaborazione interrotta')}</h2><p class="job-error-cause">${esc(explanation.cause)}</p><p>${esc(explanation.action)}</p>${explanation.detail?`<details><summary>Messaggio completo</summary><p class="job-error-detail">${esc(explanation.detail)}</p></details>`:''}<p class="hint">Questo avviso rimane aperto finché non lo chiudi. La spiegazione resta nei dettagli e nella schermata di creazione.</p><div class="actions"><button class="btn primary" id="job-error-details">Apri i dettagli del lavoro</button><button class="btn" id="job-error-dismiss">Ho letto · chiudi</button></div></div>`);
 $('#job-error-dismiss').onclick=closeModal;
 $('#job-error-details').onclick=safe(async()=>{acknowledgeJobError();await detail(job.id)});
}
function acknowledgeJobError(){
 if(!currentErrorJob)return;
 acknowledgedJobErrors.add(currentErrorJob);currentErrorJob=null;
 localStorage.setItem('h3-job-errors-read',JSON.stringify([...acknowledgedJobErrors].slice(-200)));
}
function updateJobErrors(){
 const initial=!jobErrorsStarted,latest=state.jobs[0];
 for(const job of state.jobs){
  if(job.status==='failed'&&!acknowledgedJobErrors.has(job.id)&&((initial&&job.id===latest?.id)||!initial&&knownJobStatuses.get(job.id)!=='failed'))pendingJobErrors.add(job.id);
  knownJobStatuses.set(job.id,job.status);
 }
 jobErrorsStarted=true;
 for(const id of [...pendingJobErrors])if(!state.jobs.some(j=>j.id===id&&j.status==='failed')||acknowledgedJobErrors.has(id))pendingJobErrors.delete(id);
 if(!$('#modal').open){const job=state.jobs.find(j=>pendingJobErrors.has(j.id));if(job)showJobError(job)}
 renderStudioErrors();
}
const pendingJobErrors=new Set();
document.querySelector('#modal').addEventListener('close',acknowledgeJobError);
function renderStudioErrors(){
 const root=$('#studio-errors');if(!root)return;
 const jobs=state.jobs.filter(j=>j.status==='failed'&&((pid&&j.project_id===pid)||j.id===studioResultSource));
 root.innerHTML=jobs.length?`<section class="card job-error-card"><div class="eyebrow">ULTIMI LAVORI INTERROTTI</div>${jobs.slice(0,3).map(j=>`<div><h3>${esc(j.request.title)}</h3><p>${esc(jobErrorExplanation(j).cause)}</p><button class="btn small" data-job-error="${esc(j.id)}">Leggi la spiegazione</button></div>`).join('')}</section>`:'';
 $$('[data-job-error]',root).forEach(button=>button.onclick=()=>showJobError(state.jobs.find(j=>j.id===button.dataset.jobError)));
}
