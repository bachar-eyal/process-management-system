#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט לתיקון המערכת
"""

import os
import sys
from create_admin_user import create_admin_user
from create_test_team import create_test_team
from debug_teams import debug_teams_system
from test_auth import test_authentication

def fix_system():
    """תיקון המערכת"""
    print("🔧 תיקון מערכת הצוותים")
    print("=" * 50)
    
    # שלב 1: צור משתמש admin במסד הנתונים הראשי
    print("\n1️⃣ יצירת משתמש admin במסד הנתונים הראשי...")
    create_admin_user()
    
    # שלב 2: צור צוות בדיקה
    print("\n2️⃣ יצירת צוות בדיקה...")
    create_test_team()
    
    # שלב 3: בדוק את המערכת
    print("\n3️⃣ בדיקת מערכת הצוותים...")
    debug_teams_system()
    
    # שלב 4: בדוק אימות
    print("\n4️⃣ בדיקת אימות משתמשים...")
    test_authentication()
    
    print("\n✅ תיקון המערכת הושלם!")
    print("\n🚀 עכשיו תוכל:")
    print("   1. להפעיל את המערכת: python app.py")
    print("   2. לגשת ל: http://localhost:5000")
    print("   3. לבחור צוות ולהתחבר עם admin/eyal1234")

if __name__ == "__main__":
    fix_system()
