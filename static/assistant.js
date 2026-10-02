'use strict';
function bindAssistantModelPicker(){
 $('#assistant-model-browse').onclick=safe(e=>busy(e.currentTarget,async()=>{
  const input=$('#s-internal-model'),status=$('#assistant-status');
  status.textContent='Scegli il file GGUF nella finestra aperta sul PC che esegue H3-Music.';
  try{
   const result=await api('llm/browse',{});
   if(!input.isConnected)return;
   if(result.path){input.value=result.path;status.textContent='Modello selezionato. Premi Salva preferenze per usarlo. Il file viene usato dalla sua cartella, senza copiarlo.'}
   else await assistantPreferences();
  }catch(error){if(status.isConnected)status.textContent=error.message;throw error}
 }));
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
