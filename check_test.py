import sqlite3
import os
import shutil

# נתיב מוחלט
db_path = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\test.db"

if not os.path.exists(db_path):
    print(f"❌ קובץ לא נמצא: {db_path}")
    exit()

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

except Exception as e:
    print(f"❌ שגיאה: {e}")
finally:
    conn.close()