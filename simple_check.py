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

print("=" * 80)
print("בדיקת זהות מבנה DB")
print("=" * 80)
print(f"\nמקור: {source[1]}")
print(f"יעד: {target[1]}")

conn1 = sqlite3.connect(db1)
conn2 = sqlite3.connect(db2)

c1 = conn1.cursor()
c2 = conn2.cursor()

c1.execute("PRAGMA table_info(process_tags)")
cols1 = [(c[0], c[1], c[2]) for c in c1.fetchall()]

c2.execute("PRAGMA table_info(process_tags)")
cols2 = [(c[0], c[1], c[2]) for c in c2.fetchall()]

names1 = [c[1] for c in cols1]
names2 = [c[1] for c in cols2]

print(f"\n{'='*80}")
print("טבלת process_tags:")
print(f"{'='*80}")
print(f"\nמקור ({len(cols1)} עמודות):")
for i, (cid, name, typ) in enumerate(cols1):
    print(f"  [{cid}] {name} ({typ})")

print(f"\nיעד ({len(cols2)} עמודות):")
for i, (cid, name, typ) in enumerate(cols2):
    print(f"  [{cid}] {name} ({typ})")

print(f"\n{'='*80}")
print("תוצאות:")
print(f"{'='*80}")

same_cols = set(names1) == set(names2)
same_order = names1 == names2

if same_cols:
    print("✅ אותן עמודות")
else:
    print("❌ עמודות שונות")
    only1 = set(names1) - set(names2)
    only2 = set(names2) - set(names1)
    if only1:
        print(f"  רק במקור: {only1}")
    if only2:
        print(f"  רק ביעד: {only2}")

if same_order:
    print("✅ סדר זהה")
else:
    print("❌ סדר שונה")
    print(f"\n  מקור: {names1}")
    print(f"  יעד: {names2}")

# בדוק גם סוגים
same_types = True
if same_cols:
    for i, (col1, col2) in enumerate(zip(cols1, cols2)):
        if col1[2] != col2[2]:
            same_types = False
            print(f"\n❌ סוג שונה בעמודה {col1[1]}: {col1[2]} vs {col2[2]}")

if same_types and same_cols:
    print("✅ סוגים זהים")
elif same_cols:
    print("❌ סוגים שונים")

print(f"\n{'='*80}")
if same_cols and same_order and same_types:
    print("✅ המבנה זהה לחלוטין!")
else:
    print("⚠️  יש הבדלים במבנה")
print("=" * 80)

conn1.close()
conn2.close()
