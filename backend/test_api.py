import os
import tempfile
import unittest
import sqlite3
from unittest.mock import patch
from pathlib import Path

temporary = tempfile.TemporaryDirectory()
os.environ['TODO_DB_PATH'] = str(Path(temporary.name) / 'test.sqlite3')
from fastapi.testclient import TestClient
from backend.main import app, database
if os.environ.get('TEST_DRIVER') == 'libsql':
    import libsql
    import backend.main
    from backend.storage import Connection
    backend.main.connect = lambda path: Connection(libsql.connect(str(path)))
HEADERS={"X-Little-List":"1"}
CREDENTIALS={"username":"test_owner","password":"test-password-long-enough"}

def login(client):
    client.headers.update(HEADERS)
    result=client.post("/api/auth/login",json=CREDENTIALS)
    if result.status_code==401:
        result=client.post("/api/auth/register",json=CREDENTIALS)
    assert result.status_code==200, result.text
    return result.json()

class TasksTest(unittest.TestCase):
    def test_complete_workflow_and_persistence(self):
        with TestClient(app) as client:
            login(client)
            self.assertEqual(client.get('/api/tasks').json(), [])
            self.assertEqual(client.post('/api/tasks', json={'title':'   '}).status_code, 422)
            self.assertEqual(client.post('/api/tasks', json={'title':'x'*301}).status_code, 422)
            first = client.post('/api/tasks', json={'title':' First task '}).json()
            second = client.post('/api/tasks', json={'title':'Second task'}).json()
            self.assertEqual(first['title'], 'First task')
            note='Remember the details.\nBring the reference document.'
            self.assertEqual(first['notes'], '')
            self.assertEqual(client.put(f"/api/tasks/{first['id']}/notes",json={'notes':note}).json()['notes'],note)
            self.assertEqual(client.put(f"/api/tasks/{first['id']}/notes",json={'notes':'x'*5001}).status_code,422)
            self.assertEqual(client.put('/api/tasks/999999/notes',json={'notes':'missing'}).status_code,404)
            self.assertTrue(client.patch(f"/api/tasks/{first['id']}", json={'completed':True}).json()['completed'])
            self.assertEqual(client.put('/api/tasks/order',json={'ids':[first['id'],first['id']]}).status_code,409)
            self.assertEqual(client.put('/api/tasks/order',json={'ids':[second['id'],first['id']]}).status_code,200)
        with TestClient(app) as client:
            login(client)
            saved = client.get('/api/tasks').json()
            self.assertEqual([t['id'] for t in saved],[second['id'],first['id']])
            self.assertTrue(saved[1]['completed'])
            self.assertEqual(saved[1]['notes'],note)
            self.assertEqual(client.put(f"/api/tasks/{first['id']}/notes",json={'notes':'Edited note'}).json()['notes'],'Edited note')
            self.assertEqual(client.put(f"/api/tasks/{first['id']}/notes",json={'notes':''}).json()['notes'],'')
            self.assertFalse(client.patch(f"/api/tasks/{first['id']}",json={'completed':False}).json()['completed'])
            self.assertEqual(client.delete(f"/api/tasks/{first['id']}").status_code,204)
            self.assertEqual(client.delete(f"/api/tasks/{first['id']}").status_code,404)
            self.assertEqual(len(client.get('/api/tasks').json()),1)
            details={'title':'Renamed task','due_date':'2026-01-01','priority':'high'}
            self.assertEqual(client.put(f"/api/tasks/{second['id']}/details",json=details).status_code,200)
            for invalid in [dict(details,title=' '),dict(details,due_date='2026-02-30'),dict(details,priority='urgent')]:
                self.assertEqual(client.put(f"/api/tasks/{second['id']}/details",json=invalid).status_code,422)
            client.put(f"/api/tasks/{second['id']}/notes",json={'notes':'Recover this too'})
            client.delete(f"/api/tasks/{second['id']}")
            self.assertEqual(client.get('/api/tasks').json(),[])
        with TestClient(app) as client:
            login(client)
            self.assertEqual(len(client.get('/api/tasks/trash').json()),2)
            restored=client.post(f"/api/tasks/{second['id']}/restore").json()[0]
            for key,value in details.items(): self.assertEqual(restored[key],value)
            self.assertEqual(restored['notes'],'Recover this too')
            self.assertEqual(client.post(f"/api/tasks/{second['id']}/restore").status_code,404)
            self.assertEqual(client.put(f"/api/tasks/{second['id']}/details",json=dict(details,due_date=None)).json()['due_date'],None)

    def test_existing_database_is_migrated_without_losing_tasks(self):
        legacy = Path(temporary.name) / 'legacy.sqlite3'
        with sqlite3.connect(legacy) as db:
            db.execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL)')
            db.execute("INSERT INTO tasks(title,completed,position) VALUES ('Existing task',1,0)")
        db.close()
        with patch('backend.main.DB_PATH',legacy):
            with TestClient(app) as client:
                owner=login(client)
                self.assertEqual(client.get('/api/tasks').json(),[])
                with database() as db:
                    row=db.execute('SELECT * FROM tasks WHERE id = 1').fetchone()
                    self.assertEqual(row['title'],'Existing task')
                    self.assertIsNone(row['user_id'])
                    db.execute('UPDATE tasks SET user_id = ? WHERE id = 1',(owner['id'],))
                self.assertEqual(client.put('/api/tasks/1/notes',json={'notes':'Keep this note'}).status_code,200)
            with TestClient(app) as client:
                login(client)
                self.assertEqual(client.get('/api/tasks').json()[0]['notes'],'Keep this note')

    def test_private_accounts_sessions_and_csrf(self):
        private = Path(temporary.name) / 'private.sqlite3'
        with patch('backend.main.DB_PATH',private):
            with TestClient(app) as alice, TestClient(app) as bob:
                self.assertEqual(alice.get('/api/tasks').status_code,401)
                self.assertEqual(alice.post('/api/tasks',json={'title':'No header'}).status_code,403)
                alice.headers.update(HEADERS);bob.headers.update(HEADERS)
                login(alice)
                b=bob.post('/api/auth/register',json={'username':'another_user','password':'different-long-password'})
                self.assertEqual(b.status_code,200)
                token=alice.cookies.get('little_list_session')
                task=alice.post('/api/tasks',json={'title':'Private task'}).json()
                task_id=task['id']
                self.assertEqual(bob.get('/api/tasks').json(),[])
                for method,path,body in [('patch',f'/api/tasks/{task_id}',{'completed':True}),('put',f'/api/tasks/{task_id}/notes',{'notes':'intrusion'}),('put',f'/api/tasks/{task_id}/details',{'title':'intrusion'}),('delete',f'/api/tasks/{task_id}',None),('post',f'/api/tasks/{task_id}/restore',None)]:
                    self.assertEqual(bob.request(method,path,json=body).status_code,404)
                self.assertEqual(bob.put('/api/tasks/order',json={'ids':[task_id]}).status_code,409)
                self.assertEqual(alice.post('/api/tasks',headers={'Origin':'https://evil.example'},json={'title':'CSRF'}).status_code,403)
                self.assertEqual(alice.get('/api/tasks').headers['cache-control'],'no-store')
                alice.delete(f'/api/tasks/{task_id}')
                self.assertEqual(bob.get('/api/tasks/trash').json(),[])
                self.assertEqual(bob.post(f'/api/tasks/{task_id}/restore').status_code,404)
                alice.post(f'/api/tasks/{task_id}/restore')
                with database() as db:
                    self.assertNotEqual(db.execute('SELECT password_hash FROM users WHERE username = ?',('test_owner',)).fetchone()['password_hash'],CREDENTIALS['password'])
                    self.assertIsNone(db.execute('SELECT * FROM sessions WHERE token_hash = ?',(token,)).fetchone())
            with TestClient(app) as returning:
                returning.headers.update(HEADERS)
                returning.cookies.set('little_list_session',token)
                self.assertEqual(returning.get('/api/tasks').json()[0]['title'],'Private task')
                self.assertEqual(returning.post('/api/logout').status_code,204)
                returning.cookies.set('little_list_session',token)
                self.assertEqual(returning.get('/api/tasks').status_code,401)
                self.assertEqual(returning.post('/api/auth/login',json=dict(CREDENTIALS,password='wrong-password-long')).status_code,401)
                with database() as db:
                    db.execute("UPDATE auth_attempts SET attempts = 10 WHERE key = 'user:test_owner'")
                self.assertEqual(returning.post('/api/auth/login',json=CREDENTIALS).status_code,429)

    def test_cloud_configuration_fails_closed(self):
        from backend.storage import connect
        with patch.dict(os.environ,{'REQUIRE_REMOTE_DB':'1','TURSO_DATABASE_URL':'','TURSO_AUTH_TOKEN':''}):
            with self.assertRaises(RuntimeError): connect(':memory:')
        with patch.dict(os.environ,{'TURSO_DATABASE_URL':'libsql://example.turso.io','TURSO_AUTH_TOKEN':''}):
            with self.assertRaises(RuntimeError): connect(':memory:')

if __name__ == '__main__':
    unittest.main()
