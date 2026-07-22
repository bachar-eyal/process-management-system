# -*- coding: utf-8 -*-
from team_manager import TeamManager

tm = TeamManager()
teams = tm.get_all_teams()

eyal_team = next((t for t in teams if t[1] == 'eyal'), None)

if eyal_team:
    team_id = eyal_team[0]
    team_name = eyal_team[1]
    db_path = tm.get_team_db_path(team_id)
    
    print(f"צוות: {team_name} (ID: {team_id})")
    print(f"משתמש ב-DB: {db_path}")
    print(f"\nזהו הקובץ הפעיל - לא הגיבוי!")
    print(f"הגיבוי (.backup_final) הוא רק עותק לשם בטחון.")
else:
    print("צוות eyal לא נמצא")

