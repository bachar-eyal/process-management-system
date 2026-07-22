# -*- coding: utf-8 -*-
"""
סקריפט לתיקון מבנה ה-DB של eyal כך שיהיה זהה למבנה של צוות בדיקה
"""

import sqlite3
import os
import shutil
from team_manager import TeamManager

def get_columns_info(db_path, table_name):
    """מחזיר את כל העמודות בטבלה"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    cols = c.fetchall()
    conn.close()
    return cols

def fix_table_structure(source_db, target_db, table_name):
    """מתקן את מבנה הטבלה כך שיתאים למקור"""
    
    print(f"\n{'='*80}")
    print(f"תיקון טבלה: {table_name}")
    print(f"{'='*80}")
    
    source_cols = get_columns_info(source_db, table_name)
    target_cols = get_columns_info(target_db, table_name)
    
    source_names = [col[1] for col in source_cols]
    target_names = [col[1] for col in target_cols]
    
    target_conn = sqlite3.connect(target_db)
    target_c = target_conn.cursor()
    
    # 1. הוסף עמודות חסרות
    missing_cols = set(source_names) - set(target_names)
    if missing_cols:
        print(f"\nמוסיף עמודות חסרות: {missing_cols}")
        added_cols = []
        for col_name in missing_cols:
            source_col = next((c for c in source_cols if c[1] == col_name), None)
            if source_col:
                col_type = source_col[2]
                not_null = " NOT NULL" if source_col[3] else ""
                default_val = source_col[4]
                
                # טיפול ב-DEFAULT
                if default_val is not None:
                    if isinstance(default_val, (int, float)):
                        default = f" DEFAULT {default_val}"
                    elif isinstance(default_val, str) and default_val.upper() in ['CURRENT_TIMESTAMP']:
                        default = f" DEFAULT {default_val}"
                    else:
                        default = f" DEFAULT '{default_val}'"
                else:
                    default = ""
                
                try:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{not_null}{default}"
                    target_c.execute(sql)
                    target_conn.commit()
                    print(f"  ✅ נוספה עמודה: {col_name} ({col_type})")
                    added_cols.append(col_name)
                except Exception as e:
                    print(f"  ❌ שגיאה בהוספת {col_name}: {e}")
                    print(f"     SQL: {sql}")
        
        # סגור את החיבור ופתח מחדש כדי ש-SQLite יראה את השינויים
        target_conn.close()
        target_conn = sqlite3.connect(target_db)
        target_c = target_conn.cursor()
        
        # עדכן את target_cols אחרי הוספת עמודות ווודא שהן נוספו
        target_cols = get_columns_info(target_db, table_name)
        target_names_after = [col[1] for col in target_cols]
        
        # בדוק אם כל העמודות נוספו
        still_missing = set(source_names) - set(target_names_after)
        if still_missing:
            print(f"  ⚠️  עדיין חסרות עמודות: {still_missing}")
        else:
            print(f"  ✅ כל העמודות נוספו בהצלחה")
        
        target_names = target_names_after
        print(f"  עדכון: יש כעת {len(target_names)} עמודות ביעד (היו {len(target_names) - len(added_cols)})")
    
    # 2. אם הסדר שונה, צור טבלה חדשה בסדר הנכון
    # עדכן שוב את target_cols לפני בדיקת הסדר
    target_cols = get_columns_info(target_db, table_name)
    target_names = [col[1] for col in target_cols]
    
    # בדוק אם יש הבדל בסדר או בעמודות
    if source_names != target_names:
        print(f"\nסדר עמודות שונה - משנה את הסדר...")
        
        # שלוף את כל הנתונים
        target_c.execute(f"SELECT * FROM {table_name}")
        rows = target_c.fetchall()
        print(f"  נמצאו {len(rows)} רשומות להעתקה")
        
        # צור טבלה חדשה עם הסדר הנכון
        new_table_name = f"{table_name}_new"
        
        # בנה את ה-CREATE TABLE
        col_defs = []
        for col in source_cols:
            col_name = col[1]
            col_type = col[2]
            not_null = " NOT NULL" if col[3] else ""
            default = f" DEFAULT {col[4]}" if col[4] else ""
            pk = " PRIMARY KEY" if col[5] else ""
            
            col_def = f"{col_name} {col_type}{pk}{not_null}{default}"
            col_defs.append(col_def)
        
        create_sql = f"CREATE TABLE {new_table_name} ({', '.join(col_defs)})"
        print(f"  יוצר טבלה חדשה: {new_table_name}")
        target_c.execute(create_sql)
        
        # צור מיפוי של אינדקסים מהטבלה הישנה
        target_col_map = {col[1]: idx for idx, col in enumerate(target_cols)}
        
        # העתק את הנתונים
        if rows:
            print(f"  מעתיק {len(rows)} רשומות...")
            copied = 0
            for row in rows:
                # בנה רשימת ערכים לפי הסדר החדש
                values = []
                for col_name in source_names:
                    if col_name in target_col_map:
                        idx = target_col_map[col_name]
                        if idx < len(row):
                            values.append(row[idx])
                        else:
                            values.append(None)
                    else:
                        # עמודה חדשה - השתמש בברירת מחדל או None
                        values.append(None)
                
                placeholders = ', '.join(['?' for _ in source_names])
                insert_sql = f"INSERT INTO {new_table_name} ({', '.join(source_names)}) VALUES ({placeholders})"
                try:
                    target_c.execute(insert_sql, tuple(values))
                    copied += 1
                except Exception as e:
                    print(f"    ⚠️  שגיאה בהעתקת רשומה: {e}")
                    # נסה להדפיס את הנתונים לצורך דיבאג
                    if copied < 3:  # הדפס רק את הראשונות
                        print(f"      SQL: {insert_sql}")
                        print(f"      Values: {values[:5]}...")  # רק 5 ראשונות
            
            target_conn.commit()
            print(f"  ✅ הועתקו {copied} מתוך {len(rows)} רשומות")
        
        # מחוק את הטבלה הישנה ושנה שם
        print(f"  מחליף טבלות...")
        target_c.execute(f"DROP TABLE {table_name}")
        target_c.execute(f"ALTER TABLE {new_table_name} RENAME TO {table_name}")
        target_conn.commit()
        print(f"  ✅ הטבלה שונתה לסדר הנכון")
    else:
        print(f"✅ סדר העמודות כבר תואם")
    
    target_conn.close()

def main():
    print("=" * 80)
    print("תיקון מבנה DB כך שיתאים למבנה של צוות בדיקה")
    print("=" * 80)
    
    team_manager = TeamManager()
    teams = team_manager.get_all_teams()
    
    # מצא את הצוותים
    source_team = None
    target_team = None
    
    for team in teams:
        if 'בדיקה' in team[1]:
            source_team = team
        # חפש את test_eyal_new או test_for_eyal
        if 'test' in team[1].lower() and 'eyal' in team[1].lower():
            target_team = team
    
    if not source_team:
        print("❌ צוות 'צוות בדיקה' לא נמצא")
        return
    
    if not target_team:
        print("❌ צוות עם 'test' ו-'eyal' לא נמצא")
        print("צוותים קיימים:")
        for t in teams:
            print(f"  {t[0]}: {t[1]}")
        return
    
    source_db = team_manager.get_team_db_path(source_team[0])
    target_db = team_manager.get_team_db_path(target_team[0])
    
    if not os.path.exists(source_db):
        print(f"❌ קובץ DB לא נמצא: {source_db}")
        return
    
    if not os.path.exists(target_db):
        print(f"❌ קובץ DB לא נמצא: {target_db}")
        return
    
    print(f"\nמקור: {source_team[1]}")
    print(f"  {source_db}")
    print(f"\nיעד: {target_team[1]}")
    print(f"  {target_db}")
    
    # שמור גיבוי
    backup_path = target_db + ".backup2"
    print(f"\n📦 יצירת גיבוי: {backup_path}")
    shutil.copy2(target_db, backup_path)
    print("✅ גיבוי נוצר")
    
    print(f"\nמתקן את מבנה ה-DB של: {target_team[1]}")
    
    # תיקון הטבלאות
    tables_to_fix = ['process_tags', 'approved_issues']
    
    for table in tables_to_fix:
        try:
            fix_table_structure(source_db, target_db, table)
        except Exception as e:
            print(f"\n❌ שגיאה בתיקון טבלה {table}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ סיום תיקון מבנה ה-DB")
    print("=" * 80)
    print("\n💡 ניתן להריץ את check_sync.py כדי לוודא שהכל תקין")

if __name__ == '__main__':
    main()

