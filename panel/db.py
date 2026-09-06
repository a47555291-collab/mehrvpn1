import sqlite3
from contextlib import contextmanager
from pathlib import Path
from .config import DB_PATH
SCHEMA='''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'admin',created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,common_name TEXT UNIQUE NOT NULL,quota_bytes INTEGER NOT NULL DEFAULT 0,used_bytes INTEGER NOT NULL DEFAULT 0,expires_at INTEGER,revoked INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
'''
def connect(path:Path=DB_PATH):
 path.parent.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(path); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); c.execute('PRAGMA journal_mode=WAL'); return c
def init_db(path:Path=DB_PATH):
 with connect(path) as c: c.executescript(SCHEMA); c.commit()
@contextmanager
def db():
 c=connect()
 try: yield c; c.commit()
 finally: c.close()
