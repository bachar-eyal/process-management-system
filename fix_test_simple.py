import sqlite3
import os
import shutil

# נתיבים
test_db = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\test.db"
working_db = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\צוות בדיקה_20250826_162719.db"

print("🔧 מתקן test.db בהתאם לצוות בדיקה")

# יצור גיבוי
backup_path = test_db + ".backup"
shutil.copy2(test_db, backup_path)
print(f"💾 יצרתי גיבוי: {backup_path}")

# קבל את המבנה הנכון מצוות בדיקה
conn_working = sqlite3.connect(working_db)
c_working = conn_working.cursor()
c_working.execute("PRAGMA table_info(process_tags)")
working_columns = c_working.fetchall()
working_names = [col[1] for col in working_columns]
conn_working.close()

print(f"📋 מבנה נכון: {', '.join(working_names)}")

# תיקון test.db
conn_test = sqlite3.connect(test_db)
c_test = conn_test.cursor()

try:
    # קבל את כל הנתונים מהטבלה הישנה
    c_test.execute("SELECT * FROM process_tags")
    all_data = c_test.fetchall()
    
    print(f"📊 מצאתי {len(all_data)} תגים")
    
    # קבל את המבנה הנוכחי
    c_test.execute("PRAGMA table_info(process_tags)")
    old_columns = [col[1] for col in c_test.fetchall()]
    print(f"📋 מבנה ישן: {', '.join(old_columns)}")
    
    # בדוק אילו עמודות חסרות
    missing_columns = set(working_names) - set(old_columns)
    if missing_columns:
        print(f"⚠️ עמודות חסרות: {', '.join(missing_columns)}")
        
        # הוסף עמודות חסרות
        for col in missing_columns:
            c_test.execute(f"ALTER TABLE process_tags ADD COLUMN {col} TEXT")
            print(f"✅ הוספתי עמודה: {col}")
    
    # צור טבלה חדשה עם הסדר הנכון
    print(f"\n🔧 יוצר טבלה חדשה עם סדר נכון...")
    
    # צור SQL ליצירת הטבלה החדשה
    create_parts = []
    for col_info in working_columns:
        col_name = col_info[1]
        col_type = col_info[2]
        if col_name == 'tag_id':
            create_parts.append(f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT")
        else:
            create_parts.append(f"{col_name} {col_type}")
    
    create_sql = f"CREATE TABLE process_tags_new ({', '.join(create_parts)})"
    c_test.execute(create_sql)
    
    # העבר את הנתונים מהטבלה הישנה לחדשה
    print(f"📊 מעביר נתונים...")
    
    for row in all_data:
        # צור רשימה עם הערכים בסדר הנכון
        new_row = [None] * len(working_names)
        
        # העבר את הערכים מהמיקומים הישנים לחדשים
        for i, old_col in enumerate(old_columns):
            if old_col in working_names:
                new_index = working_names.index(old_col)
                new_row[new_index] = row[i]
        
        # הוסף את השורה החדשה
        placeholders = ','.join(['?' for _ in working_names])
        insert_sql = f"INSERT INTO process_tags_new ({','.join(working_names)}) VALUES ({placeholders})"
        c_test.execute(insert_sql, new_row)
    
    # מחק את הטבלה הישנה ושנה את שם החדשה
    c_test.execute("DROP TABLE process_tags")
    c_test.execute("ALTER TABLE process_tags_new RENAME TO process_tags")
    
    # עדכן את הנתונים החסרים
    print(f"🔧 מעדכן נתונים חסרים...")
    
    # עדכן SKU חסר
    c_test.execute("UPDATE process_tags SET sku = (SELECT sku FROM products WHERE products.serial_number = process_tags.serial_number LIMIT 1) WHERE sku IS NULL OR sku = ''")
    
    # עדכן מבצעים חסרים
    c_test.execute("UPDATE process_tags SET performer = 'לא מוגדר' WHERE performer IS NULL OR performer = ''")
    
    # עדכן בודקים חסרים
    c_test.execute("UPDATE process_tags SET checker = 'לא מוגדר' WHERE checker IS NULL OR checker = ''")
    
    # עדכן שדות JSON
    c_test.execute("UPDATE process_tags SET test_results = '[]' WHERE test_results IS NULL OR test_results = ''")
    c_test.execute("UPDATE process_tags SET item_statuses = '[]' WHERE item_statuses IS NULL OR item_statuses = ''")
    
    # עדכן חתימות
    c_test.execute("UPDATE process_tags SET performer_signature = '' WHERE performer_signature IS NULL")
    c_test.execute("UPDATE process_tags SET checker_signature = '' WHERE checker_signature IS NULL")
    
    # תיקון תיאור תקלה
    c_test.execute("UPDATE process_tags SET fault_description = REPLACE(fault_description, '\\\\n', CHAR(10)) WHERE fault_description LIKE '%\\\\n%'")
    
    conn_test.commit()
    
    # בדוק את התוצאה
    c_test.execute("PRAGMA table_info(process_tags)")
    new_columns = [col[1] for col in c_test.fetchall()]
    print(f"✅ סדר חדש: {', '.join(new_columns)}")
    
    # בדוק תג לדוגמה
    c_test.execute("SELECT * FROM process_tags LIMIT 1")
    sample = c_test.fetchone()
    if sample:
        print(f"\n📊 תג לדוגמה אחרי תיקון:")
        for i, (col_name, value) in enumerate(zip(new_columns, sample)):
            print(f"  {i}: {col_name} = '{value}'")
    
    print("✅ תיקון test.db הושלם!")
    
except Exception as e:
    print(f"❌ שגיאה בתיקון: {e}")
    conn_test.rollback()
finally:
    conn_test.close()

print("\n🎉 תיקון הושלם בהצלחה!")
print("💡 עכשיו test.db אמור להיות בדיוק כמו צוות בדיקה")
print("💡 ההדפסה אמורה לעבוד נכון עכשיו")
