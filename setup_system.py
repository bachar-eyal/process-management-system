#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט להגדרת המערכת המלא
"""

import os
import sys
from create_main_admin import create_main_admin
from team_manager import TeamManager

def setup_system():
    """הגדרת המערכת המלא"""
    print("🔧 הגדרת מערכת הצוותים")
    print("=" * 50)
    
    # שלב 1: צור admin ראשי
    print("\n1️⃣ יצירת Admin ראשי...")
    create_main_admin()
    
    # שלב 2: אתחל את מסד הנתונים של הצוותים
    print("\n2️⃣ אתחול מסד הנתונים של הצוותים...")
    tm = TeamManager()
    print("✅ מסד הנתונים של הצוותים מוכן")
    
    print("\n✅ הגדרת המערכת הושלמה!")
    print("\n📋 פרטי התחברות:")
    print("   🔐 מסד נתונים ראשי:")
    print("      👤 שם משתמש: superadmin")
    print("      🔑 סיסמה: super1234")
    print("\n   🎯 יצירת צוותים:")
    print("      📝 הכנס את פרטי ה-Admin הראשי (superadmin/super1234)")
    print("      📝 המערכת תיצור משתמש admin חדש לצוות")
    print("\n🚀 עכשיו תוכל:")
    print("   1. להפעיל את המערכת: python app.py")
    print("   2. לגשת ל: http://localhost:5000")
    print("   3. להתחבר למסד ראשי או ליצור צוותים חדשים")

if __name__ == "__main__":
    setup_system()
