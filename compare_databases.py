import sqlite3
import os
import shutil

# נתיבים
test_db = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\test.db"
working_db = r"C:\Users\bacha\OneDrive\שולחן העבודה\project p\Process tag project version\teams_databases\צוות בדיקה_20250826_162719.db"

print("🔍 משווה בין databases:")
print(f"  test.db: {os.path.exists(test_db)}")
print(f"  צוות בדיקה: {os.path.exists(working_db)}")

if not os.path.exists(test_db) or not os.path.exists(working_db):
    print("❌ אחד מהקבצים לא קיים")
    exit()

# בדוק מבנה process_tags
print("\n📋 השוואת מבנה process_tags:")

# test.db
conn_test = sqlite3.connect(test_db)
c_test = conn_test.cursor()
c_test.execute("PRAGMA table_info(process_tags)")
test_columns = c_test.fetchall()
test_names = [col[1] for col in test_columns]

# working db
conn_working = sqlite3.connect(working_db)
c_working = conn_working.cursor()
c_working.execute("PRAGMA table_info(process_tags)")
working_columns = c_working.fetchall()
working_names = [col[1] for col in working_columns]

print(f"test.db עמודות ({len(test_names)}):")
for i, name in enumerate(test_names):
    print(f"  {i}: {name}")

print(f"\nצוות בדיקה עמודות ({len(working_names)}):")
for i, name in enumerate(working_names):
    print(f"  {i}: {name}")

# השווה שמות עמודות
print(f"\n🔍 השוואת שמות עמודות:")
print(f"  רק בtest.db: {set(test_names) - set(working_names)}")
print(f"  רק בצוות בדיקה: {set(working_names) - set(test_names)}")
print(f"  משותפות: {set(test_names) & set(working_names)}")

# השווה סדר עמודות
print(f"\n📊 השוואת סדר עמודות:")
common_columns = set(test_names) & set(working_names)

for col in common_columns:
    test_pos = test_names.index(col)
    working_pos = working_names.index(col)
    if test_pos != working_pos:
        print(f"  ⚠️ {col}: test={test_pos}, working={working_pos}")
    else:
        print(f"  ✅ {col}: מיקום זהה ({test_pos})")

conn_test.close()
conn_working.close()

print("\n✅ השוואה הושלמה")