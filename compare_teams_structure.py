"""
סקריפט להשוואת מבנה ה-database בין שני צוותים
"""

import sqlite3
import os
from team_manager import TeamManager

def get_all_columns(cursor, table_name):
    """מחזיר את כל העמודות בטבלה"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return columns

def get_table_structure(db_path, table_name):
    """מחזיר את מבנה הטבלה"""
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # בדוק אם הטבלה קיימת
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        return None
    
    columns = get_all_columns(cursor, table_name)
    conn.close()
    
    return columns

def compare_teams_structure(team1_name, team2_name):
    """השוואת מבנה בין שני צוותים"""
    team_manager = TeamManager()
    
    # מצא את הצוותים
    teams = team_manager.get_all_teams()
    team1 = None
    team2 = None
    
    for team in teams:
        if team1_name.lower() in team[1].lower():
            team1 = team
        if team2_name.lower() in team[1].lower():
            team2 = team
    
    if not team1:
        print(f"❌ צוות '{team1_name}' לא נמצא")
        return
    
    if not team2:
        print(f"❌ צוות '{team2_name}' לא נמצא")
        return
    
    print("=" * 80)
    print(f"השוואת מבנה בין: {team1[1]} ו-{team2[1]}")
    print("=" * 80)
    
    db_path1 = team_manager.get_team_db_path(team1[0])
    db_path2 = team_manager.get_team_db_path(team2[0])
    
    if not db_path1 or not os.path.exists(db_path1):
        print(f"❌ קובץ database לא נמצא: {db_path1}")
        return
    
    if not db_path2 or not os.path.exists(db_path2):
        print(f"❌ קובץ database לא נמצא: {db_path2}")
        return
    
    # השווה את טבלת process_tags
    print("\n" + "=" * 80)
    print("טבלת process_tags")
    print("=" * 80)
    
    cols1 = get_table_structure(db_path1, 'process_tags')
    cols2 = get_table_structure(db_path2, 'process_tags')
    
    if cols1 is None:
        print(f"❌ טבלת process_tags לא נמצאה ב-{team1[1]}")
        return
    
    if cols2 is None:
        print(f"❌ טבלת process_tags לא נמצאה ב-{team2[1]}")
        return
    
    # השווה עמודות
    col_names1 = {col[1]: col for col in cols1}
    col_names2 = {col[1]: col for col in cols2}
    
    all_col_names = set(col_names1.keys()) | set(col_names2.keys())
    
    print(f"\n{'עמודה':<30} {team1[1]:<30} {team2[1]:<30} סטטוס")
    print("-" * 100)
    
    differences = []
    for col_name in sorted(all_col_names):
        in_team1 = col_name in col_names1
        in_team2 = col_name in col_names2
        
        if in_team1 and in_team2:
            col1 = col_names1[col_name]
            col2 = col_names2[col_name]
            
            # השווה את הסוג
            type1 = col1[2]
            type2 = col2[2]
            
            if type1 != type2:
                status = f"⚠️  סוג שונה ({type1} vs {type2})"
                differences.append(f"עמודה '{col_name}': סוג שונה - {team1[1]}: {type1}, {team2[1]}: {type2}")
            else:
                status = "✅ זהה"
            
            team1_info = f"{type1}"
            team2_info = f"{type2}"
        elif in_team1:
            status = f"❌ חסר ב-{team2[1]}"
            team1_info = f"{col_names1[col_name][2]}"
            team2_info = "---"
            differences.append(f"עמודה '{col_name}': קיימת רק ב-{team1[1]}")
        else:
            status = f"❌ חסר ב-{team1[1]}"
            team1_info = "---"
            team2_info = f"{col_names2[col_name][2]}"
            differences.append(f"עמודה '{col_name}': קיימת רק ב-{team2[1]}")
        
        print(f"{col_name:<30} {team1_info:<30} {team2_info:<30} {status}")
    
    print("\n" + "=" * 80)
    if differences:
        print("סיכום הבדלים:")
        print("=" * 80)
        for diff in differences:
            print(f"  - {diff}")
    else:
        print("✅ אין הבדלים במבנה!")
        print("=" * 80)
    
    # השווה גם טבלאות אחרות
    print("\n" + "=" * 80)
    print("טבלאות אחרות")
    print("=" * 80)
    
    tables_to_check = ['spare_parts', 'approved_skus', 'approved_issues', 'team_members']
    
    for table_name in tables_to_check:
        print(f"\n--- {table_name} ---")
        cols1 = get_table_structure(db_path1, table_name)
        cols2 = get_table_structure(db_path2, table_name)
        
        if cols1 is None and cols2 is None:
            print("  לא קיימת בשניהם")
            continue
        
        if cols1 is None:
            print(f"  ❌ חסר ב-{team1[1]}")
            continue
        
        if cols2 is None:
            print(f"  ❌ חסר ב-{team2[1]}")
            continue
        
        col_names1 = {col[1] for col in cols1}
        col_names2 = {col[1] for col in cols2}
        
        only_in_1 = col_names1 - col_names2
        only_in_2 = col_names2 - col_names1
        
        if only_in_1:
            print(f"  ⚠️  עמודות רק ב-{team1[1]}: {', '.join(only_in_1)}")
        if only_in_2:
            print(f"  ⚠️  עמודות רק ב-{team2[1]}: {', '.join(only_in_2)}")
        if not only_in_1 and not only_in_2:
            print(f"  ✅ זהה ({len(col_names1)} עמודות)")

if __name__ == '__main__':
    compare_teams_structure('צוות בדיקה', 'eyal')

