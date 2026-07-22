# -*- coding: utf-8 -*-
"""
סקריפט לתיקון מבנה ה-DB של eyal (לא test_eyal_new)
"""

import sqlite3
import os
import shutil
from team_manager import TeamManager

def get_columns_info(db_path, table_name):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    cols = c.fetchall()
    conn.close()
    return cols

def fix_table_structure(source_db, target_db, table_name):
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
        for col_name in missing_cols:
            source_col = next((c for c in source_cols if c[1] == col_name), None)
            if source_col:
                col_type = source_col[2]
                not_null = " NOT NULL" if source_col[3] else ""
                default_val = source_col[4]
                
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
                except Exception as e:
                    print(f"  ❌ שגיאה: {e}")
        
        target_conn.close()
        target_conn = sqlite3.connect(target_db)
        target_c = target_conn.cursor()
        target_cols = get_columns_info(target_db, table_name)
        target_names = [col[1] for col in target_cols]
    
    # 2. בדוק אם הסדר שונה
    if source_names != target_names:
        print(f"\nסדר עמודות שונה - משנה את הסדר...")
        
        target_c.execute(f"SELECT * FROM {table_name}")
        rows = target_c.fetchall()
        print(f"  נמצאו {len(rows)} רשומות")
        
        new_table_name = f"{table_name}_new"
        
        col_defs = []
        for col in source_cols:
            col_name, col_type = col[1], col[2]
            not_null = " NOT NULL" if col[3] else ""
            default_val = col[4]
            pk = " PRIMARY KEY" if col[5] else ""
            
            if default_val is not None:
                if isinstance(default_val, (int, float)):
                    default = f" DEFAULT {default_val}"
                elif isinstance(default_val, str) and default_val.upper() in ['CURRENT_TIMESTAMP']:
                    default = f" DEFAULT {default_val}"
                else:
                    default = f" DEFAULT '{default_val}'"
            else:
                default = ""
            
            col_defs.append(f"{col_name} {col_type}{pk}{not_null}{default}")
        
        target_c.execute(f"CREATE TABLE {new_table_name} ({', '.join(col_defs)})")
        
        if rows:
            target_col_map = {col[1]: idx for idx, col in enumerate(target_cols)}
            print(f"  מעתיק {len(rows)} רשומות...")
            copied = 0
            for row in rows:
                values = []
                for col_name in source_names:
                    if col_name in target_col_map:
                        idx = target_col_map[col_name]
                        values.append(row[idx] if idx < len(row) else None)
                    else:
                        values.append(None)
                
                target_c.execute(f"INSERT INTO {new_table_name} ({', '.join(source_names)}) VALUES ({', '.join(['?' for _ in source_names])})", values)
                copied += 1
            
            target_conn.commit()
            print(f"  ✅ הועתקו {copied} רשומות")
        
        target_c.execute(f"DROP TABLE {table_name}")
        target_c.execute(f"ALTER TABLE {new_table_name} RENAME TO {table_name}")
        target_conn.commit()
        print(f"  ✅ הטבלה שונתה לסדר הנכון")
    else:
        print(f"✅ סדר העמודות תואם")
    
    target_conn.close()

# מצא צוותים
tm = TeamManager()
teams = tm.get_all_teams()

print("צוותים קיימים:")
for t in teams:
    print(f"  {t[0]}: {t[1]}")

source_team = next((t for t in teams if 'בדיקה' in t[1]), None)
target_team = next((t for t in teams if 'eyal' in t[1].lower() and 'test' not in t[1].lower()), None)

if not source_team:
    print("❌ צוות בדיקה לא נמצא")
    exit(1)

if not target_team:
    print("❌ צוות eyal לא נמצא")
    exit(1)

source_db = tm.get_team_db_path(source_team[0])
target_db = tm.get_team_db_path(target_team[0])

print(f"\nמקור: {source_team[1]}")
print(f"  {source_db}")
print(f"\nיעד: {target_team[1]}")
print(f"  {target_db}")

# גיבוי
backup = target_db + ".backup_final"
print(f"\n📦 גיבוי: {backup}")
shutil.copy2(target_db, backup)

# תיקון
for table in ['process_tags', 'approved_issues']:
    try:
        fix_table_structure(source_db, target_db, table)
    except Exception as e:
        print(f"❌ שגיאה ב-{table}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*80)
print("✅ סיום")
print("="*80)

