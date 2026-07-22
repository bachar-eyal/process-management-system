import sqlite3
import os

db1 = "teams_databases/צוות בדיקה_20250826_162719.db"
db2 = "teams_databases/eyal_20251105_104247.db"

def get_columns(db_path, table):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    cols = {col[1]: col[2] for col in c.fetchall()}
    conn.close()
    return cols

print("=" * 80)
print("השוואת מבנה process_tags בין שני הצוותים")
print("=" * 80)

cols1 = get_columns(db1, 'process_tags')
cols2 = get_columns(db2, 'process_tags')

all_cols = set(cols1.keys()) | set(cols2.keys())

print(f"\n{'עמודה':<35} {'צוות בדיקה':<25} {'eyal':<25} סטטוס")
print("-" * 100)

differences = []
for col in sorted(all_cols):
    in1 = col in cols1
    in2 = col in cols2
    
    if in1 and in2:
        if cols1[col] != cols2[col]:
            status = f"⚠️  סוג שונה"
            differences.append(f"{col}: {cols1[col]} vs {cols2[col]}")
        else:
            status = "✅"
        t1_info = cols1[col]
        t2_info = cols2[col]
    elif in1:
        status = f"❌ חסר ב-eyal"
        t1_info = cols1[col]
        t2_info = "---"
        differences.append(f"{col}: קיים רק ב-צוות בדיקה")
    else:
        status = f"❌ חסר ב-צוות בדיקה"
        t1_info = "---"
        t2_info = cols2[col]
        differences.append(f"{col}: קיים רק ב-eyal")
    
    print(f"{col:<35} {t1_info:<25} {t2_info:<25} {status}")

print("\n" + "=" * 80)
if differences:
    print("סיכום הבדלים:")
    for d in differences:
        print(f"  - {d}")
else:
    print("✅ אין הבדלים במבנה!")
print("=" * 80)

