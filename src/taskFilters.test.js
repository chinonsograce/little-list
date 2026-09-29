import {test} from 'node:test';
import assert from 'node:assert/strict';
import {matchesTask,isOverdue,localDate} from './taskFilters.js';
const task={title:'Assignment',notes:'Use SQLite',priority:'high',completed:false,due_date:'2026-09-28'};
test('combines case-insensitive note search, status, and priority',()=>{
 assert.equal(matchesTask(task,' sqlite ','pending','high'),true);
 assert.equal(matchesTask(task,'sqlite','completed','high'),false);
 assert.equal(matchesTask(task,'sqlite','pending','low'),false);
 assert.equal(matchesTask(task,'missing','all','all'),false);
});
test('overdue excludes completed tasks, missing dates, and today',()=>{
 assert.equal(isOverdue(task,'2026-09-29'),true);
 assert.equal(isOverdue(task,'2026-09-28'),false);
 assert.equal(isOverdue({...task,completed:true},'2026-09-29'),false);
 assert.equal(isOverdue({...task,due_date:null},'2026-09-29'),false);
 assert.equal(localDate(new Date(2026,0,2)), '2026-01-02');
});
