import React, {useState} from 'react';

export async function accountRequest(path, body) {
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Little-List':'1'},body:body ? JSON.stringify(body) : undefined});
  const data=response.status===204 ? null : await response.json();
  if(!response.ok) throw new Error(typeof data?.detail==='string' ? data.detail : 'Check your username and password. Passwords must have 12–128 characters.');
  return data;
}

export default function Account({onSignedIn}) {
  const [register,setRegister]=useState(false);
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  async function submit(event) {
    event.preventDefault(); if(busy) return;
    setBusy(true);setError('');
    try {const user=await accountRequest(`/api/auth/${register ? 'register' : 'login'}`,{username,password});setPassword('');onSignedIn(user);}
    catch(error){setError(error.message);}
    finally {setBusy(false);}
  }
  return <main className="account-page"><a className="brand" href="/">✓ little list.</a><section className="workspace account-card"><div className="list-header"><div><h1>{register ? 'Your own little list.' : 'Welcome back.'}</h1><p>Sign in to keep your tasks and notes private.</p></div></div><form className="account-form" onSubmit={submit}>
    <label htmlFor="username">Username</label><input id="username" autoComplete="username" required minLength={3} maxLength={40} pattern="[A-Za-z0-9_]{3,40}" value={username} onChange={e=>setUsername(e.target.value)} disabled={busy}/>
    <label htmlFor="password">Password</label><input id="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={12} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} disabled={busy}/>
    <p>Use 3–40 letters, numbers, or underscores for your username and at least 12 characters for your password.</p>
    {error && <p role="alert" className="account-error">{error}</p>}
    <button className="add-button" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}</button>
    <button type="button" className="account-switch" disabled={busy} onClick={()=>{setRegister(!register);setError('');}}>{register ? 'Already have an account? Sign in' : 'New here? Create an account'}</button>
    <p>Keep your password somewhere safe. Password recovery is not available yet.</p>
  </form></section></main>;
}
