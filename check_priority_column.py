# -*- coding: utf-8 -*-
import sqlite3
from team_manager import TeamManager

tm = TeamManager()
teams = tm.get_all_teams()

source = next((t for t in teams if 'בדיקה' in t[1]), None)
target = next((t for t in teams if 'eyal' in t[1].lower()), None)

if not source or not target:
    print("לא נמצאו צוותים")
    exit(1)

db1 = tm.get_team_db_path(source[0])
db2 = tm.get_team_db_path(target[0])

conn1 = sqlite3.connect(db1)
c1 = conn1.cursor()
c1.execute("PRAGMA table_info(process_tags)")
cols1 = c1.fetchall()

conn2 = sqlite3.connect(db2)
c2 = conn2.cursor()
c2.execute("PRAGMA table_info(process_tags)")
cols2 = c2.fetchall()

print("עמודה priority במקור (צוות בדיקה):")
for col in cols1:
    if col[1] == 'priority':
        print(f"  cid={col[0]}, name={col[1]}, type={col[2]}, not_null={col[3]}, default={col[4]}, pk={col[5]}")

print("\nעמודה priority ביעד (eyal):")
found = False
for col in cols2:
    if col[1] == 'priority':
        found = True
        print(f"  cid={col[0]}, name={col[1]}, type={col[2]}, not_null={col[3]}, default={col[4]}, pk={col[5]}")
if not found:
    print("  ❌ לא נמצאה!")

conn1.close()
conn2.close()

