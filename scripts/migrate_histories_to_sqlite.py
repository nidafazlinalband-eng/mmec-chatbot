"""
Migrate JSON histories and settings into a single SQLite database (data/mmec.db).
Usage:
    python scripts/migrate_histories_to_sqlite.py

This script will:
 - create data/mmec.db if missing
 - create tables: users, histories, settings
 - import JSON files from data/histories/*.json
 - import data/settings.json if present

After running, you can open the DB with the sqlite3 CLI or tools like DB Browser for SQLite.
"""
import os
import json
import sqlite3
from glob import glob

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
DB_PATH = os.path.join(DATA_DIR, 'mmec.db')
HIST_DIR = os.path.join(DATA_DIR, 'histories')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HIST_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    role TEXT,
    extra TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    role TEXT,
    sender TEXT,
    text TEXT,
    ts TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)''')

conn.commit()

# Import histories
count = 0
for path in glob(os.path.join(HIST_DIR, '*.json')):
    try:
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'r', encoding='utf-8') as f:
            lst = json.load(f)
        for item in lst:
            sender = item.get('from') or item.get('sender') or 'user'
            text = item.get('text') or item.get('message') or ''
            ts = item.get('ts') or item.get('timestamp') or ''
            role = item.get('role') or name
            c.execute('INSERT INTO histories (username, role, sender, text, ts) VALUES (?,?,?,?,?)', (name, role, sender, text, ts))
            count += 1
    except Exception as e:
        print('Failed to import', path, e)

# Import settings.json
settings_path = os.path.join(DATA_DIR, 'settings.json')
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            s = json.load(f)
        for k, v in s.items():
            c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (k, json.dumps(v)))
    except Exception as e:
        print('Failed to import settings', e)

conn.commit()
conn.close()
print('Imported', count, 'history rows into', DB_PATH)
