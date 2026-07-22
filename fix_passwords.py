#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט לתיקון כל הסיסמאות
"""

import sqlite3
import hashlib
from team_manager import TeamManager

def fix_all_passwords():
    """מתקן את כל הסיסמאות"""
    print("🔧 תיקון כל הסיסמאות")
    print("=" * 50)
    
    # סיסמה אחידה
    password = "eyal1234"
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    print(f"🔑 סיסמה: {password}")
    print(f"🔐 מוצפנת: {hashed_password}")
    
    # תיקון מסד הנתונים הראשי
    print("\n1️⃣ תיקון מסד הנתונים הראשי...")
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # עדכן את כל המשתמשים
        cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (hashed_password,))
        cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
        
        conn.commit()
        conn.close()
        print("✅ מסד הנתונים הראשי תוקן")
    except Exception as e:
        print(f"❌ שגיאה בתיקון מסד הנתונים הראשי: {e}")
    
    # תיקון צוותים
    print("\n2️⃣ תיקון צוותים...")
    tm = TeamManager()
    teams = tm.get_all_teams()
    
    for team in teams:
        team_id, team_name, created_date, is_active = team
        print(f"\n📋 צוות #{team_id}: {team_name}")
        
        try:
            # עדכן את הסיסמה במסד הנתונים של הצוותים
            conn = sqlite3.connect('teams.db')
            cursor = conn.cursor()
            
            cursor.execute("UPDATE team_users SET password = ? WHERE team_id = ? AND username = 'admin'", 
                         (hashed_password, team_id))
            
            conn.commit()
            conn.close()
            print(f"   ✅ סיסמה תוקנה")
            
            # בדוק אימות
            auth_result = tm.authenticate_user(team_id, 'admin', password)
            if auth_result:
                print(f"   ✅ אימות עובד!")
            else:
                print(f"   ❌ אימות נכשל!")
                
        except Exception as e:
            print(f"   ❌ שגיאה: {e}")
    
    print("\n✅ תיקון הסיסמאות הושלם!")

if __name__ == "__main__":
    fix_all_passwords()
