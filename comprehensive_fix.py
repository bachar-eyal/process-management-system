#!/usr/bin/env python3
"""
סקריפט מקיף לתיקון כל הבעיות ב-database ישן
"""

import sqlite3
import os
import json
import re

def comprehensive_fix(db_path):
    """תיקון מקיף של כל הבעיות ב-database"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 תיקון מקיף של: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # שלב 1: בדוק את המבנה
        print("\n📋 שלב 1: בדיקת מבנה")
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        print(f"עמודות: {', '.join(columns)}")
        
        # שלב 2: תיקון מבנה הטבלה
        print("\n🔧 שלב 2: תיקון מבנה")
        required_columns = {
            'checker': 'TEXT',
            'item_statuses': 'TEXT',
            'sku': 'TEXT',
            'performer_signature': 'TEXT',
            'checker_signature': 'TEXT'
        }
        
        for column_name, column_type in required_columns.items():
            if column_name not in columns:
                try:
                    c.execute(f"ALTER TABLE process_tags ADD COLUMN {column_name} {column_type}")
                    print(f"✅ הוספתי עמודה: {column_name}")
                except sqlite3.Error as e:
                    print(f"⚠️ שגיאה בהוספת {column_name}: {e}")
        
        # שלב 3: תיקון נתונים
        print("\n🔧 שלב 3: תיקון נתונים")
        
        # תיקון SKU
        c.execute("UPDATE process_tags SET sku = (SELECT sku FROM products WHERE products.serial_number = process_tags.serial_number LIMIT 1) WHERE sku IS NULL OR sku = ''")
        
        # תיקון תיאור תקלה
        c.execute("UPDATE process_tags SET fault_description = REPLACE(fault_description, '\\\\n', CHAR(10)) WHERE fault_description LIKE '%\\\\n%'")
        
        # תיקון מבצעים
        c.execute("SELECT COUNT(*) FROM team_members WHERE role = 'מבצע' OR role = 'performer'")
        performer_count = c.fetchone()[0]
        
        if performer_count > 0:
            c.execute("UPDATE process_tags SET performer = (SELECT name || ' (' || id_number || ')' FROM team_members WHERE role = 'מבצע' OR role = 'performer' LIMIT 1) WHERE performer IS NULL OR performer = '' OR performer = 'לא מוגדר'")
        else:
            c.execute("UPDATE process_tags SET performer = (SELECT name || ' (' || id_number || ')' FROM team_members LIMIT 1) WHERE performer IS NULL OR performer = '' OR performer = 'לא מוגדר'")
        
        # תיקון בודקים
        c.execute("SELECT COUNT(*) FROM team_members WHERE role = 'בודק' OR role = 'checker'")
        checker_count = c.fetchone()[0]
        
        if checker_count > 0:
            c.execute("UPDATE process_tags SET checker = (SELECT name || ' (' || id_number || ')' FROM team_members WHERE role = 'בודק' OR role = 'checker' LIMIT 1) WHERE checker IS NULL OR checker = '' OR checker = 'לא מוגדר'")
        else:
            c.execute("UPDATE process_tags SET checker = (SELECT name || ' (' || id_number || ')' FROM team_members WHERE role != 'מבצע' AND role != 'performer' LIMIT 1) WHERE checker IS NULL OR checker = '' OR checker = 'לא מוגדר'")
        
        # תיקון שדות JSON
        c.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL OR test_results = ''")
        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL OR item_statuses = ''")
        
        # תיקון חתימות
        c.execute("UPDATE process_tags SET performer_signature = '' WHERE performer_signature IS NULL")
        c.execute("UPDATE process_tags SET checker_signature = '' WHERE checker_signature IS NULL")
        
        # שלב 4: עדכון חתימות
        print("\n🔧 שלב 4: עדכון חתימות")
        
        # עדכן חתימות מבצע
        c.execute("SELECT tag_id, performer FROM process_tags WHERE performer IS NOT NULL AND performer != ''")
        tags_with_performer = c.fetchall()
        
        for tag_id, performer in tags_with_performer:
            id_match = re.search(r'\((\d+)\)', performer)
            if id_match:
                performer_id = id_match.group(1)
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (performer_id,))
                sig_result = c.fetchone()
                if sig_result and sig_result[0]:
                    c.execute("UPDATE process_tags SET performer_signature = ? WHERE tag_id = ?", (sig_result[0], tag_id))
        
        # עדכן חתימות בודק
        c.execute("SELECT tag_id, checker FROM process_tags WHERE checker IS NOT NULL AND checker != ''")
        tags_with_checker = c.fetchall()
        
        for tag_id, checker in tags_with_checker:
            id_match = re.search(r'\((\d+)\)', checker)
            if id_match:
                checker_id = id_match.group(1)
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (checker_id,))
                sig_result = c.fetchone()
                if sig_result and sig_result[0]:
                    c.execute("UPDATE process_tags SET checker_signature = ? WHERE tag_id = ?", (sig_result[0], tag_id))
        
        conn.commit()
        print("✅ תיקון מקיף הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_fix(db_path):
    """בדוק שהתיקון עבד"""
    
    if not os.path.exists(db_path):
        return False
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק תג לדוגמה
        c.execute("SELECT tag_id, serial_number, sku, fault_description, performer, checker FROM process_tags LIMIT 1")
        sample = c.fetchone()
        
        if sample:
            tag_id, serial, sku, fault_desc, performer, checker = sample
            print(f"\n📊 בדיקת תיקון - תג {tag_id}:")
            print(f"  מספר סידורי: {serial}")
            print(f"  SKU: {sku}")
            print(f"  תיאור תקלה: '{fault_desc[:50]}...' (אורך: {len(fault_desc)})")
            print(f"  מבצע: {performer}")
            print(f"  בודק: {checker}")
            
            # בדוק אם יש שורות חדשות בתיאור
            if '\n' in fault_desc:
                parts = fault_desc.split('\n')
                print(f"  תיאור מחולק ל-{len(parts)} חלקים")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקה: {e}")
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון מקיף")
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
    
    if comprehensive_fix(database_path):
        print("\n🔍 בודק את התיקון...")
        if verify_fix(database_path):
            print("\n🎉 תיקון הושלם בהצלחה!")
            print("💡 עכשיו ההדפסה אמורה לעבוד כמו ב-database החדש")
            print("💡 כולל תיאור תקלה מלא ושמות הבודק והמבצע")
        else:
            print("\n⚠️ התיקון הושלם אבל יש בעיות בבדיקה")
    else:
        print("\n❌ תיקון נכשל")

if __name__ == "__main__":
    main()
