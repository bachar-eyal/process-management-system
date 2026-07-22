#!/usr/bin/env python3
"""
סקריפט לתיקון נתונים ב-database ישן כדי שיוצגו נכון בהדפסה
"""

import sqlite3
import os
import json

def fix_database_data(db_path):
    """תקן את הנתונים ב-database כדי שיוצגו נכון בהדפסה"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן נתונים ב: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק את המבנה הנוכחי של הטבלאות
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        print(f"📋 עמודות ב-process_tags: {', '.join(columns)}")
        
        # תיקון 1: וודא שיש עמודת sku ושהיא מולאת
        if 'sku' in columns:
            print("🔧 מתקן עמודת SKU...")
            
            # עדכן תגים שאין להם SKU
            c.execute("SELECT tag_id, serial_number FROM process_tags WHERE sku IS NULL OR sku = ''")
            tags_without_sku = c.fetchall()
            
            for tag_id, serial_number in tags_without_sku:
                # חפש את ה-SKU מהמוצר
                c.execute("SELECT sku FROM products WHERE serial_number = ?", (serial_number,))
                sku_result = c.fetchone()
                if sku_result:
                    sku = sku_result[0]
                    c.execute("UPDATE process_tags SET sku = ? WHERE tag_id = ?", (sku, tag_id))
                    print(f"✅ עדכנתי תג {tag_id} עם SKU {sku}")
        
        # תיקון 2: וודא שעמודת checker מולאת
        if 'checker' in columns:
            print("🔧 מתקן עמודת checker...")
            
            # עדכן תגים שאין להם checker
            c.execute("SELECT tag_id FROM process_tags WHERE checker IS NULL OR checker = ''")
            tags_without_checker = c.fetchall()
            
            for (tag_id,) in tags_without_checker:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET checker = 'לא מוגדר' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם checker ברירת מחדל")
        
        # תיקון 3: וודא שעמודת item_statuses מולאת
        if 'item_statuses' in columns:
            print("🔧 מתקן עמודת item_statuses...")
            
            # עדכן תגים שאין להם item_statuses
            c.execute("SELECT tag_id FROM process_tags WHERE item_statuses IS NULL OR item_statuses = ''")
            tags_without_statuses = c.fetchall()
            
            for (tag_id,) in tags_without_statuses:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם item_statuses ברירת מחדל")
        
        # תיקון 4: וודא שעמודת performer_signature מולאת
        if 'performer_signature' in columns:
            print("🔧 מתקן עמודת performer_signature...")
            
            # עדכן תגים שאין להם performer_signature
            c.execute("SELECT tag_id FROM process_tags WHERE performer_signature IS NULL OR performer_signature = ''")
            tags_without_perf_sig = c.fetchall()
            
            for (tag_id,) in tags_without_perf_sig:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET performer_signature = '' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם performer_signature ברירת מחדל")
        
        # תיקון 5: וודא שעמודת checker_signature מולאת
        if 'checker_signature' in columns:
            print("🔧 מתקן עמודת checker_signature...")
            
            # עדכן תגים שאין להם checker_signature
            c.execute("SELECT tag_id FROM process_tags WHERE checker_signature IS NULL OR checker_signature = ''")
            tags_without_check_sig = c.fetchall()
            
            for (tag_id,) in tags_without_check_sig:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET checker_signature = '' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם checker_signature ברירת מחדל")
        
        # תיקון 6: וודא שעמודת test_results מולאת
        if 'test_results' in columns:
            print("🔧 מתקן עמודת test_results...")
            
            # עדכן תגים שאין להם test_results
            c.execute("SELECT tag_id FROM process_tags WHERE test_results IS NULL OR test_results = ''")
            tags_without_test_results = c.fetchall()
            
            for (tag_id,) in tags_without_test_results:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET test_results = '[]' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם test_results ברירת מחדל")
        
        # תיקון 7: וודא שעמודת performer מולאת
        if 'performer' in columns:
            print("🔧 מתקן עמודת performer...")
            
            # עדכן תגים שאין להם performer
            c.execute("SELECT tag_id FROM process_tags WHERE performer IS NULL OR performer = ''")
            tags_without_performer = c.fetchall()
            
            for (tag_id,) in tags_without_performer:
                # השתמש בערך ברירת מחדל
                c.execute("UPDATE process_tags SET performer = 'לא מוגדר' WHERE tag_id = ?", (tag_id,))
                print(f"✅ עדכנתי תג {tag_id} עם performer ברירת מחדל")
        
        conn.commit()
        print("✅ תיקון הנתונים הושלם בהצלחה!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון הנתונים: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון נתונים ב-database ישן")
    print("=" * 50)
    
    database_path = input("הזן נתיב לקובץ ה-database שלך: ").strip()
    
    if not database_path:
        print("❌ לא הוזן נתיב")
        return
    
    if fix_database_data(database_path):
        print("\n🎉 תיקון הנתונים הושלם בהצלחה!")
        print("💡 עכשיו ההדפסה אמורה להציג את כל הנתונים נכון")
        print("💡 כולל תיאור התקלה המלא ופרטי הבודק")
    else:
        print("\n❌ תיקון הנתונים נכשל")

if __name__ == "__main__":
    main()
