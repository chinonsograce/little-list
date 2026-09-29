import React, {useEffect, useRef, useState} from 'react';

export default function VoicePanel({tasks, disabled, onDictate, onCommand}) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const canSpeak = !!(window.speechSynthesis && window.SpeechSynthesisUtterance);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [message, setMessage] = useState('Choose a microphone button to begin.');
  const [transcript, setTranscript] = useState('');
  const [commandText, setCommandText] = useState('');
  const recognition = useRef(null);
  const utterance = useRef(null);
  const timer = useRef(null);
  const latest = useRef({onDictate,onCommand,tasks,disabled});
  latest.current = {onDictate,onCommand,tasks,disabled};
  function stopReading() {
    if (utterance.current) { utterance.current.onend=null; utterance.current.onerror=null; }
    window.speechSynthesis?.cancel(); utterance.current=null; setSpeaking(false);
  }
  function readTasks() {
    if (!canSpeak) { setMessage('Readouts are unavailable in this browser.'); return; }
    stopReading();
    const list = latest.current.tasks;
    const lines = list.length ? [`You have ${list.length} tasks.`,...list.map((t,i)=>`Task ${i+1}. ${t.title}. ${t.completed ? 'Complete' : 'Not complete'}.`)] : ['Your list is empty.'];
    setSpeaking(true); setMessage('Reading your list. Use Stop reading to end the readout.');
    let index=0;
    function next() {
      if (index === lines.length) { setSpeaking(false); utterance.current=null; setMessage('Finished reading your list.'); return; }
      const speech = new SpeechSynthesisUtterance(lines[index++]);
      speech.lang='en-US'; speech.rate=0.95;
      speech.onend=next;
      speech.onerror=()=>{setSpeaking(false); setMessage('Could not play the readout. Check your browser audio settings.');};
      utterance.current=speech; window.speechSynthesis.speak(speech);
    }
    next();
  }
  async function execute(text) {
    if (latest.current.disabled) { setMessage('Please wait for the list to finish saving, then try again.'); return; }
    try {
      const result=await latest.current.onCommand(text);
      if (result==='read') readTasks();
      else setMessage(result ? 'Done. Your list has been saved.' : 'The change could not be saved. Check the message below.');
    } catch (error) { setMessage(error.message); }
  }
  function listen(mode) {
    if (!Recognition || recognition.current) return;
    stopReading(); setTranscript('');
    const instance = new Recognition();
    recognition.current=instance;
    instance.lang='en-US'; instance.continuous=false; instance.interimResults=true;
    let finalText='', failure=false;
    instance.onresult=event=>{
      let partial='';
      for(let i=event.resultIndex;i<event.results.length;i++) {
        if(event.results[i].isFinal) finalText+=event.results[i][0].transcript+' ';
        else partial+=event.results[i][0].transcript;
      }
      setTranscript((finalText+partial).trim());
    };
    instance.onerror=event=>{
      failure=true;
      const messages={'not-allowed':'Microphone access was denied. Allow it in your browser’s site settings, then try again.','service-not-allowed':'This browser cannot use the speech service. Try opening this address in Chrome.','audio-capture':'No microphone is available. Connect one and check its permissions.','network':'The speech service could not connect. Check your internet connection or try Chrome.','no-speech':'No speech was heard. Tap the microphone and try again.','language-not-supported':'English speech recognition is unavailable in this browser.'};
      setMessage(messages[event.error] || 'Voice input stopped. Please try again or type your task.');
    };
    instance.onend=()=>{
      clearTimeout(timer.current); recognition.current=null; setListening(false);
      if(failure) return;
      const text=finalText.trim();
      if(!text) {setMessage('No complete phrase was heard. Please try again.'); return;}
      if(mode==='dictate') {
        latest.current.onDictate(text.slice(0,300));
        setMessage(text.length>300 ? 'The first 300 characters are ready in the task box. Review them, then choose Add task.' : 'Your words are in the task box. Review them, then choose Add task.');
      } else execute(text);
    };
    try {
      instance.start(); setListening(true); setMessage(mode==='dictate' ? 'Listening for a task… Speak, then pause.' : 'Listening for a command… Speak, then pause.');
      timer.current=setTimeout(()=>instance.stop(),20000);
    } catch { recognition.current=null; setListening(false); setMessage('Voice input could not start. Try again or open this address in Chrome.'); }
  }
  function cancelListening() {
    const instance=recognition.current;
    if(instance) {instance.onend=null;instance.onerror=null;instance.onresult=null;instance.abort();}
    clearTimeout(timer.current);recognition.current=null;setListening(false);setMessage('Listening cancelled. No changes made.');
  }
  useEffect(()=>()=>{
    clearTimeout(timer.current);
    if(recognition.current) {recognition.current.onend=null;recognition.current.onerror=null;recognition.current.onresult=null;recognition.current.abort();}
    if(utterance.current) {utterance.current.onend=null;utterance.current.onerror=null;window.speechSynthesis?.cancel();}
  },[]);
  return <section className="voice-panel" aria-label="Voice assistant">
    <div className="voice-heading"><h3>Give your keyboard a break</h3><span>VOICE ASSISTANT</span></div>
    <div className="voice-controls">
      <button type="button" disabled={!Recognition || disabled || listening} onClick={()=>listen('dictate')}>🎙 Speak a task</button>
      <button type="button" disabled={!Recognition || disabled || listening} onClick={()=>listen('command')}>Voice command</button>
      <button type="button" disabled={!canSpeak || disabled || listening} onClick={speaking ? ()=>{stopReading();setMessage('Readout stopped.');} : readTasks}>{speaking ? 'Stop reading' : 'Read my tasks'}</button>
      {listening && <button type="button" className="cancel-listening" onClick={cancelListening}>Cancel listening</button>}
    </div>
    {!Recognition && <p className="voice-compatibility">Voice input is unavailable in this browser. Open this app’s address in Chrome to try it, or type a command below.</p>}
    {!canSpeak && <p className="voice-compatibility">Spoken readouts are unavailable in this browser.</p>}
    <p className="voice-status" role="status">{listening && <span className="listening-dot"/>}{message}</p>
    {transcript && <p className="transcript">Heard: “{transcript}”</p>}
    <details><summary>Commands & microphone help</summary>
      <p>Task numbers follow the current list order, including completed tasks.</p>
      <ul><li>“Add buy milk” — adds a task immediately.</li><li>“Complete the first task” or “uncheck task one”.</li><li>“Move task two up” or “move task one to position three”.</li><li>“Move task two to the top” or “to the bottom”.</li><li>“Read my tasks”.</li></ul>
      <p>Listening starts only when you click a microphone button, and stops after one phrase or 20 seconds. Allow microphone access when your browser asks. Recognition may need internet and send audio to your browser’s speech service. This app does not store recordings. Speech is currently set to English.</p>
      <label htmlFor="typed-command">You can also type a command</label><div className="typed-command"><input id="typed-command" value={commandText} maxLength={340} onChange={e=>setCommandText(e.target.value)} placeholder="Complete task one" disabled={disabled || listening}/><button type="button" disabled={disabled || listening || !commandText.trim()} onClick={()=>execute(commandText)}>Run command</button></div>
    </details>
  </section>;
}
