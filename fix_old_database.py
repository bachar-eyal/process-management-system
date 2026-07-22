#!/usr/bin/env python3
"""
סקריפט לתיקון database ישן כדי שיעבוד עם הקוד החדש
הסקריפט מוסיף עמודות חסרות לטבלאות הקיימות
"""

import sqlite3
import os
import sys

def fix_database(db_path):
    """תקן database ישן על ידי הוספת עמודות חסרות"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ ה-database לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק אילו טבלאות קיימות
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        print(f"📋 טבלאות קיימות: {', '.join(tables)}")
        
        # תיקון טבלת process_tags
        if 'process_tags' in tables:
            print("🔧 מתקן טבלת process_tags...")
            
            # בדוק אילו עמודות קיימות
            c.execute("PRAGMA table_info(process_tags)")
            existing_columns = [col[1] for col in c.fetchall()]
            print(f"📋 עמודות קיימות ב-process_tags: {', '.join(existing_columns)}")
            
            # רשימת עמודות שצריכות להיות קיימות
            required_columns = {
                'checker': 'TEXT',
                'item_statuses': 'TEXT', 
                'sku': 'TEXT',
                'performer_signature': 'TEXT',
                'checker_signature': 'TEXT'
            }
            
            # הוסף עמודות חסרות
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    try:
                        c.execute(f"ALTER TABLE process_tags ADD COLUMN {column_name} {column_type}")
                        print(f"✅ הוספתי עמודה: {column_name}")
                    except sqlite3.Error as e:
                        print(f"⚠️ שגיאה בהוספת עמודה {column_name}: {e}")
        
        # תיקון טבלת team_members
        if 'team_members' in tables:
            print("🔧 מתקן טבלת team_members...")
            
            c.execute("PRAGMA table_info(team_members)")
            existing_columns = [col[1] for col in c.fetchall()]
            print(f"📋 עמודות קיימות ב-team_members: {', '.join(existing_columns)}")
            
            # הוסף עמודות חסרות
            if 'signature' not in existing_columns:
                try:
                    c.execute("ALTER TABLE team_members ADD COLUMN signature TEXT")
                    print("✅ הוספתי עמודה: signature")
                except sqlite3.Error as e:
                    print(f"⚠️ שגיאה בהוספת עמודה signature: {e}")
        
        # תיקון טבלת approved_skus
        if 'approved_skus' in tables:
            print("🔧 מתקן טבלת approved_skus...")
            
            c.execute("PRAGMA table_info(approved_skus)")
            existing_columns = [col[1] for col in c.fetchall()]
            print(f"📋 עמודות קיימות ב-approved_skus: {', '.join(existing_columns)}")
            
            # הוסף עמודות חסרות
            if 'final_check_image' not in existing_columns:
                try:
                    c.execute("ALTER TABLE approved_skus ADD COLUMN final_check_image TEXT")
                    print("✅ הוספתי עמודה: final_check_image")
                except sqlite3.Error as e:
                    print(f"⚠️ שגיאה בהוספת עמודה final_check_image: {e}")
        
        # וודא שטבלת spare_parts קיימת
        if 'spare_parts' not in tables:
            print("🔧 יוצר טבלת spare_parts...")
            c.execute('''CREATE TABLE spare_parts
                         (part_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          part_number TEXT UNIQUE NOT NULL,
                          description TEXT,
                          manufacturer TEXT,
                          date_added DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            print("✅ יצרתי טבלת spare_parts")
        
        # וודא שטבלת spare_parts_usage קיימת
        if 'spare_parts_usage' not in tables:
            print("🔧 יוצר טבלת spare_parts_usage...")
            c.execute('''CREATE TABLE spare_parts_usage
                         (usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          tag_id INTEGER,
                          part_id INTEGER,
                          serial_number TEXT,
                          date_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY (tag_id) REFERENCES process_tags (tag_id),
                          FOREIGN KEY (part_id) REFERENCES spare_parts (part_id))''')
            print("✅ יצרתי טבלת spare_parts_usage")
        
        conn.commit()
        print("✅ תיקון ה-database הושלם בהצלחה!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון ה-database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון database ישן")
    print("=" * 50)
    
    # חפש קבצי database
    possible_paths = [
        'database.db',
        'teams_databases',
        'teams.db'
    ]
    
    databases_found = []
    
    for path in possible_paths:
        if os.path.exists(path):
            if os.path.isfile(path) and path.endswith('.db'):
                databases_found.append(path)
            elif os.path.isdir(path):
                # חפש קבצי .db בתיקייה
                for file in os.listdir(path):
                    if file.endswith('.db'):
                        databases_found.append(os.path.join(path, file))
    
    if not databases_found:
        print("❌ לא נמצאו קבצי database")
        return
    
    print(f"📋 נמצאו {len(databases_found)} קבצי database:")
    for i, db_path in enumerate(databases_found, 1):
        print(f"  {i}. {db_path}")
    
    print("\n🔧 מתחיל תיקון...")
    
    success_count = 0
    for db_path in databases_found:
        print(f"\n{'='*50}")
        if fix_database(db_path):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ סיום: תוקנו {success_count} מתוך {len(databases_found)} databases")
    
    if success_count == len(databases_found):
        print("🎉 כל ה-databases תוקנו בהצלחה!")
        print("💡 עכשיו לחצן ההדפסה אמור לעבוד")
    else:
        print("⚠️ חלק מה-databases לא תוקנו. בדוק את השגיאות למעלה")

if __name__ == "__main__":
    main()
