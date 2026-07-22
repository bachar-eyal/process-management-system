#!/usr/bin/env python3
"""
סקריפט לתיקון בעיות JSON ב-database ישן
"""

import sqlite3
import os
import json

def fix_json_issues(db_path):
    """תקן בעיות JSON ב-database"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן בעיות JSON ב: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק את כל התגים
        c.execute("SELECT tag_id, test_results, item_statuses FROM process_tags")
        tags = c.fetchall()
        
        print(f"📊 מצאתי {len(tags)} תגים לבדיקה")
        
        fixed_count = 0
        
        for tag_id, test_results, item_statuses in tags:
            tag_fixed = False
            
            # תיקון test_results
            if test_results:
                try:
                    # נסה לפרסר את ה-JSON
                    parsed = json.loads(test_results)
                    if not isinstance(parsed, list):
                        # אם זה לא רשימה, שנה לרשימה ריקה
                        c.execute("UPDATE process_tags SET test_results = '[]' WHERE tag_id = ?", (tag_id,))
                        print(f"✅ תיקנתי test_results לתג {tag_id}")
                        tag_fixed = True
                except (json.JSONDecodeError, TypeError):
                    # אם יש שגיאה בפרסור, שנה לרשימה ריקה
                    c.execute("UPDATE process_tags SET test_results = '[]' WHERE tag_id = ?", (tag_id,))
                    print(f"✅ תיקנתי test_results לתג {tag_id}")
                    tag_fixed = True
            
            # תיקון item_statuses
            if item_statuses:
                try:
                    # נסה לפרסר את ה-JSON
                    parsed = json.loads(item_statuses)
                    if not isinstance(parsed, list):
                        # אם זה לא רשימה, שנה לרשימה ריקה
                        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE tag_id = ?", (tag_id,))
                        print(f"✅ תיקנתי item_statuses לתג {tag_id}")
                        tag_fixed = True
                except (json.JSONDecodeError, TypeError):
                    # אם יש שגיאה בפרסור, שנה לרשימה ריקה
                    c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE tag_id = ?", (tag_id,))
                    print(f"✅ תיקנתי item_statuses לתג {tag_id}")
                    tag_fixed = True
            
            if tag_fixed:
                fixed_count += 1
        
        # עדכן שדות NULL
        c.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL")
        c.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL")
        
        conn.commit()
        
        print(f"✅ תיקנתי {fixed_count} תגים")
        print("✅ תיקון JSON הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_json_fix(db_path):
    """בדוק שהתיקון עבד"""
    
    if not os.path.exists(db_path):
        return False
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק תג לדוגמה
        c.execute("SELECT tag_id, test_results, item_statuses FROM process_tags LIMIT 1")
        sample = c.fetchone()
        
        if sample:
            tag_id, test_results, item_statuses = sample
            print(f"\n📊 בדיקת תיקון JSON - תג {tag_id}:")
            
            # בדוק test_results
            try:
                if test_results:
                    parsed = json.loads(test_results)
                    print(f"  test_results: {type(parsed)} - {parsed}")
                else:
                    print(f"  test_results: NULL")
            except Exception as e:
                print(f"  test_results: שגיאה - {e}")
            
            # בדוק item_statuses
            try:
                if item_statuses:
                    parsed = json.loads(item_statuses)
                    print(f"  item_statuses: {type(parsed)} - {parsed}")
                else:
                    print(f"  item_statuses: NULL")
            except Exception as e:
                print(f"  item_statuses: שגיאה - {e}")
            
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקה: {e}")
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון בעיות JSON")
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
    
    if fix_json_issues(database_path):
        print("\n🔍 בודק את התיקון...")
        if verify_json_fix(database_path):
            print("\n🎉 תיקון JSON הושלם בהצלחה!")
            print("💡 עכשיו ההדפסה אמורה לעבוד בלי שגיאות")
        else:
            print("\n⚠️ התיקון הושלם אבל יש בעיות בבדיקה")
    else:
        print("\n❌ תיקון נכשל")

if __name__ == "__main__":
    main()
