import os
from datetime import date
from typing import Literal
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import JSONResponse
from backend import auth
from backend.storage import connect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get('TODO_DB_PATH', ROOT / 'backend' / 'tasks.sqlite3'))

@contextmanager
def database():
    connection = connect(DB_PATH)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
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
        for name, definition in [('due_date', 'TEXT'), ('priority', "TEXT NOT NULL DEFAULT 'medium'"), ('deleted', 'INTEGER NOT NULL DEFAULT 0'), ('user_id', 'INTEGER')]:
            if name not in columns:
                db.execute(f'ALTER TABLE tasks ADD COLUMN {name} {definition}')
        auth.initialize(db)
        db.execute('CREATE INDEX IF NOT EXISTS tasks_owner ON tasks(user_id, deleted, position)')
    yield

app = FastAPI(title='Little List API', lifespan=lifespan)


@app.middleware('http')
async def protect_requests(request: Request, call_next):
    if request.url.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('x-little-list') != '1':
            return JSONResponse({'detail': 'Refresh the page and try again.'}, status_code=403)
        origin = request.headers.get('origin')
        from urllib.parse import urlsplit
        if origin and urlsplit(origin).netloc != request.headers.get('host'):
            return JSONResponse({'detail': 'Cross-site requests are not allowed.'}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


def require_user(request: Request):
    with database() as db:
        return auth.current_user(db, request)


@app.get('/api/auth/me')
def me(user=Depends(require_user)):
    return user


@app.post('/api/auth/{action}')
def authenticate(action: str, credentials: auth.Credentials, request: Request, response: Response):
    if action not in ('register', 'login'):
        raise HTTPException(404, 'Unknown account action.')
    with database() as db:
        auth.throttle(db, credentials.username, request)
    with database() as db:
        user = db.execute('SELECT * FROM users WHERE username = ?', (credentials.username,)).fetchone()
    if action == 'register':
        if user:
            raise HTTPException(409, 'That username is unavailable. Choose another or sign in.')
        encoded = auth.password_hash(credentials.password)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM users WHERE username = ?', (credentials.username,)).fetchone():
                raise HTTPException(409, 'That username is unavailable.')
            user = db.execute('INSERT INTO users(username,password_hash) VALUES (?,?) RETURNING id, username', (credentials.username, encoded)).fetchone()
    else:
        encoded = user['password_hash'] if user else auth.password_hash('dummy-password-not-valid', '00' * 16)
        if not auth.password_matches(credentials.password, encoded) or not user:
            raise HTTPException(401, 'Incorrect username or password.')
    with database() as db:
        auth.create_session(db, user['id'], response, os.environ.get('COOKIE_SECURE') == '1')
    return {'id': user['id'], 'username': user['username']}


@app.post('/api/logout', status_code=204)
def logout(request: Request, response: Response):
    with database() as db:
        db.execute('DELETE FROM sessions WHERE token_hash = ?', (auth.token_hash(request.cookies.get('little_list_session', '')),))
    response.delete_cookie('little_list_session', path='/')
    response.status_code = 204
    return response

@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.get('/api/config')
def config():
    return {'public_demo': False, 'private_lists': True}

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

def rows(db, user_id, deleted=0):
    return [dict(row) | {'completed': bool(row['completed'])} for row in db.execute('SELECT id,title,completed,position,notes,due_date,priority FROM tasks WHERE deleted = ? AND user_id = ? ORDER BY position, id', (deleted, user_id))]

@app.get('/api/tasks/trash')
def get_deleted(user=Depends(require_user)):
    with database() as db:
        return rows(db, user['id'], 1)

@app.post('/api/tasks/{task_id}/restore')
def restore_task(task_id: int, user=Depends(require_user)):
    with database() as db:
        if db.execute('UPDATE tasks SET deleted = 0 WHERE id = ? AND deleted = 1 AND user_id = ?', (task_id, user['id'])).rowcount == 0:
            raise HTTPException(404, 'Deleted task not found.')
        return rows(db, user['id'])

@app.put('/api/tasks/{task_id}/details')
def edit_details(task_id: int, task: TaskDetails, user=Depends(require_user)):
    with database() as db:
        if db.execute('UPDATE tasks SET title = ?, due_date = ?, priority = ? WHERE id = ? AND deleted = 0 AND user_id = ?', (task.title, task.due_date.isoformat() if task.due_date else None, task.priority, task_id, user['id'])).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db, user['id']) if row['id'] == task_id)

@app.get('/api/tasks')
def get_tasks(user=Depends(require_user)):
    with database() as db:
        return rows(db, user['id'])

@app.post('/api/tasks', status_code=201)
def add_task(task: NewTask, user=Depends(require_user)):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        created = db.execute('INSERT INTO tasks (title, user_id, position) VALUES (?, ?, (SELECT COALESCE(MAX(position), -1) + 1 FROM tasks WHERE user_id = ?)) RETURNING id', (task.title, user['id'], user['id'])).fetchone()
        return next(row for row in rows(db, user['id']) if row['id'] == created['id'])

@app.put('/api/tasks/order')
def reorder_tasks(order: TaskOrder, user=Depends(require_user)):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        existing = {row['id'] for row in db.execute('SELECT id FROM tasks WHERE deleted = 0 AND user_id = ?', (user['id'],))}
        if len(order.ids) != len(existing) or set(order.ids) != existing:
            raise HTTPException(409, 'The list changed. Refresh and try again.')
        db.executemany('UPDATE tasks SET position = ? WHERE id = ? AND user_id = ?', ((i, task_id, user['id']) for i, task_id in enumerate(order.ids)))
        return rows(db, user['id'])

@app.patch('/api/tasks/{task_id}')
def update_task(task_id: int, task: TaskUpdate, user=Depends(require_user)):
    with database() as db:
        if db.execute('UPDATE tasks SET completed = ? WHERE id = ? AND deleted = 0 AND user_id = ?', (task.completed, task_id, user['id'])).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db, user['id']) if row['id'] == task_id)

@app.delete('/api/tasks/{task_id}', status_code=204)
def delete_task(task_id: int, user=Depends(require_user)):
    with database() as db:
        if db.execute('UPDATE tasks SET deleted = 1 WHERE id = ? AND deleted = 0 AND user_id = ?', (task_id, user['id'])).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
    return Response(status_code=204)

@app.put('/api/tasks/{task_id}/notes')
def save_notes(task_id: int, note: TaskNotes, user=Depends(require_user)):
    with database() as db:
        if db.execute('UPDATE tasks SET notes = ? WHERE id = ? AND deleted = 0 AND user_id = ?', (note.notes, task_id, user['id'])).rowcount == 0:
            raise HTTPException(404, 'Task not found.')
        return next(row for row in rows(db, user['id']) if row['id'] == task_id)

if (ROOT / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='frontend')
