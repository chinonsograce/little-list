import os
import tempfile
import unittest
import sqlite3
from unittest.mock import patch
from pathlib import Path

temporary = tempfile.TemporaryDirectory()
os.environ['TODO_DB_PATH'] = str(Path(temporary.name) / 'test.sqlite3')
from fastapi.testclient import TestClient
from backend.main import app

class TasksTest(unittest.TestCase):
    def test_complete_workflow_and_persistence(self):
        with TestClient(app) as client:
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
                tasks=client.get('/api/tasks').json()
                self.assertEqual(tasks,[{'id':1,'title':'Existing task','completed':True,'position':0,'notes':'','due_date':None,'priority':'medium'}])
                self.assertEqual(client.put('/api/tasks/1/notes',json={'notes':'Keep this note'}).status_code,200)
            with TestClient(app) as client:
                self.assertEqual(client.get('/api/tasks').json()[0]['notes'],'Keep this note')

if __name__ == '__main__':
    unittest.main()
