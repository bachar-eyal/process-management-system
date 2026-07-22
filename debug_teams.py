#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט לבדיקת מערכת הצוותים
"""

import sqlite3
import os
from team_manager import TeamManager

def debug_teams_system():
    """בודק את מערכת הצוותים"""
    print("🔍 בדיקת מערכת הצוותים")
    print("=" * 50)
    
    # בדוק אם קובץ teams.db קיים
    if os.path.exists('teams.db'):
        print("✅ קובץ teams.db קיים")
    else:
        print("❌ קובץ teams.db לא קיים")
        return
    
    # בדוק אם תיקיית teams_databases קיימת
    if os.path.exists('teams_databases'):
        print("✅ תיקיית teams_databases קיימת")
        print(f"📁 תוכן התיקייה: {os.listdir('teams_databases')}")
    else:
        print("❌ תיקיית teams_databases לא קיימת")
    
    # צור instance של TeamManager
    tm = TeamManager()
    
    # בדוק את כל הצוותים
    teams = tm.get_all_teams()
    print(f"\n👥 מספר צוותים: {len(teams)}")
    
    for team in teams:
        team_id, team_name, created_date, is_active = team
        print(f"\n📋 צוות #{team_id}: {team_name}")
        print(f"   📅 נוצר ב: {created_date}")
        print(f"   ✅ פעיל: {is_active}")
        
        # בדוק מסד נתונים
        db_path = tm.get_team_db_path(team_id)
        if db_path and os.path.exists(db_path):
            print(f"   💾 מסד נתונים: {db_path}")
            
            # בדוק טבלאות
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"   📊 טבלאות: {[t[0] for t in tables]}")
                
                # בדוק מספר תגים
                cursor.execute("SELECT COUNT(*) FROM process_tags")
                tags_count = cursor.fetchone()[0]
                print(f"   🏷️  מספר תגים: {tags_count}")
                
                # בדוק מספר משתמשים
                cursor.execute("SELECT COUNT(*) FROM users")
                users_count = cursor.fetchone()[0]
                print(f"   👤 מספר משתמשים: {users_count}")
                
                conn.close()
            except Exception as e:
                print(f"   ❌ שגיאה בבדיקת מסד נתונים: {e}")
        else:
            print(f"   ❌ מסד נתונים לא נמצא: {db_path}")
    
    # בדוק משתמשים בכל צוות
    print(f"\n🔐 בדיקת משתמשים:")
    for team in teams:
        team_id = team[0]
        team_name = team[1]
        
        # בדוק משתמשים בצוות
        conn = sqlite3.connect('teams.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM team_users WHERE team_id = ?", (team_id,))
        users = cursor.fetchall()
        conn.close()
        
        print(f"\n   👥 צוות {team_name}:")
        for user in users:
            username, role = user
            print(f"      👤 {username} ({role})")

if __name__ == "__main__":
    debug_teams_system()
