import React, {useState} from 'react';
export default function TaskDetails({task, disabled, onSave}) {
  const [editing,setEditing]=useState(false);
  const [title,setTitle]=useState(task.title);
  const [due,setDue]=useState(task.due_date || '');
  const [priority,setPriority]=useState(task.priority || 'medium');
  const [message,setMessage]=useState('');
  function open() {setTitle(task.title);setDue(task.due_date || '');setPriority(task.priority || 'medium');setMessage('');setEditing(true);}
  return <div className="task-details">
    {!editing ? <button type="button" disabled={disabled} onClick={open} aria-label={`Edit ${task.title}`}>Edit task</button> : <div className="details-editor">
      <label>Task name<input value={title} maxLength={300} onChange={e=>setTitle(e.target.value)} disabled={disabled}/></label>
      <label>Due date<input type="date" value={due} onInput={e=>setDue(e.currentTarget.value)} onChange={e=>setDue(e.target.value)} disabled={disabled}/></label>
      <label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)} disabled={disabled}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
      <div className="details-buttons"><button disabled={disabled || !title.trim()} onClick={async()=>{if(await onSave({title:title.trim(),due_date:due || null,priority})) setEditing(false);else setMessage('Could not save. Your edits are still here.');}}>Save changes</button><button disabled={disabled} onClick={()=>setEditing(false)}>Cancel</button></div>
      <span role="status">{message}</span>
    </div>}
  </div>;
}
