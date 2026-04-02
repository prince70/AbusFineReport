import sqlite3, os
p='production.db'
if not os.path.exists(p):
    print('NO_DB')
else:
    con=sqlite3.connect(p)
    c=con.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for r in c.fetchall():
        print(r[0])
    con.close()
