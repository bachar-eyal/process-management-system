#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט לבדיקת מסד הנתונים הראשי
"""

import sqlite3
import os

def check_main_database():
    """בודק את מסד הנתונים הראשי"""
    print("🔍 בדיקת מסד הנתונים הראשי")
    print("=" * 50)
    
    # בדוק אם קובץ database.db קיים
    if os.path.exists('database.db'):
        print("✅ קובץ database.db קיים")
    else:
        print("❌ קובץ database.db לא קיים")
        return
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # בדוק טבלאות
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 טבלאות במסד הנתונים: {[t[0] for t in tables]}")
        
        # בדוק משתמשים
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f"👤 מספר משתמשים: {users_count}")
        
        if users_count > 0:
            cursor.execute("SELECT username, role FROM users")
            users = cursor.fetchall()
            print("📋 רשימת משתמשים:")
            for user in users:
                username, role = user
                print(f"   👤 {username} ({role})")
        
        # בדוק תגים
        cursor.execute("SELECT COUNT(*) FROM process_tags")
        tags_count = cursor.fetchone()[0]
        print(f"🏷️  מספר תגים: {tags_count}")
        
        # בדוק מוצרים
        cursor.execute("SELECT COUNT(*) FROM products")
        products_count = cursor.fetchone()[0]
        print(f"📦 מספר מוצרים: {products_count}")
        
        conn.close()
        print("✅ בדיקת מסד הנתונים הושלמה בהצלחה")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקת מסד הנתונים: {e}")

if __name__ == "__main__":
    check_main_database()
