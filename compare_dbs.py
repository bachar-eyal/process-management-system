# -*- coding: utf-8 -*-
import sqlite3
import os

# נתיבים
db1_path = os.path.join('teams_databases', 'צוות בדיקה_20250826_162719.db')
db2_path = os.path.join('teams_databases', 'eyal_20251105_104247.db')

def get_columns(db_path, table):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        cols = {col[1]: (col[2], col[0]) for col in c.fetchall()}
        conn.close()
        return cols
    except Exception as e:
        print(f"שגיאה בקריאת {db_path}: {e}")
        return {}

print("=" * 100)
print("השוואת מבנה process_tags בין 'צוות בדיקה' ו-'eyal'")
print("=" * 100)

cols1 = get_columns(db1_path, 'process_tags')
cols2 = get_columns(db2_path, 'process_tags')

all_cols = sorted(set(cols1.keys()) | set(cols2.keys()))

print(f"\n{'עמודה':<35} {'צוות בדיקה':<30} {'eyal':<30} {'סטטוס':<20}")
print("-" * 115)

differences = []
for col in all_cols:
    in1 = col in cols1
    in2 = col in cols2
    
    if in1 and in2:
        type1, idx1 = cols1[col]
        type2, idx2 = cols2[col]
        if type1 != type2 or idx1 != idx2:
            status = f"⚠️  שונה"
            differences.append(f"{col}: סוג {type1} (idx {idx1}) vs {type2} (idx {idx2})")
        else:
            status = "✅ זהה"
        t1_info = f"{type1} (idx {idx1})"
        t2_info = f"{type2} (idx {idx2})"
    elif in1:
        type1, idx1 = cols1[col]
        status = f"❌ חסר ב-eyal"
        t1_info = f"{type1} (idx {idx1})"
        t2_info = "---"
        differences.append(f"{col}: קיים רק ב-צוות בדיקה")
    else:
        type2, idx2 = cols2[col]
        status = f"❌ חסר ב-צוות בדיקה"
        t1_info = "---"
        t2_info = f"{type2} (idx {idx2})"
        differences.append(f"{col}: קיים רק ב-eyal")
    
    print(f"{col:<35} {t1_info:<30} {t2_info:<30} {status:<20}")

print("\n" + "=" * 100)
if differences:
    print(f"סיכום: נמצאו {len(differences)} הבדלים:")
    print("=" * 100)
    for d in differences:
        print(f"  • {d}")
else:
    print("✅ אין הבדלים במבנה - המבנה זהה!")
    print("=" * 100)

# השווה גם מספר עמודות
print(f"\nמספר עמודות: צוות בדיקה = {len(cols1)}, eyal = {len(cols2)}")

