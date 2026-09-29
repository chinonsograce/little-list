"""Password hashing, database-backed sessions and login throttling."""
import hashlib
import hmac
import secrets
import time
import re
from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

SESSION_SECONDS = 7 * 24 * 3600
ITERATIONS = 600_000


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=12, max_length=128)

    @field_validator('username')
    @classmethod
    def username_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,40}', value):
            raise ValueError('Use 3–40 letters, numbers, or underscores for your username.')
        return value


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'{salt}${digest}'


def password_matches(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split('$')[0]), encoded)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS auth_attempts (key TEXT PRIMARY KEY, attempts INTEGER NOT NULL, expires_at INTEGER NOT NULL)')


def throttle(db, username, request):
    db.execute('BEGIN IMMEDIATE')
    now = int(time.time())
    # Enforced by account name and direct client IP; forwarded headers must be trusted only by the host.
    keys = [f'user:{username}', f'ip:{request.client.host if request.client else "unknown"}']
    db.execute('DELETE FROM auth_attempts WHERE expires_at < ?', (now,))
    for key in keys:
        row = db.execute('SELECT attempts FROM auth_attempts WHERE key = ?', (key,)).fetchone()
        if row and row['attempts'] >= (10 if key.startswith('user:') else 50):
            raise HTTPException(429, 'Too many attempts. Please wait 15 minutes before trying again.')
    for key in keys:
        db.execute('INSERT INTO auth_attempts(key, attempts, expires_at) VALUES (?, 1, ?) ON CONFLICT(key) DO UPDATE SET attempts = attempts + 1', (key, now + 900))


def create_session(db, user_id, response: Response, secure):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    db.execute('DELETE FROM sessions WHERE expires_at < ?', (now,))
    db.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES (?,?,?)', (token_hash(token), user_id, now + SESSION_SECONDS))
    response.set_cookie('little_list_session', token, max_age=SESSION_SECONDS, httponly=True, secure=secure, samesite='strict', path='/')


def current_user(db, request: Request):
    token = request.cookies.get('little_list_session', '')
    row = db.execute('SELECT users.id, users.username FROM sessions JOIN users ON users.id = sessions.user_id WHERE token_hash = ? AND expires_at > ?', (token_hash(token), int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, 'Please sign in to access your list.')
    return row
