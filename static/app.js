const $ = (id) => document.getElementById(id);
const message = $("message");
let recognition = null;
let finalTranscript = "";

function showMessage(text, type="") {
  message.textContent = text;
  message.className = "message " + type;
  message.classList.remove("hidden");
}
function hideMessage(){ message.classList.add("hidden"); }
async function api(path, options={}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(()=>({error:"Unexpected server response."}));
  if(!res.ok) throw new Error(data.error || "Request failed.");
  return data;
}
function jsonOptions(body){return {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};}
function busy(button, text){button.dataset.oldText=button.innerHTML;button.disabled=true;button.innerHTML=text;}
function unbusy(button){button.disabled=false;if(button.dataset.oldText)button.innerHTML=button.dataset.oldText;}
function showNotes(text){
  $("notesOutput").textContent=text;
  $("results").classList.remove("hidden");
  $("results").scrollIntoView({behavior:"smooth",block:"start"});
}
async function generateNotes(transcript, subject, language, detail, button){
  if(!transcript.trim()){showMessage("Please add or capture a lecture transcript first.","error");return;}
  hideMessage();busy(button,"Generating notes…");
  try{
    const data=await api("/api/generate-notes",jsonOptions({transcript,subject,language,detail}));
    showNotes(data.notes);showMessage("Notes generated. Review important details against the lecture.","success");
  }catch(e){showMessage(e.message,"error");}
  finally{unbusy(button);}
}
document.querySelectorAll(".tab").forEach(btn=>btn.addEventListener("click",()=>{
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("active",b===btn));
  document.querySelectorAll(".mode-panel").forEach(p=>p.classList.toggle("hidden",p.id!==btn.dataset.tab));
  hideMessage();
}));
$("youtubeBtn").addEventListener("click",async()=>{
  const url=$("youtubeUrl").value.trim();if(!url){showMessage("Paste a YouTube URL first.","error");return;}
  busy($("youtubeBtn"),"Fetching captions…");hideMessage();
  try{const data=await api("/api/youtube-transcript",jsonOptions({url}));$("recordedTranscript").value=data.transcript;showMessage("Transcript loaded. Review it, then generate notes.","success");}
  catch(e){showMessage(e.message,"error");}
  finally{unbusy($("youtubeBtn"));}
});
$("audioBtn").addEventListener("click",async()=>{
  const file=$("audioFile").files[0];if(!file){showMessage("Choose an audio file first.","error");return;}
  const form=new FormData();form.append("audio",file);busy($("audioBtn"),"Transcribing audio…");hideMessage();
  try{const data=await api("/api/transcribe-audio",{method:"POST",body:form});$("recordedTranscript").value=data.transcript;showMessage("Audio transcription completed. Please review technical terms.","success");}
  catch(e){showMessage(e.message,"error");}
  finally{unbusy($("audioBtn"));}
});
$("recordedNotesBtn").addEventListener("click",()=>generateNotes($("recordedTranscript").value,$("subject").value,$("language").value,$("detail").value,$("recordedNotesBtn")));
$("liveNotesBtn").addEventListener("click",()=>generateNotes($("liveTranscript").value,$("liveSubject").value,$("liveLanguage").value,"Detailed",$("liveNotesBtn")));

$("startLive").addEventListener("click",()=>{
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){showMessage("Live speech recognition is not supported in this browser. Try Chrome, or paste the lecture transcript manually.","error");return;}
  recognition=new SR();recognition.continuous=true;recognition.interimResults=true;
  recognition.lang=({"English":"en-IN","Telugu":"te-IN","Hindi":"hi-IN","Tamil":"ta-IN","Kannada":"kn-IN","Malayalam":"ml-IN"})[$("liveLanguage").value]||"en-IN";
  finalTranscript=$("liveTranscript").value.trim();
  recognition.onstart=()=>{$("liveState").textContent="Listening to your lecture…";$("liveHint").textContent="Speak near the microphone. Keep this tab open.";$("startLive").disabled=true;$("stopLive").disabled=false;};
  recognition.onresult=(event)=>{
    let interim="";
    for(let i=event.resultIndex;i<event.results.length;i++){
      const text=event.results[i][0].transcript;
      if(event.results[i].isFinal)finalTranscript+=" "+text;else interim+=text;
    }
    $("liveTranscript").value=(finalTranscript+" "+interim).trim();
  };
  recognition.onerror=(event)=>showMessage("Microphone recognition issue: "+event.error+". Check browser permission or paste transcript manually.","error");
  recognition.onend=()=>{$("liveState").textContent="Capture stopped";$("liveHint").textContent="Review the transcript and generate your notes.";$("startLive").disabled=false;$("stopLive").disabled=true;};
  recognition.start();
});
$("stopLive").addEventListener("click",()=>{if(recognition)recognition.stop();});
$("clearLive").addEventListener("click",()=>{$("liveTranscript").value="";finalTranscript="";if(recognition){try{recognition.stop()}catch(e){}}hideMessage();});
$("copyBtn").addEventListener("click",async()=>{
  try{await navigator.clipboard.writeText($("notesOutput").textContent);showMessage("Notes copied to clipboard.","success");}
  catch(e){showMessage("Clipboard access blocked by browser. Select and copy the notes manually.","error");}
});
$("downloadBtn").addEventListener("click",()=>{
  const text=$("notesOutput").textContent;const blob=new Blob([text],{type:"text/markdown;charset=utf-8"});
  const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download="lecture-notes.md";a.click();URL.revokeObjectURL(url);
});
api("/api/health").then(data=>{
  $("apiStatus").textContent=data.ai_configured?"AI service connected":"AI key needed";
  document.querySelector(".status-dot").style.background=data.ai_configured?"#27b58a":"#e8aa39";
}).catch(()=>{$("apiStatus").textContent="Start the local server";});
