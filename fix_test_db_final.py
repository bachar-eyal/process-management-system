import sqlite3
import os
import shutil
import json

def fix_test_database():
    """תקן את test.db"""
    
    # נתיב מוחלט
    db_path = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\test.db"
    
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
        # בדוק את המבנה הנוכחי
        c.execute("PRAGMA table_info(process_tags)")
        old_columns = [col[1] for col in c.fetchall()]
        print(f"📋 עמודות ישן: {', '.join(old_columns)}")
        
        # קבל את כל הנתונים
        c.execute("SELECT * FROM process_tags")
        all_data = c.fetchall()
        print(f"📊 מצאתי {len(all_data)} תגים")
        
        # הגדר את הסדר הנכון
        correct_order = [
            'tag_id', 'serial_number', 'fault_description', 'actions_taken',
            'status', 'date_updated', 'is_closed', 'date_opened', 'test_results',
            'performer', 'checker', 'item_statuses', 'sku', 'performer_signature', 'checker_signature'
        ]
        
        # הוסף עמודות חסרות
        missing_columns = set(correct_order) - set(old_columns)
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
        
        # צור טבלה חדשה עם הסדר הנכון
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
        
        # העבר נתונים
        for row in all_data:
            new_row = [None] * len(correct_order)
            for i, old_col in enumerate(old_columns):
                if old_col in correct_order:
                    new_index = correct_order.index(old_col)
                    new_row[new_index] = row[i]
            
            placeholders = ','.join(['?' for _ in correct_order])
            insert_sql = f"INSERT INTO process_tags_new ({','.join(correct_order)}) VALUES ({placeholders})"
            c.execute(insert_sql, new_row)
        
        # החלף טבלות
        c.execute("DROP TABLE process_tags")
        c.execute("ALTER TABLE process_tags_new RENAME TO process_tags")
        
        # עדכן נתונים חסרים
        c.execute("UPDATE process_tags SET sku = (SELECT sku FROM products WHERE products.serial_number = process_tags.serial_number LIMIT 1) WHERE sku IS NULL OR sku = ''")
        c.execute("UPDATE process_tags SET performer = 'לא מוגדר' WHERE performer IS NULL OR performer = ''")
        c.execute("UPDATE process_tags SET checker = 'לא מוגדר' WHERE checker IS NULL OR checker = ''")
        c.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL OR test_results = ''")
        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL OR item_statuses = ''")
        c.execute("UPDATE process_tags SET performer_signature = '' WHERE performer_signature IS NULL")
        c.execute("UPDATE process_tags SET checker_signature = '' WHERE checker_signature IS NULL")
        c.execute("UPDATE process_tags SET fault_description = REPLACE(fault_description, '\\\\n', CHAR(10)) WHERE fault_description LIKE '%\\\\n%'")
        
        conn.commit()
        
        # בדוק את התוצאה
        c.execute("PRAGMA table_info(process_tags)")
        new_columns = [col[1] for col in c.fetchall()]
        print(f"✅ סדר חדש: {', '.join(new_columns)}")
        
        print("✅ תיקון test.db הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    fix_test_database()
