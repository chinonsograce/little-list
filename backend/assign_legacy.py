"""Explicitly assign old unowned tasks after the owner creates an app account."""
import argparse
from backend.main import database

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Assign preserved legacy tasks to an existing account.')
    parser.add_argument('--username', required=True)
    args = parser.parse_args()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        user = db.execute('SELECT id FROM users WHERE username = ?', (args.username.lower(),)).fetchone()
        if not user:
            raise SystemExit('Create that account in the app first.')
        count = db.execute('UPDATE tasks SET user_id = ? WHERE user_id IS NULL', (user['id'],)).rowcount
    print(f'Assigned {count} preserved tasks.')
