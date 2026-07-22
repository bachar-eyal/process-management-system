import sqlite3
import os
from team_manager import TeamManager

tm = TeamManager()
teams = tm.get_all_teams()

print("צוותים:")
for t in teams:
    print(f"  {t[0]}: {t[1]}")

# מצא את הצוותים
team1 = None
team2 = None
for t in teams:
    if 'בדיקה' in t[1]:
        team1 = t
    if 'eyal' in t[1].lower():
        team2 = t

if team1 and team2:
    db1 = tm.get_team_db_path(team1[0])
    db2 = tm.get_team_db_path(team2[0])
    
    print(f"\n{team1[1]}: {db1}")
    print(f"{team2[1]}: {db2}")
    
    # השווה process_tags
    conn1 = sqlite3.connect(db1)
    c1 = conn1.cursor()
    c1.execute("PRAGMA table_info(process_tags)")
    cols1 = {col[1]: col[2] for col in c1.fetchall()}
    conn1.close()
    
    conn2 = sqlite3.connect(db2)
    c2 = conn2.cursor()
    c2.execute("PRAGMA table_info(process_tags)")
    cols2 = {col[1]: col[2] for col in c2.fetchall()}
    conn2.close()
    
    print("\nעמודות ב-process_tags:")
    all_cols = set(cols1.keys()) | set(cols2.keys())
    for col in sorted(all_cols):
        in1 = col in cols1
        in2 = col in cols2
        if in1 and in2:
            if cols1[col] != cols2[col]:
                print(f"  {col}: {cols1[col]} vs {cols2[col]} ⚠️")
            else:
                print(f"  {col}: ✅ זהה")
        elif in1:
            print(f"  {col}: רק ב-{team1[1]}")
        else:
            print(f"  {col}: רק ב-{team2[1]}")

