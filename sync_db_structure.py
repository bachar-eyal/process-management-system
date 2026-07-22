# -*- coding: utf-8 -*-
"""
סקריפט לשינוי מבנה ה-DB של eyal כך שיהיה זהה למבנה של צוות בדיקה
"""

import sqlite3
import os
from team_manager import TeamManager

def get_columns_info(db_path, table_name):
    """מחזיר את כל העמודות בטבלה עם כל המידע"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    cols = c.fetchall()
    conn.close()
    return cols

def reorder_table_structure(source_db_path, target_db_path, table_name):
    """משנה את סדר העמודות בטבלה כך שיתאים למבנה המקור"""
    
    print(f"\n{'='*80}")
    print(f"שינוי מבנה טבלת {table_name}")
    print(f"{'='*80}")
    
    source_conn = sqlite3.connect(source_db_path)
    target_conn = sqlite3.connect(target_db_path)
    
    source_c = source_conn.cursor()
    target_c = target_conn.cursor()
    
    # קבל את מבנה הטבלה משני ה-DBs
    source_cols = get_columns_info(source_db_path, table_name)
    target_cols = get_columns_info(target_db_path, table_name)
    
    print(f"\nמבנה מקור ({os.path.basename(source_db_path)}):")
    for col in source_cols:
        print(f"  [{col[0]}] {col[1]} ({col[2]})")
    
    print(f"\nמבנה יעד ({os.path.basename(target_db_path)}):")
    for col in target_cols:
        print(f"  [{col[0]}] {col[1]} ({col[2]})")
    
    # צור מיפוי של שמות עמודות
    source_col_names = [col[1] for col in source_cols]
    target_col_names = [col[1] for col in target_cols]
    
    # בדוק אם יש עמודות חסרות
    missing_in_target = set(source_col_names) - set(target_col_names)
    missing_in_source = set(target_col_names) - set(source_col_names)
    
    if missing_in_target:
        print(f"\n⚠️  עמודות חסרות ביעד: {', '.join(missing_in_target)}")
        # הוסף עמודות חסרות
        for col_name in missing_in_target:
            # מצא את סוג העמודה מהמקור
            source_col = next((c for c in source_cols if c[1] == col_name), None)
            if source_col:
                col_type = source_col[2]
                try:
                    target_c.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    target_conn.commit()
                    print(f"  ✅ נוספה עמודה: {col_name} ({col_type})")
                except sqlite3.OperationalError as e:
                    print(f"  ❌ שגיאה בהוספת עמודה {col_name}: {e}")
    
    if missing_in_source:
        print(f"\n⚠️  עמודות קיימות ביעד אבל לא במקור: {', '.join(missing_in_source)}")
        print(f"  (אלו יישמרו ב-DB)")
    
    # אם יש הבדל בסדר, נצטרך ליצור טבלה חדשה
    source_order = [col[1] for col in source_cols]
    target_order = [col[1] for col in target_cols]
    
    # הסר עמודות שלא קיימות במקור
    common_cols = [col for col in source_order if col in target_col_names]
    
    if source_order != common_cols:
        print(f"\n🔄 סדר העמודות שונה - יוצר טבלה חדשה...")
        
        # שלוף את כל הנתונים
        target_c.execute(f"SELECT * FROM {table_name}")
        rows = target_c.fetchall()
        print(f"  נמצאו {len(rows)} רשומות")
        
        # צור טבלה חדשה עם הסדר הנכון
        new_table_name = f"{table_name}_new"
        
        # בנה את ה-CREATE TABLE עם הסדר הנכון
        col_defs = []
        for col in source_cols:
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else ""
            default = f"DEFAULT {col[4]}" if col[4] else ""
            pk = "PRIMARY KEY" if col[5] else ""
            
            col_def = f"{col_name} {col_type}"
            if pk:
                col_def += f" {pk}"
            if not_null:
                col_def += f" {not_null}"
            if default:
                col_def += f" {default}"
            
            col_defs.append(col_def)
        
        create_sql = f"CREATE TABLE {new_table_name} ({', '.join(col_defs)})"
        print(f"\n  יצירת טבלה חדשה: {new_table_name}")
        target_c.execute(create_sql)
        
        # העתק את הנתונים
        if rows:
            # בנה רשימת עמודות משותפות
            common_cols_in_order = [col for col in source_order if col in target_col_names]
            cols_str = ', '.join(common_cols_in_order)
            
            # מצא את האינדקסים ביעד
            target_col_indices = {col[1]: idx for idx, col in enumerate(target_cols)}
            
            print(f"  העתקת {len(rows)} רשומות...")
            for row in rows:
                # בנה רשימת ערכים לפי הסדר החדש
                values = []
                for col_name in source_order:
                    if col_name in target_col_indices:
                        idx = target_col_indices[col_name]
                        if idx < len(row):
                            values.append(row[idx])
                        else:
                            values.append(None)
                    else:
                        values.append(None)
                
                placeholders = ', '.join(['?' for _ in source_order])
                insert_sql = f"INSERT INTO {new_table_name} ({', '.join(source_order)}) VALUES ({placeholders})"
                target_c.execute(insert_sql, tuple(values))
            
            target_conn.commit()
            print(f"  ✅ הועתקו {len(rows)} רשומות")
        
        # מחוק את הטבלה הישנה ושנה שם
        target_c.execute(f"DROP TABLE {table_name}")
        target_c.execute(f"ALTER TABLE {new_table_name} RENAME TO {table_name}")
        target_conn.commit()
        print(f"  ✅ הטבלה שונתה לסדר החדש")
    
    else:
        print(f"\n✅ סדר העמודות כבר תואם - אין צורך בשינוי")
    
    source_conn.close()
    target_conn.close()

def main():
    print("=" * 80)
    print("שינוי מבנה DB של eyal כך שיתאים למבנה של צוות בדיקה")
    print("=" * 80)
    
    team_manager = TeamManager()
    teams = team_manager.get_all_teams()
    
    # מצא את הצוותים
    source_team = None
    target_team = None
    
    for team in teams:
        if 'בדיקה' in team[1]:
            source_team = team
        if 'eyal' in team[1].lower():
            target_team = team
    
    if not source_team:
        print("❌ צוות 'צוות בדיקה' לא נמצא")
        return
    
    if not target_team:
        print("❌ צוות 'eyal' לא נמצא")
        return
    
    source_db = team_manager.get_team_db_path(source_team[0])
    target_db = team_manager.get_team_db_path(target_team[0])
    
    if not os.path.exists(source_db):
        print(f"❌ קובץ DB לא נמצא: {source_db}")
        return
    
    if not os.path.exists(target_db):
        print(f"❌ קובץ DB לא נמצא: {target_db}")
        return
    
    print(f"\nמקור: {source_team[1]} -> {source_db}")
    print(f"יעד: {target_team[1]} -> {target_db}")
    
    # הפעל אוטומטית (גיבוי ייווצר אוטומטית)
    print("\n⚠️  זה ישנה את מבנה ה-DB של eyal.")
    print("⚠️  גיבוי ייווצר אוטומטית לפני השינויים.")
    print("⚠️  ממשיך אוטומטית...")
    
    # שמור גיבוי
    backup_path = target_db + ".backup"
    print(f"\n📦 יצירת גיבוי: {backup_path}")
    import shutil
    shutil.copy2(target_db, backup_path)
    print("✅ גיבוי נוצר")
    
    # שנה את מבנה הטבלאות
    tables_to_sync = ['process_tags', 'spare_parts', 'approved_skus', 'approved_issues', 'team_members']
    
    for table in tables_to_sync:
        try:
            reorder_table_structure(source_db, target_db, table)
        except Exception as e:
            print(f"\n❌ שגיאה בטבלה {table}: {e}")
    
    print("\n" + "=" * 80)
    print("✅ סיום שינוי מבנה ה-DB")
    print("=" * 80)

if __name__ == '__main__':
    main()

