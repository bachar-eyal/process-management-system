# -*- coding: utf-8 -*-
import sqlite3
import os
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

def get_cols(db, table):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    cols = [(c[0], c[1], c[2]) for c in c.fetchall()]
    conn.close()
    return cols

print("=" * 80)
print("בדיקת זהות מבנה DB")
print("=" * 80)

for table in ['process_tags', 'spare_parts', 'approved_skus', 'approved_issues', 'team_members']:
    print(f"\n{table}:")
    cols1 = get_cols(db1, table)
    cols2 = get_cols(db2, table)
    
    names1 = [c[1] for c in cols1]
    names2 = [c[1] for c in cols2]
    
    same_order = names1 == names2
    same_cols = set(names1) == set(names2)
    
    if same_order and same_cols:
        print("  ✅ זהה")
    else:
        if not same_cols:
            print(f"  ❌ עמודות שונות")
            only1 = set(names1) - set(names2)
            only2 = set(names2) - set(names1)
            if only1:
                print(f"    רק במקור: {only1}")
            if only2:
                print(f"    רק ביעד: {only2}")
        if not same_order:
            print(f"  ❌ סדר שונה")
            print(f"    מקור: {names1}")
            print(f"    יעד: {names2}")

