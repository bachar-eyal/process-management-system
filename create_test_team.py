#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט ליצירת צוות בדיקה
"""

from team_manager import TeamManager

def create_test_team():
    """יוצר צוות בדיקה"""
    print("🧪 יצירת צוות בדיקה")
    print("=" * 50)
    
    tm = TeamManager()
    
    # צור צוות בדיקה
    team_name = "צוות בדיקה"
    admin_username = "admin"
    admin_password = "eyal1234"
    
    print(f"📋 שם הצוות: {team_name}")
    print(f"👤 שם משתמש: {admin_username}")
    print(f"🔑 סיסמה: {admin_password}")
    
    # בדוק אם הצוות כבר קיים
    if tm.team_exists(team_name):
        print("⚠️  הצוות כבר קיים!")
        return
    
    # צור את הצוות
    result = tm.create_team(team_name, admin_username, admin_password)
    
    if result['success']:
        print("✅ צוות נוצר בהצלחה!")
        print(f"🆔 ID צוות: {result['team_id']}")
        
        # בדוק את הצוות שנוצר
        teams = tm.get_all_teams()
        for team in teams:
            if team[1] == team_name:
                team_id = team[0]
                print(f"📊 פרטי צוות:")
                print(f"   🆔 ID: {team_id}")
                print(f"   📋 שם: {team[1]}")
                print(f"   📅 נוצר: {team[2]}")
                print(f"   ✅ פעיל: {team[3]}")
                
                # בדוק מסד נתונים
                db_path = tm.get_team_db_path(team_id)
                print(f"   💾 מסד נתונים: {db_path}")
                
                # בדוק משתמש
                auth_result = tm.authenticate_user(team_id, admin_username, admin_password)
                if auth_result:
                    print(f"   ✅ אימות משתמש עובד!")
                else:
                    print(f"   ❌ אימות משתמש נכשל!")
                break
    else:
        print(f"❌ שגיאה ביצירת צוות: {result['message']}")

if __name__ == "__main__":
    create_test_team()
