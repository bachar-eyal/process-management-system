"""
סקריפט לבדיקת מבנה ה-database - מציג את כל הטבלאות והעמודות
"""

import sqlite3
import os
from team_manager import TeamManager

def get_all_columns(cursor, table_name):
    """מחזיר את כל העמודות בטבלה"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return columns

def check_database_structure(db_path):
    """בודק את המבנה של ה-database"""
    if not os.path.exists(db_path):
        print(f"❌ קובץ database לא נמצא: {db_path}")
        return
    
    print("=" * 80)
    print(f"מבנה Database: {db_path}")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # קבל את כל שמות הטבלאות
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    if not tables:
        print("❌ לא נמצאו טבלאות ב-database")
        conn.close()
        return
    
    print(f"\n📊 נמצאו {len(tables)} טבלאות:\n")
    
    for table_tuple in tables:
        table_name = table_tuple[0]
        print(f"\n{'=' * 80}")
        print(f"📋 טבלה: {table_name}")
        print(f"{'=' * 80}")
        
        columns = get_all_columns(cursor, table_name)
        
        if not columns:
            print("  ⚠️  אין עמודות בטבלה זו")
            continue
        
        print(f"\n  סה\"כ {len(columns)} עמודות:\n")
        
        # הדפס כותרת
        print(f"  {'מספר':<8} {'שם עמודה':<25} {'סוג':<15} {'NULL?':<8} {'ברירת מחדל':<20} {'PK':<5}")
        print(f"  {'-' * 80}")
        
        # הדפס כל עמודה
        for col in columns:
            cid, name, col_type, not_null, default_val, pk = col
            
            null_str = "לא" if not_null else "כן"
            pk_str = "✓" if pk else ""
            default_str = str(default_val) if default_val else ""
            
            print(f"  {cid:<8} {name:<25} {col_type:<15} {null_str:<8} {default_str:<20} {pk_str:<5}")
        
        # ספור רשומות
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n  📊 מספר רשומות: {count}")
        except Exception as e:
            print(f"\n  ⚠️  שגיאה בספירת רשומות: {e}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ סיום בדיקת מבנה ה-database")
    print("=" * 80)

def main():
    import sys
    
    print("=" * 80)
    print("בדיקת מבנה Database")
    print("=" * 80)
    
    team_manager = TeamManager()
    
    # בדוק אם הועבר נתיב או team_id כארגומנט
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit():
            # זה team_id
            team_id = int(arg)
            team = team_manager.get_team_by_id(team_id)
            if not team:
                print(f"❌ שגיאה: צוות עם ID {team_id} לא נמצא")
                return
            db_path = team_manager.get_team_db_path(team_id)
            if not db_path or not os.path.exists(db_path):
                print(f"❌ שגיאה: קובץ database של הצוות לא נמצא: {db_path}")
                return
            print(f"\n✅ נבחר צוות: {team[1]}")
            print(f"   נתיב database: {db_path}\n")
        else:
            # זה נתיב לקובץ
            db_path = arg
            if not os.path.exists(db_path):
                print(f"❌ שגיאה: קובץ database לא נמצא: {db_path}")
                return
            print(f"\n✅ נבחר database: {db_path}\n")
    else:
        # הצג את כל הצוותים הקיימים
        print("\n--- צוותים קיימים ---")
        teams = team_manager.get_all_teams()
        if not teams:
            print("לא נמצאו צוותים במערכת.")
            return
        
        for i, team in enumerate(teams, 1):
            team_id, team_name, created_date, is_active = team
            status = "פעיל" if is_active else "לא פעיל"
            print(f"{i}. {team_name} (ID: {team_id}) - {status} - נוצר: {created_date}")
        
        # בחר צוות
        print("\n--- בחירת צוות לבדיקה ---")
        team_id_input = input("הכנס את מספר ה-ID של הצוות (או Enter לבדיקת database.db): ").strip()
        
        if team_id_input:
            try:
                team_id = int(team_id_input)
                team = team_manager.get_team_by_id(team_id)
                if not team:
                    print(f"❌ שגיאה: צוות עם ID {team_id} לא נמצא")
                    return
                
                db_path = team_manager.get_team_db_path(team_id)
                if not db_path or not os.path.exists(db_path):
                    print(f"❌ שגיאה: קובץ database של הצוות לא נמצא: {db_path}")
                    return
                
                print(f"\n✅ נבחר צוות: {team[1]}")
                print(f"   נתיב database: {db_path}\n")
                
            except ValueError:
                print("❌ שגיאה: מספר ID לא תקין")
                return
        else:
            # בדוק את database.db הראשי
            db_path = 'database.db'
            if not os.path.exists(db_path):
                print(f"❌ שגיאה: קובץ database לא נמצא: {db_path}")
                return
            print(f"\n✅ נבחר database ראשי: {db_path}\n")
    
    # בדוק את המבנה
    check_database_structure(db_path)

if __name__ == '__main__':
    main()

