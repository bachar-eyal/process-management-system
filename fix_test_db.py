#!/usr/bin/env python3
"""
סקריפט לבדיקה ותיקון של test.db
"""

import sqlite3
import os
import shutil
import json

def check_test_db():
    """בדוק את test.db"""
    
    db_path = "teams_databases/test.db"
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔍 בודק: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק טבלאות
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        print(f"📋 טבלאות: {', '.join(tables)}")
        
        # בדוק מבנה process_tags
        if 'process_tags' in tables:
            c.execute("PRAGMA table_info(process_tags)")
            columns = c.fetchall()
            print(f"\n📊 עמודות ב-process_tags ({len(columns)}):")
            for i, (cid, name, type_, notnull, default, pk) in enumerate(columns):
                print(f"  {i}: {name} ({type_})")
            
            # בדוק כמה תגים יש
            c.execute("SELECT COUNT(*) FROM process_tags")
            count = c.fetchone()[0]
            print(f"\n📈 מספר תגים: {count}")
            
            # בדוק תג לדוגמה
            if count > 0:
                c.execute("SELECT * FROM process_tags LIMIT 1")
                sample = c.fetchone()
                print(f"\n📊 תג לדוגמה:")
                for i, (col_name, value) in enumerate(zip([col[1] for col in columns], sample)):
                    print(f"  {i}: {col_name} = '{value}'")
        
        # בדוק מבנה team_members
        if 'team_members' in tables:
            c.execute("PRAGMA table_info(team_members)")
            team_columns = c.fetchall()
            print(f"\n👥 עמודות ב-team_members ({len(team_columns)}):")
            for i, (cid, name, type_, notnull, default, pk) in enumerate(team_columns):
                print(f"  {i}: {name} ({type_})")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        return False
    finally:
        conn.close()

