#!/usr/bin/env python3
"""TABLEAU NICOLA — kanban web, auth simple, données SQLite, sync Obsidian."""
import os, json, time, sqlite3, hashlib, hmac, secrets
from flask import Flask, request, jsonify, send_from_directory, session, redirect

DB = os.environ.get('BOARD_DB', '/app/data/board.db')
SECRET = os.environ.get('BOARD_SECRET', secrets.token_hex(32))
PASSWORD_HASH = os.environ.get('BOARD_PASSWORD_HASH')  # sha256 hex

app = Flask(__name__, static_folder='static')
app.secret_key = SECRET
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=30)

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  groupe TEXT NOT NULL,          -- apps | web | projets | vie-pro | vie-perso
  site TEXT DEFAULT '',          -- site web rattaché (ex: angelsfinance.net)
  title TEXT NOT NULL,
  detail TEXT DEFAULT '',
  status TEXT DEFAULT 'todo',    -- todo | doing | done
  prio INTEGER DEFAULT 2,       -- 1 haute 2 normale 3 basse
  due TEXT DEFAULT '',          -- date ISO
  created_at REAL, updated_at REAL, done_at REAL
);
CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, label TEXT, pos INTEGER);
"""

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c

DEFAULT_GROUPS = [('apps','Apps',1),('web','Sites Web',2),('projets','Projets',3),('vie-pro','Vie Pro',4),('vie-perso','Vie Perso',5)]

def migrate():
    # migration ad-hoc: ajouter la colonne site si absente
    c = db()
    cols = [r[1] for r in c.execute('PRAGMA table_info(items)')]
    if 'site' not in cols:
        c.execute('ALTER TABLE items ADD COLUMN site TEXT DEFAULT \'\'')
        c.commit()
    c.close()

def init_groups():
    c = db()
    for g in DEFAULT_GROUPS:
        c.execute('INSERT OR IGNORE INTO groups VALUES (?,?,?)', g)
    c.commit(); c.close()

@app.route('/api/login', methods=['POST'])
def login():
    p = request.json.get('password','')
    if PASSWORD_HASH and hmac.compare_digest(hashlib.sha256(p.encode()).hexdigest(), PASSWORD_HASH):
        session['ok'] = True
        session.permanent = True  # cookie 30 jours, plus de re-login à chaque visite
        return jsonify(ok=True)
    return jsonify(ok=False), 401

@app.route('/api/items')
def items():
    if not session.get('ok'): return jsonify(err='login'), 401
    c = db(); rows = [dict(r) for r in c.execute('SELECT * FROM items ORDER BY groupe, prio, id DESC')]
    c.close(); return jsonify(rows)

@app.route('/api/items', methods=['POST'])
def add():
    if not session.get('ok'): return jsonify(err='login'), 401
    d = request.json
    c = db(); now = time.time()
    cur = c.execute('INSERT INTO items (groupe,site,title,detail,status,prio,due,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',
        (d.get('groupe','projets'), d.get('site',''), d.get('title',''), d.get('detail',''), d.get('status','todo'), d.get('prio',2), d.get('due',''), now, now))
    c.commit(); nid = cur.lastrowid; c.close()
    return jsonify(id=nid)

@app.route('/api/items/<int:iid>', methods=['PATCH'])
def patch(iid):
    if not session.get('ok'): return jsonify(err='login'), 401
    d = request.json
    fields = {k: d[k] for k in ('title','detail','status','prio','due','groupe','site') if k in d}
    fields['updated_at'] = time.time()
    if 'status' in d: fields['done_at'] = time.time() if d['status']=='done' else None
    c = db()
    sets = ','.join(f'{k}=?' for k in fields)
    c.execute(f'UPDATE items SET {sets} WHERE id=?', list(fields.values())+[iid])
    c.commit(); c.close()
    return jsonify(ok=True)

@app.route('/api/items/<int:iid>', methods=['DELETE'])
def dele(iid):
    if not session.get('ok'): return jsonify(err='login'), 401
    c = db(); c.execute('DELETE FROM items WHERE id=?',(iid,)); c.commit(); c.close()
    return jsonify(ok=True)

@app.route('/api/sites')
def sites():
    if not session.get('ok'): return jsonify(err='login'), 401
    c = db()
    rows = [dict(r) for r in c.execute('SELECT site, COUNT(*) as n FROM items WHERE site != \'\' GROUP BY site ORDER BY n DESC')]
    c.close(); return jsonify(rows)

@app.route('/api/groups')
def groups():
    if not session.get('ok'): return jsonify(err='login'), 401
    c = db(); rows = [dict(r) for r in c.execute('SELECT * FROM groups ORDER BY pos')]
    c.close(); return jsonify(rows)

@app.route('/')
def index():
    return send_from_directory('static','index.html')

migrate()
migrate()
init_groups()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
