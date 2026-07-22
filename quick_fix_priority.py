# -*- coding: utf-8 -*-
import sqlite3
import shutil
from team_manager import TeamManager

tm = TeamManager()
teams = tm.get_all_teams()

target = next((t for t in teams if 'eyal' in t[1].lower()), None)
if not target:
    print("לא נמצא")
    exit(1)

db = tm.get_team_db_path(target[0])
print(f"מתקן: {target[1]}")

# גיבוי
shutil.copy2(db, db + ".backup_priority")

conn = sqlite3.connect(db)
c = conn.cursor()

# בדוק אם קיימת
c.execute("PRAGMA table_info(process_tags)")
cols = [col[1] for col in c.fetchall()]

if 'priority' not in cols:
    print("מוסיף priority...")
    c.execute("ALTER TABLE process_tags ADD COLUMN priority INTEGER DEFAULT 0")
    conn.commit()
    print("✅ נוספה")
else:
    print("✅ כבר קיימת")

conn.close()
print("✅ סיום")

