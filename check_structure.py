import sqlite3
import os

# נתיב מוחלט
db_path = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\test.db"

print(f"🔍 בודק: {db_path}")
print(f"קובץ קיים: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
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
        
        conn.close()
        print("✅ בדיקה הושלמה")
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
else:
    print("❌ קובץ לא נמצא")
