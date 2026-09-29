import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import VoicePanel from './VoicePanel.jsx';
import {parseCommand} from './voiceCommands.js';
import TaskNote from './TaskNote.jsx';
import TaskDetails from './TaskDetails.jsx';
import {matchesTask,isOverdue} from './taskFilters.js';

async function api(path = '', method = 'GET', body) {
  const response = await fetch(`/api/tasks${path}`, {method, headers: {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body)});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not save your changes. Please try again.');
  }
  return response.status === 204 ? null : response.json();
}

function App() {
  const [tasks, setTasks] = useState([]);
  const [publicDemo,setPublicDemo]=useState(false);
  useEffect(()=>{fetch('/api/config').then(r=>r.json()).then(c=>setPublicDemo(c.public_demo)).catch(()=>{});},[]);
  const [search,setSearch]=useState('');
  const [filter,setFilter]=useState('all');
  const [priorityFilter,setPriorityFilter]=useState('all');
  const [trash,setTrash]=useState([]);
  const [deleted,setDeleted]=useState(null);
  const filtering=!!search.trim() || filter!=='all' || priorityFilter!=='all';
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(null);
  const [over, setOver] = useState(null);
  const input = useRef(null);
  const lock = useRef(false);
  const completed = tasks.filter(task => task.completed).length;
  async function load() {
    setLoading(true); setError('');
    try { const [active,removed]=await Promise.all([api(),api('/trash')]); setTasks(active);setTrash(removed); } catch { setError('Your list could not be loaded. Check that the app is running and try again.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  async function mutate(action) {
    if (lock.current) return false;
    lock.current = true; setBusy(true); setError('');
    try { await action(); return true; } catch (err) { setError(err.message); return false; }
    finally { lock.current = false; setBusy(false); }
  }
  function add(event) {
    event.preventDefault();
    if (!title.trim()) return;
    mutate(async () => { const task = await api('', 'POST', {title: title.trim()}); setTasks(previous => [...previous, task]); setTitle(''); input.current?.focus(); });
  }
  async function voiceCommand(text) {
    const command=parseCommand(text,tasks);
    if(command.type==='read') return 'read';
    if(filtering && command.type!=='add') throw new Error('Clear the search and filters before using numbered voice commands.');
    return mutate(async()=>{
      if(command.type==='add') {
        const task=await api('','POST',{title:command.title});
        setTasks(previous=>[...previous,task]);
      } else if(command.type==='complete') {
        const updated=await api(`/${command.id}`,'PATCH',{completed:command.completed});
        setTasks(previous=>previous.map(t=>t.id===updated.id?updated:t));
      } else setTasks(await api('/order','PUT',{ids:command.ids}));
    });
  }
  function restore(id) {
    return mutate(async()=>{setTasks(await api(`/${id}/restore`,'POST'));setTrash(previous=>previous.filter(t=>t.id!==id));setDeleted(previous=>previous?.id===id?null:previous);});
  }
  function move(id, targetId) {
    setDragging(null); setOver(null);
    if (filtering || id === targetId || id === null) return;
    const next = [...tasks];
    const from = next.findIndex(t => t.id === id), to = next.findIndex(t => t.id === targetId);
    if (from < 0 || to < 0) return;
    next.splice(to, 0, next.splice(from, 1)[0]);
    mutate(async () => setTasks(await api('/order', 'PUT', {ids: next.map(t => t.id)})));
  }
  return <div className="app">
    <header><a className="brand" href="/" aria-label="Little List home"><span className="brand-mark">✓</span> little list<span className="brand-dot">.</span></a><span className="header-note"><span className="status-dot"/> A little space for a clearer mind</span></header>
    <main>
      {publicDemo && <p className="undo-banner">Public demo: everyone shares this list. Use sample data only. Tasks may reset when the free server sleeps or restarts.</p>}
      <div className="eyebrow">ONE THING AT A TIME</div>
      <div className="heading-row"><div><h1>Make room for your day<span>.</span></h1><p className="intro">Big plans, small steps. It all starts with a list.</p></div><span className="date">{new Date().toLocaleDateString(undefined, {month:'short', day:'numeric', weekday:'short'})}</span></div>
      <section className="workspace" aria-label="Your to-do list">
        <div className="list-header"><div><h2>My tasks <span className="count">{tasks.length}</span></h2><p>{tasks.length ? `${tasks.length - completed} left to do. You've got this.` : 'A fresh start, ready when you are.'}</p></div><span className="saved" aria-live="polite">{loading ? 'Loading…' : busy ? 'Saving…' : error ? 'Needs attention' : '✓ All changes saved'}</span></div>
        <form onSubmit={add}><label className="sr-only" htmlFor="new-task">New task</label><span className="add-symbol">＋</span><input ref={input} id="new-task" value={title} onChange={e=>setTitle(e.target.value)} maxLength={300} placeholder="What would you like to get done?" disabled={loading || busy}/><button className="add-button" disabled={!title.trim() || loading || busy}>Add task <span>↗</span></button></form>
        <VoicePanel tasks={tasks} disabled={busy || loading} onDictate={setTitle} onCommand={voiceCommand}/>
        {error && <div className="error" role="alert">{error} <button onClick={load} disabled={busy || loading}>Refresh list</button></div>}
        <div className="filters"><label>Search tasks and notes<input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Find a task…"/></label><label>Status<select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All tasks</option><option value="pending">Pending</option><option value="completed">Completed</option><option value="overdue">Overdue</option></select></label><label>Priority<select value={priorityFilter} onChange={e=>setPriorityFilter(e.target.value)}><option value="all">All priorities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>{filtering && <button onClick={()=>{setSearch('');setFilter('all');setPriorityFilter('all');}}>Clear filters</button>}</div>
        {filtering && <p className="filter-info">Showing {tasks.filter(t=>matchesTask(t,search,filter,priorityFilter)).length} of {tasks.length} tasks. Clear filters to reorder or use numbered voice commands.</p>}
        {deleted && <div className="undo-banner" role="status">Deleted “{deleted.title}”. <button disabled={busy} onClick={()=>restore(deleted.id)}>Undo</button><button onClick={()=>setDeleted(null)} aria-label="Dismiss undo message">×</button></div>}
        {!loading && tasks.length>0 && !tasks.some(t=>matchesTask(t,search,filter,priorityFilter)) && <p className="empty">No tasks match. Try another search or clear the filters.</p>}
        {loading ? <div className="empty">Opening your list…</div> : tasks.length === 0 ? <div className="empty"><div className="empty-icon">✓</div><h3>A little less on your mind.</h3><p>Add your first task above.<br/>One small step is a great place to start.</p></div> : <ul className="tasks">{tasks.map((task,index)=>matchesTask(task,search,filter,priorityFilter) && <li key={task.id} className={`${task.completed ? 'complete' : ''} ${over===task.id ? 'drop-target' : ''} ${dragging===task.id ? 'dragging' : ''}`} onDragOver={event=>{event.preventDefault(); if(!busy && !filtering) setOver(task.id);}} onDrop={event=>{event.preventDefault(); move(dragging,task.id);}}>
          <span className="drag-handle" draggable={!busy && !filtering} onDragStart={event=>{setDragging(task.id); event.dataTransfer.effectAllowed='move'; event.dataTransfer.setData('text/plain',String(task.id));}} onDragEnd={()=>{setDragging(null);setOver(null);}} title="Drag to reorder" aria-hidden="true">⠿</span>
          <input type="checkbox" aria-label={`Mark ${task.title} ${task.completed ? 'incomplete' : 'complete'}`} checked={task.completed} disabled={busy} onChange={()=>mutate(async()=>{const updated=await api(`/${task.id}`,'PATCH',{completed:!task.completed});setTasks(previous=>previous.map(t=>t.id===task.id?updated:t));})}/>
          <span className="task-number" aria-label={`Task ${index+1}`}>{index+1}.</span><span className="task-title">{task.title}</span>
          <div className="task-actions"><button aria-label={`Move ${task.title} up`} title="Move up" disabled={busy || filtering || index===0} onClick={()=>move(task.id,tasks[index-1].id)}>↑</button><button aria-label={`Move ${task.title} down`} title="Move down" disabled={busy || filtering || index===tasks.length-1} onClick={()=>move(task.id,tasks[index+1].id)}>↓</button><button className="delete" aria-label={`Delete ${task.title}`} title="Delete task" disabled={busy} onClick={()=>mutate(async()=>{await api(`/${task.id}`,'DELETE');setTasks(previous=>previous.filter(t=>t.id!==task.id));setTrash(previous=>[...previous,task]);setDeleted(task);})}>×</button></div>
          <div className="task-meta"><span className={`priority priority-${task.priority}`}>{task.priority} priority</span>{task.due_date && <span className={isOverdue(task) ? 'overdue' : ''}>{isOverdue(task) ? 'Overdue · ' : 'Due '}{task.due_date}</span>}</div>
          <TaskDetails task={task} disabled={busy} onSave={details=>mutate(async()=>{const updated=await api(`/${task.id}/details`,'PUT',details);setTasks(previous=>previous.map(t=>t.id===task.id?updated:t));})}/>
          <TaskNote task={task} disabled={busy} onSave={notes=>mutate(async()=>{const updated=await api(`/${task.id}/notes`,'PUT',{notes});setTasks(previous=>previous.map(t=>t.id===task.id?updated:t));})}/>
        </li>)}</ul>}
        <div className="list-footer"><span>⠿ Drag to reorder <span className="separator">·</span> or use the arrows</span><span aria-live="polite">{completed} of {tasks.length} complete</span></div>
        <details className="trash-panel"><summary>Deleted tasks ({trash.length})</summary><p>Restore a task with its note, date, and priority, even after reloading.</p>{trash.map(task=><div key={task.id}><span>{task.title}</span><button disabled={busy} onClick={()=>restore(task.id)} aria-label={`Restore ${task.title}`}>Restore</button></div>)}{!trash.length && <p>No deleted tasks.</p>}</details>
      </section>
      <div className="bottom-note"><span>✧</span> Progress doesn’t have to be perfect. Just keep going.</div>
    </main><footer><span>A little list. A lighter day.</span><span>Made for your everyday.</span></footer>
  </div>;
}

createRoot(document.getElementById('root')).render(<App/>);
