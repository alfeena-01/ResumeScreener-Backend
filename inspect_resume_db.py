import sqlite3, pathlib
fn=pathlib.Path('db.sqlite3')
print('db path', fn)
print('exists', fn.exists())
if not fn.exists():
    raise SystemExit(1)
conn=sqlite3.connect(fn)
cur=conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables=[r[0] for r in cur.fetchall()]
print('tables', tables)
if 'users_resume' in tables:
    cur.execute('SELECT id, user_id, resume_file, uploaded_at FROM users_resume')
    rows=cur.fetchall()
    print('users_resume count', len(rows))
    for r in rows:
        print(r)
else:
    print('users_resume table missing')
conn.close()
