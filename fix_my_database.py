#!/usr/bin/env python3
"""
סקריפט פשוט לתיקון database ישן ספציפי
"""

import sqlite3
import os

def fix_specific_database(db_path):
    """תקן database ספציפי"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # הוסף עמודות חסרות ל-process_tags
        columns_to_add = [
            ("checker", "TEXT"),
            ("item_statuses", "TEXT"),
            ("sku", "TEXT"),
            ("performer_signature", "TEXT"),
            ("checker_signature", "TEXT")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                c.execute(f"ALTER TABLE process_tags ADD COLUMN {column_name} {column_type}")
                print(f"✅ הוספתי: {column_name}")
            except sqlite3.Error:
                print(f"ℹ️ עמודה כבר קיימת: {column_name}")
        
        # הוסף עמודה ל-team_members
        try:
            c.execute("ALTER TABLE team_members ADD COLUMN signature TEXT")
            print("✅ הוספתי: signature")
        except sqlite3.Error:
            print("ℹ️ עמודה כבר קיימת: signature")
        
        # הוסף עמודה ל-approved_skus
        try:
            c.execute("ALTER TABLE approved_skus ADD COLUMN final_check_image TEXT")
            print("✅ הוספתי: final_check_image")
        except sqlite3.Error:
            print("ℹ️ עמודה כבר קיימת: final_check_image")
        
        conn.commit()
        print("✅ תיקון הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # שנה את הנתיב לקובץ ה-database שלך
    database_path = input("הזן נתיב לקובץ ה-database שלך: ").strip()
    
    if not database_path:
        print("❌ לא הוזן נתיב")
        exit(1)
    
    if fix_specific_database(database_path):
        print("\n🎉 התיקון הושלם בהצלחה!")
        print("💡 עכשיו לחצן ההדפסה אמור לעבוד")
    else:
        print("\n❌ התיקון נכשל")
