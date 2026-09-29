"""Use local SQLite or a remote Turso libSQL database (never a disposable replica)."""
import os
import sqlite3


class Cursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.rowcount = cursor.rowcount

    def __iter__(self):
        columns = [column[0] for column in self.cursor.description or []]
        return iter(dict(zip(columns, row)) for row in self.cursor.fetchall())

    def fetchone(self):
        return next(iter(self), None)


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, args=()):
        return Cursor(self.connection.execute(sql, args))

    def executemany(self, sql, parameters):
        for args in parameters:
            self.execute(sql, args)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def connect(path):
    url = os.environ.get('TURSO_DATABASE_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    if bool(url) != bool(token):
        raise RuntimeError('Both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be configured.')
    if url:
        import libsql
        return Connection(libsql.connect(database=url, auth_token=token))
    if os.environ.get('REQUIRE_REMOTE_DB') == '1':
        raise RuntimeError('Cloud database credentials are required. Refusing temporary storage.')
    return Connection(sqlite3.connect(path, timeout=10))
