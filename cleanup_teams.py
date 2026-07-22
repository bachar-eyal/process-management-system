#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

def cleanup_teams():
    """מנקה צוותים לא רצויים"""
    
    # התחבר למסד הנתונים
    conn = sqlite3.connect('teams.db')
    cursor = conn.cursor()
    
    # קבל את כל הצוותים
    cursor.execute('SELECT team_id, team_name, db_path FROM teams')
    teams = cursor.fetchall()
    
    print("צוותים קיימים:")
    for team in teams:
        print(f"ID: {team[0]}, Name: {team[1]}, DB: {team[2]}")
    
    # מחק צוותים לא רצויים
    teams_to_delete = ['צוות ברירת מחדל']
    
    for team_name in teams_to_delete:
        cursor.execute('SELECT team_id, db_path FROM teams WHERE team_name = ?', (team_name,))
        team = cursor.fetchone()
        
        if team:
            team_id, db_path = team
            print(f"\nמוחק צוות: {team_name} (ID: {team_id})")
            
            # מחק משתמשי הצוות
            cursor.execute('DELETE FROM team_users WHERE team_id = ?', (team_id,))
            
            # מחק את הצוות
            cursor.execute('DELETE FROM teams WHERE team_id = ?', (team_id,))
            
            # מחק את קובץ מסד הנתונים
            if os.path.exists(db_path):
                os.remove(db_path)
                print(f"נמחק קובץ: {db_path}")
            
            print(f"✅ צוות {team_name} נמחק בהצלחה!")
        else:
            print(f"❌ צוות {team_name} לא נמצא")
    
    conn.commit()
    conn.close()
    
    print("\n✅ ניקוי הצוותים הושלם!")

if __name__ == "__main__":
    cleanup_teams()
