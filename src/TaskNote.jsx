import React, {useEffect, useState} from 'react';

export default function TaskNote({task, disabled, onSave}) {
  const [draft,setDraft]=useState(task.notes || '');
  const [status,setStatus]=useState('');
  const dirty=draft!==(task.notes || '');
  useEffect(()=>{
    if(!dirty) return;
    const warn=event=>{event.preventDefault();event.returnValue='';};
    window.addEventListener('beforeunload',warn);
    return ()=>window.removeEventListener('beforeunload',warn);
  },[dirty]);
  async function save() {
    setStatus('Saving…');
    const saved=await onSave(draft);
    setStatus(saved ? 'Note saved.' : 'Could not save. Your draft is still here; please try again.');
  }
  return <details className="task-note">
    <summary>{task.notes ? 'View / edit note' : 'Add a note'}{dirty && <span> · Unsaved changes</span>}</summary>
    <div className="note-editor">
      <label htmlFor={`note-${task.id}`}>Note for {task.title}</label>
      <textarea id={`note-${task.id}`} rows={4} maxLength={5000} value={draft} disabled={disabled} placeholder="Add details, ideas, or a reminder…" onChange={event=>{setDraft(event.target.value);setStatus('');}}/>
      <div className="note-actions"><button type="button" disabled={disabled || !dirty} onClick={save}>Save note</button><button type="button" disabled={disabled || !dirty} onClick={()=>{setDraft(task.notes || '');setStatus('Changes discarded.');}}>Discard changes</button><span>{draft.length.toLocaleString()} / 5,000</span></div>
      <p className="note-status" role="status">{status || (dirty ? 'Save your changes before leaving.' : 'Clear the text and save to remove this note.')}</p>
    </div>
  </details>;
}
