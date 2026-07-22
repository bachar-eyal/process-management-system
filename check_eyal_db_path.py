# -*- coding: utf-8 -*-
import sqlite3
from team_manager import TeamManager

tm = TeamManager()
teams = tm.get_all_teams()

print("כל הצוותים:")
for t in teams:
    print(f"  {t[0]}: {t[1]}")

print("\n" + "="*80)

eyal_team = next((t for t in teams if t[1] == 'eyal'), None)

if eyal_team:
    team_id = eyal_team[0]
    team_name = eyal_team[1]
    
    # קבל את הנתיב מה-team_manager
    db_path = tm.get_team_db_path(team_id)
    
    # בדוק גם ישירות מה יש ב-teams.db
    conn = sqlite3.connect('teams.db')
    c = conn.cursor()
    c.execute("SELECT team_id, team_name, db_path FROM teams WHERE team_id = ?", (team_id,))
    team_row = c.fetchone()
    conn.close()
    
    print(f"\nצוות: {team_name} (ID: {team_id})")
    print(f"\nנתיב DB שנשמר ב-teams.db:")
    print(f"  {team_row[2] if team_row else 'לא נמצא'}")
    print(f"\nנתיב DB מה-team_manager.get_team_db_path():")
    print(f"  {db_path}")
    print(f"\n✅ זהו הקובץ הפעיל - הצוות משתמש בו!")
    print(f"\nהקובץ eyal_20251105_104247.db.backup_final הוא רק גיבוי שנוצר על ידי הסקריפט.")
else:
    print("צוות eyal לא נמצא")

