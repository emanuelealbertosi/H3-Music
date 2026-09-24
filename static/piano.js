'use strict';
// Uses the SheetSage2 reference renderer's MIDI sequence mapping with local piano samples.
let pianoUrl=null;
async function buildPianoPreview(id,part){
 const response=await fetch(`/files/${id}/preview-notes.json`);if(!response.ok)throw Error('Note per l’anteprima non disponibili.');const data=await response.json(),duration=Math.min(data.duration,120);
 const role=t=>/chord/i.test(t.name)?'chords':/vocal/i.test(t.name)?'vocal':'instrumental';
 const tracks=data.tracks.filter(t=>part==='all'||role(t)===part).map(t=>({...t,notes:t.notes.filter(n=>n.start<duration&&n.pitch>=21&&n.pitch<=109).map(n=>({...n,end:Math.min(duration,n.end)}))}));
 if(!tracks.some(t=>t.notes.length))throw Error('Nessuna nota riconosciuta per questa parte.');
 const context=new AudioContext({sampleRate:44100});
 try{
  await context.resume();const sequence=new ABCJS.synth.SynthSequence();
  for(const track of tracks){const tid=sequence.addTrack();sequence.setInstrument(tid,0);for(const n of track.notes)sequence.tracks[tid].push({cmd:'note',instrument:0,pitch:n.pitch,volume:n.velocity,start:n.start,duration:n.end-n.start,gap:0})}
  sequence.totalDuration=duration;const synth=new ABCJS.synth.CreateSynth();
  const loaded=await synth.init({audioContext:context,sequence,millisecondsPerMeasure:1000,options:{soundFontUrl:'/static/score-assets/soundfonts/',fadeLength:35,programOffsets:{acoustic_grand_piano:0},soundFontVolumeMultiplier:1}});
  if(loaded.error?.length)throw Error('Campioni di pianoforte non disponibili.');await synth.prime();const buffer=synth.getAudioBuffer();if(!buffer)throw Error('Anteprima non prodotta.');
  let peak=0;for(let c=0;c<buffer.numberOfChannels;c++){const ch=buffer.getChannelData(c);for(let i=0;i<ch.length;i++)peak=Math.max(peak,Math.abs(ch[i]))}
  const gain=Math.min(.7,peak>0?.98/peak:.7),channels=buffer.numberOfChannels,bytes=buffer.length*channels*2,wav=new ArrayBuffer(44+bytes),view=new DataView(wav),put=(o,s)=>[...s].forEach((c,i)=>view.setUint8(o+i,c.charCodeAt(0)));
  put(0,'RIFF');view.setUint32(4,36+bytes,true);put(8,'WAVE');put(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,channels,true);view.setUint32(24,buffer.sampleRate,true);view.setUint32(28,buffer.sampleRate*channels*2,true);view.setUint16(32,channels*2,true);view.setUint16(34,16,true);put(36,'data');view.setUint32(40,bytes,true);
  for(let c=0;c<channels;c++){const ch=buffer.getChannelData(c);for(let i=0;i<ch.length;i++)view.setInt16(44+(i*channels+c)*2,Math.round(Math.max(-1,Math.min(1,ch[i]*gain))*32767),true)}
  if(detailId!==id||!$('#piano-player'))return;
  if(pianoUrl)URL.revokeObjectURL(pianoUrl);pianoUrl=URL.createObjectURL(new Blob([wav],{type:'audio/wav'}));
  $('#piano-player').innerHTML=`<audio controls preload="metadata" src="${pianoUrl}"></audio><a class="btn small" href="${pianoUrl}" download="anteprima-pianoforte-${part}.wav">Scarica anteprima WAV</a>`;
 }finally{await context.close()}
}
