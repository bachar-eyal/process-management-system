#!/usr/bin/env python3
"""
סקריפט לבדיקה ותיקון עמוק של נתונים ב-database ישן
"""

import sqlite3
import os
import json

def debug_database_data(db_path):
    """בדוק ותקן את הנתונים ב-database"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔍 בודק נתונים ב: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק את המבנה הנוכחי
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        print(f"📋 עמודות: {', '.join(columns)}")
        
        # בדוק תג לדוגמה
        c.execute("SELECT * FROM process_tags LIMIT 1")
        sample_tag = c.fetchone()
        
        if sample_tag:
            print(f"\n📊 תג לדוגמה:")
            for i, (col_name, value) in enumerate(zip(columns, sample_tag)):
                print(f"  {i}: {col_name} = '{value}'")
        
        # בדוק את תיאור התקלה בפירוט
        print(f"\n🔍 בדיקת תיאור תקלה:")
        c.execute("SELECT tag_id, fault_description FROM process_tags LIMIT 3")
        fault_descriptions = c.fetchall()
        
        for tag_id, fault_desc in fault_descriptions:
            print(f"  תג {tag_id}: '{fault_desc}'")
            if fault_desc:
                print(f"    אורך: {len(fault_desc)} תווים")
                print(f"    מכיל \\n: {'\\n' in fault_desc}")
                if '\\n' in fault_desc:
                    parts = fault_desc.split('\\n')
                    print(f"    חלקים: {len(parts)}")
                    for i, part in enumerate(parts):
                        print(f"      חלק {i}: '{part}'")
        
        # בדוק את הבודק
        print(f"\n🔍 בדיקת בודק:")
        c.execute("SELECT tag_id, checker FROM process_tags LIMIT 3")
        checkers = c.fetchall()
        
        for tag_id, checker in checkers:
            print(f"  תג {tag_id}: checker = '{checker}'")
        
        # בדוק את המבצע
        print(f"\n🔍 בדיקת מבצע:")
        c.execute("SELECT tag_id, performer FROM process_tags LIMIT 3")
        performers = c.fetchall()
        
        for tag_id, performer in performers:
            print(f"  תג {tag_id}: performer = '{performer}'")
        
        # בדוק את test_results
        print(f"\n🔍 בדיקת test_results:")
        c.execute("SELECT tag_id, test_results FROM process_tags LIMIT 3")
        test_results = c.fetchall()
        
        for tag_id, test_res in test_results:
            print(f"  תג {tag_id}: test_results = '{test_res}'")
            if test_res:
                try:
                    parsed = json.loads(test_res)
                    print(f"    JSON תקין: {parsed}")
                except:
                    print(f"    ❌ JSON לא תקין")
        
        # בדוק את item_statuses
        print(f"\n🔍 בדיקת item_statuses:")
        c.execute("SELECT tag_id, item_statuses FROM process_tags LIMIT 3")
        item_statuses = c.fetchall()
        
        for tag_id, item_stat in item_statuses:
            print(f"  תג {tag_id}: item_statuses = '{item_stat}'")
            if item_stat:
                try:
                    parsed = json.loads(item_stat)
                    print(f"    JSON תקין: {parsed}")
                except:
                    print(f"    ❌ JSON לא תקין")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקה: {e}")
        return False
    finally:
        conn.close()

def fix_specific_issues(db_path):
    """תקן בעיות ספציפיות בנתונים"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן בעיות ספציפיות ב: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # תיקון 1: תיאור תקלה עם \\n במקום \n
        print("🔧 מתקן תיאור תקלה...")
        c.execute("SELECT tag_id, fault_description FROM process_tags WHERE fault_description LIKE '%\\\\n%'")
        faulty_descriptions = c.fetchall()
        
        for tag_id, fault_desc in faulty_descriptions:
            # החלף \\n ב-\n
            fixed_desc = fault_desc.replace('\\n', '\n')
            c.execute("UPDATE process_tags SET fault_description = ? WHERE tag_id = ?", (fixed_desc, tag_id))
            print(f"✅ תיקנתי תג {tag_id}")
        
        # תיקון 2: וודא שכל השדות החדשים מולאים
        print("🔧 מוסיף ערכי ברירת מחדל...")
        
        # עדכן תגים ללא SKU
        c.execute("UPDATE process_tags SET sku = (SELECT sku FROM products WHERE products.serial_number = process_tags.serial_number LIMIT 1) WHERE sku IS NULL OR sku = ''")
        
        # עדכן תגים ללא checker
        c.execute("UPDATE process_tags SET checker = 'לא מוגדר' WHERE checker IS NULL OR checker = ''")
        
        # עדכן תגים ללא performer
        c.execute("UPDATE process_tags SET performer = 'לא מוגדר' WHERE performer IS NULL OR performer = ''")
        
        # עדכן תגים ללא test_results
        c.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL OR test_results = ''")
        
        # עדכן תגים ללא item_statuses
        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL OR item_statuses = ''")
        
        # עדכן תגים ללא חתימות
        c.execute("UPDATE process_tags SET performer_signature = '' WHERE performer_signature IS NULL")
        c.execute("UPDATE process_tags SET checker_signature = '' WHERE checker_signature IS NULL")
        
        conn.commit()
        print("✅ תיקון הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔍 סקריפט בדיקה ותיקון עמוק")
    print("=" * 50)
    
    database_path = input("הזן נתיב לקובץ ה-database שלך (או Enter לשימוש ב-database.db): ").strip()
    
    # אם לא הוזן נתיב, השתמש בברירת מחדל
    if not database_path:
        database_path = "database.db"
        print(f"🔧 משתמש בנתיב ברירת מחדל: {database_path}")
    
    # בדוק אם הקובץ קיים
    if not os.path.exists(database_path):
        print(f"❌ קובץ לא נמצא: {database_path}")
        print("💡 ודא שהנתיב נכון או שהקובץ קיים")
        return
    
    # שלב 1: בדיקה
    print("\n🔍 שלב 1: בדיקת נתונים")
    print("-" * 30)
    if not debug_database_data(database_path):
        return
    
    # שלב 2: תיקון
    print("\n🔧 שלב 2: תיקון בעיות")
    print("-" * 30)
    if not fix_specific_issues(database_path):
        return
    
    # שלב 3: בדיקה אחרי תיקון
    print("\n🔍 שלב 3: בדיקה אחרי תיקון")
    print("-" * 30)
    debug_database_data(database_path)
    
    print("\n🎉 תהליך הושלם!")
    print("💡 עכשיו נסה להדפיס שוב")

if __name__ == "__main__":
    main()
