import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseCommand} from './voiceCommands.js';
const tasks=[{id:10},{id:20},{id:30}];
test('adds spoken titles and recognizes readout requests',()=>{
  assert.deepEqual(parseCommand('Add buy milk.',tasks),{type:'add',title:'buy milk'});
  assert.deepEqual(parseCommand('Add task Call Mum',tasks),{type:'add',title:'Call Mum'});
  assert.deepEqual(parseCommand('Read my tasks.',tasks),{type:'read'});
});
test('completes and unchecks the correct task with numbers or ordinals',()=>{
  for(const text of ['Complete the first task','Complete task one','Mark task 1 complete']) assert.deepEqual(parseCommand(text,tasks),{type:'complete',id:10,completed:true});
  for(const text of ['Uncheck task two','Mark the second task incomplete']) assert.deepEqual(parseCommand(text,tasks),{type:'complete',id:20,completed:false});
});
test('reorders up, down, to positions, and to list boundaries',()=>{
  for(const text of ['Move task two up','Move task two to the top']) assert.deepEqual(parseCommand(text,tasks).ids,[20,10,30]);
  assert.deepEqual(parseCommand('Move task one down',tasks).ids,[20,10,30]);
  for(const text of ['Move task one to position three','Move the first task to the bottom']) assert.deepEqual(parseCommand(text,tasks).ids,[20,30,10]);
});
test('rejects ambiguous or invalid commands without guessing a mutation',()=>{
  for(const text of ['buy milk','delete task one','complete task 0','complete task 20','move task one up','move task 3 down','move task 2 to 99','add '+ 'a'.repeat(301)]) assert.throws(()=>parseCommand(text,tasks));
  assert.throws(()=>parseCommand('complete task one',[]));
});