def fix_test_db():
    """תקן את test.db"""
    
    db_path = "teams_databases/test.db"
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן: {db_path}")
    
    # יצור גיבוי
    backup_path = db_path + ".backup"
    shutil.copy2(db_path, backup_path)
    print(f"💾 יצרתי גיבוי: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # קבל את כל הנתונים מהטבלה הישנה
        c.execute("SELECT * FROM process_tags")
        all_data = c.fetchall()
        
        print(f"📊 מצאתי {len(all_data)} תגים")
        
        # קבל את המבנה הנוכחי
        c.execute("PRAGMA table_info(process_tags)")
        old_columns = [col[1] for col in c.fetchall()]
        print(f"📋 עמודות ישן: {', '.join(old_columns)}")
        
        # הגדר את הסדר הנכון של העמודות
        correct_order = [
            'tag_id',
            'serial_number', 
            'fault_description',
            'actions_taken',
            'status',
            'date_updated',
            'is_closed',
            'date_opened',
            'test_results',
            'performer',
            'checker',
            'item_statuses',
            'sku',
            'performer_signature',
            'checker_signature'
        ]
        
        print(f"📋 סדר נכון: {', '.join(correct_order)}")
        
        # בדוק אילו עמודות חסרות
        missing_columns = set(correct_order) - set(old_columns)
        if missing_columns:
            print(f"⚠️ עמודות חסרות: {', '.join(missing_columns)}")
            
            # הוסף עמודות חסרות
            for col in missing_columns:
                if col == 'checker':
                    c.execute("ALTER TABLE process_tags ADD COLUMN checker TEXT")
                elif col == 'item_statuses':
                    c.execute("ALTER TABLE process_tags ADD COLUMN item_statuses TEXT")
                elif col == 'sku':
                    c.execute("ALTER TABLE process_tags ADD COLUMN sku TEXT")
                elif col == 'performer_signature':
                    c.execute("ALTER TABLE process_tags ADD COLUMN performer_signature TEXT")
                elif col == 'checker_signature':
                    c.execute("ALTER TABLE process_tags ADD COLUMN checker_signature TEXT")
                print(f"✅ הוספתי עמודה: {col}")
        
        # עכשיו נצטרך ליצור טבלה חדשה עם הסדר הנכון
        print(f"\n🔧 יוצר טבלה חדשה עם סדר נכון...")
        
        # צור טבלה זמנית עם הסדר הנכון
        create_sql = """
        CREATE TABLE process_tags_new (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT,
            fault_description TEXT,
            actions_taken TEXT,
            status TEXT,
            date_updated DATETIME,
            is_closed INTEGER DEFAULT 0,
            date_opened DATETIME,
            test_results TEXT,
            performer TEXT,
            checker TEXT,
            item_statuses TEXT,
            sku TEXT,
            performer_signature TEXT,
            checker_signature TEXT
        )
        """
        
        c.execute(create_sql)
        
        # העבר את הנתונים מהטבלה הישנה לחדשה
        print(f"📊 מעביר נתונים...")
        
        for row in all_data:
            # צור רשימה עם הערכים בסדר הנכון
            new_row = [None] * len(correct_order)
            
            # העבר את הערכים מהמיקומים הישנים לחדשים
            for i, old_col in enumerate(old_columns):
                if old_col in correct_order:
                    new_index = correct_order.index(old_col)
                    new_row[new_index] = row[i]
            
            # הוסף את השורה החדשה
            placeholders = ','.join(['?' for _ in correct_order])
            insert_sql = f"INSERT INTO process_tags_new ({','.join(correct_order)}) VALUES ({placeholders})"
            c.execute(insert_sql, new_row)
        
        # מחק את הטבלה הישנה ושנה את שם החדשה
        c.execute("DROP TABLE process_tags")
        c.execute("ALTER TABLE process_tags_new RENAME TO process_tags")
        
        # עדכן את הנתונים החסרים
        print(f"🔧 מעדכן נתונים חסרים...")
        
        # עדכן SKU חסר
        c.execute("UPDATE process_tags SET sku = (SELECT sku FROM products WHERE products.serial_number = process_tags.serial_number LIMIT 1) WHERE sku IS NULL OR sku = ''")
        
        # עדכן מבצעים חסרים
        c.execute("UPDATE process_tags SET performer = 'לא מוגדר' WHERE performer IS NULL OR performer = ''")
        
        # עדכן בודקים חסרים
        c.execute("UPDATE process_tags SET checker = 'לא מוגדר' WHERE checker IS NULL OR checker = ''")
        
        # עדכן שדות JSON
        c.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL OR test_results = ''")
        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL OR item_statuses = ''")
        
        # עדכן חתימות
        c.execute("UPDATE process_tags SET performer_signature = '' WHERE performer_signature IS NULL")
        c.execute("UPDATE process_tags SET checker_signature = '' WHERE checker_signature IS NULL")
        
        # תיקון תיאור תקלה
        c.execute("UPDATE process_tags SET fault_description = REPLACE(fault_description, '\\\\n', CHAR(10)) WHERE fault_description LIKE '%\\\\n%'")
        
        conn.commit()
        
        # בדוק את התוצאה
        c.execute("PRAGMA table_info(process_tags)")
        new_columns = [col[1] for col in c.fetchall()]
        print(f"✅ סדר חדש: {', '.join(new_columns)}")
        
        # בדוק תג לדוגמה
        c.execute("SELECT * FROM process_tags LIMIT 1")
        sample = c.fetchone()
        if sample:
            print(f"\n📊 תג לדוגמה אחרי תיקון:")
            for i, (col_name, value) in enumerate(zip(new_columns, sample)):
                print(f"  {i}: {col_name} = '{value}'")
        
        print("✅ תיקון test.db הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון test.db")
    print("=" * 50)
    
    # שלב 1: בדיקה
    print("\n🔍 שלב 1: בדיקת test.db")
    print("-" * 40)
    if not check_test_db():
        return
    
    # שלב 2: תיקון
    print("\n🔧 שלב 2: תיקון test.db")
    print("-" * 40)
    if not fix_test_db():
        return
    
    # שלב 3: בדיקה אחרי תיקון
    print("\n🔍 שלב 3: בדיקה אחרי תיקון")
    print("-" * 40)
    check_test_db()
    
    print("\n🎉 תיקון הושלם בהצלחה!")
    print("💡 עכשיו test.db אמור להיות כמו שאר הdatabases")
    print("💡 ההדפסה אמורה לעבוד נכון עכשיו")

if __name__ == "__main__":
    main()
