import os
import sqlite3
from datetime import date
from typing import Literal
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get('TODO_DB_PATH', ROOT / 'backend' / 'tasks.sqlite3'))

@contextmanager
def database():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()

@asynccontextmanager
async def lifespan(app):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL)')
        if 'notes' not in {row['name'] for row in db.execute('PRAGMA table_info(tasks)')}:
            db.execute("ALTER TABLE tasks ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
        columns = {row['name'] for row in db.execute('PRAGMA table_info(tasks)')}
        for name, definition in [('due_date', 'TEXT'), ('priority', "TEXT NOT NULL DEFAULT 'medium'"), ('deleted', 'INTEGER NOT NULL DEFAULT 0')]:
            if name not in columns:
                db.execute(f'ALTER TABLE tasks ADD COLUMN {name} {definition}')
    yield

app = FastAPI(title='Little List API', lifespan=lifespan)

@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.get('/api/config')
def config():
    return {'public_demo': os.environ.get('PUBLIC_DEMO') == '1'}

class NewTask(BaseModel):
    title: str = Field(min_length=1, max_length=300)

    @field_validator('title')
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Please enter a task.')
        return value

class TaskUpdate(BaseModel):
    completed: bool

class TaskDetails(NewTask):
    due_date: date | None = None
    priority: Literal['low', 'medium', 'high'] = 'medium'

class TaskOrder(BaseModel):
    ids: list[int]

class TaskNotes(BaseModel):
    notes: str = Field(max_length=5000)

def rows(db, deleted=0):
    return [dict(row) | {'completed': bool(row['completed'])} for row in db.execute('SELECT id,title,completed,position,notes,due_date,priority FROM tasks WHERE deleted = ? ORDER BY position, id', (deleted,))]

@app.get('/api/tasks/trash')
def get_deleted():
    with database() as db:
        return rows(db, 1)

@app.post('/api/tasks/{task_id}/restore')
def restore_task(task_id: int):
    with database() as db:
        if db.execute('UPDATE tasks SET deleted = 0 WHERE id = ? AND deleted = 1', (task_id,)).rowcount == 0:
            raise HTTPException(404, 'Deleted task not found.')
        return rows(db)

@app.put('/api/tasks/{task_id}/details')
def edit_details(task_id: int, task: TaskDetails):
    with database() as db:
        if db.execute('UPDATE tasks SET title = ?, due_date = ?, priority = ? WHERE id = ? AND deleted = 0', (task.title, task.due_date.isoformat() if task.due_date else None, task.priority, task_id)).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db) if row['id'] == task_id)

@app.get('/api/tasks')
def get_tasks():
    with database() as db:
        return rows(db)

@app.post('/api/tasks', status_code=201)
def add_task(task: NewTask):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        cursor = db.execute('INSERT INTO tasks (title, position) VALUES (?, (SELECT COALESCE(MAX(position), -1) + 1 FROM tasks))', (task.title,))
        return next(row for row in rows(db) if row['id'] == cursor.lastrowid)

@app.put('/api/tasks/order')
def reorder_tasks(order: TaskOrder):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = {row['id'] for row in db.execute('SELECT id FROM tasks WHERE deleted = 0')}
        if len(order.ids) != len(existing) or set(order.ids) != existing:
            raise HTTPException(409, 'The list changed. Refresh and try again.')
        db.executemany('UPDATE tasks SET position = ? WHERE id = ?', enumerate(order.ids))
        return rows(db)

@app.patch('/api/tasks/{task_id}')
def update_task(task_id: int, task: TaskUpdate):
    with database() as db:
        if db.execute('UPDATE tasks SET completed = ? WHERE id = ? AND deleted = 0', (task.completed, task_id)).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db) if row['id'] == task_id)

@app.delete('/api/tasks/{task_id}', status_code=204)
def delete_task(task_id: int):
    with database() as db:
        if db.execute('UPDATE tasks SET deleted = 1 WHERE id = ? AND deleted = 0', (task_id,)).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
    return Response(status_code=204)

@app.put('/api/tasks/{task_id}/notes')
def save_notes(task_id: int, note: TaskNotes):
    with database() as db:
        if db.execute('UPDATE tasks SET notes = ? WHERE id = ? AND deleted = 0', (note.notes, task_id)).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db) if row['id'] == task_id)

if (ROOT / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='frontend')
