# -*- coding: utf-8 -*-
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

def reorder_table(source_db, target_db, table_name):
    print(f"\n{'='*60}")
    print(f"טבלה: {table_name}")
    print(f"{'='*60}")
    
    source_cols = get_columns_info(source_db, table_name)
    target_cols = get_columns_info(target_db, table_name)
    
    source_names = [c[1] for c in source_cols]
    target_names = [c[1] for c in target_cols]
    
    # הוסף עמודות חסרות
    missing = set(source_names) - set(target_names)
    if missing:
        print(f"מוסיף עמודות חסרות: {missing}")
        target_conn = sqlite3.connect(target_db)
        target_c = target_conn.cursor()
        for col_name in missing:
            source_col = next((c for c in source_cols if c[1] == col_name), None)
            if source_col:
                try:
                    target_c.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {source_col[2]}")
                    target_conn.commit()
                    print(f"  ✅ {col_name}")
                except Exception as e:
                    print(f"  ❌ {col_name}: {e}")
        target_conn.close()
    
    # אם הסדר שונה, צור טבלה חדשה
    common = [c for c in source_names if c in target_names]
    if source_names[:len(common)] != common:
        print(f"משנה סדר עמודות...")
        target_conn = sqlite3.connect(target_db)
        target_c = target_conn.cursor()
        
        # שלוף נתונים
        target_c.execute(f"SELECT * FROM {table_name}")
        rows = target_c.fetchall()
        old_target_cols = get_columns_info(target_db, table_name)
        
        # צור טבלה חדשה
        new_name = f"{table_name}_new"
        col_defs = []
        for col in source_cols:
            name, typ = col[1], col[2]
            pk = " PRIMARY KEY" if col[5] else ""
            not_null = " NOT NULL" if col[3] else ""
            default = f" DEFAULT {col[4]}" if col[4] else ""
            col_defs.append(f"{name} {typ}{pk}{not_null}{default}")
        
        target_c.execute(f"CREATE TABLE {new_name} ({', '.join(col_defs)})")
        
        # העתק נתונים
        if rows:
            target_indices = {c[1]: i for i, c in enumerate(old_target_cols)}
            for row in rows:
                values = []
                for col_name in source_names:
                    if col_name in target_indices:
                        idx = target_indices[col_name]
                        values.append(row[idx] if idx < len(row) else None)
                    else:
                        values.append(None)
                target_c.execute(f"INSERT INTO {new_name} ({', '.join(source_names)}) VALUES ({', '.join(['?' for _ in source_names])})", values)
        
        target_c.execute(f"DROP TABLE {table_name}")
        target_c.execute(f"ALTER TABLE {new_name} RENAME TO {table_name}")
        target_conn.commit()
        target_conn.close()
        print(f"✅ סדר שונה")
    else:
        print("✅ סדר תואם")

# מצא צוותים
tm = TeamManager()
teams = tm.get_all_teams()

source_team = next((t for t in teams if 'בדיקה' in t[1]), None)
target_team = next((t for t in teams if 'eyal' in t[1].lower()), None)

if not source_team or not target_team:
    print("❌ לא נמצאו צוותים")
    exit(1)

source_db = tm.get_team_db_path(source_team[0])
target_db = tm.get_team_db_path(target_team[0])

print(f"מקור: {source_team[1]}")
print(f"יעד: {target_team[1]}")

# גיבוי
backup = target_db + ".backup"
print(f"\nגיבוי: {backup}")
shutil.copy2(target_db, backup)

# שנה טבלאות
for table in ['process_tags', 'spare_parts', 'approved_skus', 'approved_issues', 'team_members']:
    try:
        reorder_table(source_db, target_db, table)
    except Exception as e:
        print(f"❌ שגיאה ב-{table}: {e}")

print("\n✅ סיום")

