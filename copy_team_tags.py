"""
סקריפט להעתקת כל התגים מצוות קיים לצוות חדש
הסקריפט יוצר צוות חדש ומעתיק את כל התגים (פתוחים וסגורים) תוך שמירה על התאריכים המקוריים
"""

import sqlite3
import os
from datetime import datetime
from team_manager import TeamManager

def get_input(prompt, required=True, default=None):
    """קבלת קלט מהמשתמש"""
    while True:
        if default:
            val = input(f"{prompt} [{default}]: ").strip()
            if not val:
                return default
        else:
            val = input(f"{prompt}: ").strip()
        
        if not val and required:
            print("שדה חובה! אנא הכנס ערך.")
            continue
        else:
            return val

def get_all_columns(cursor, table_name):
    """מחזיר את כל העמודות בטבלה"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [col[1] for col in columns]

def copy_process_tags(source_db_path, target_db_path):
    """מעתיק את כל התגים מה-database המקור ל-database היעד"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    # קבל את כל העמודות בשני ה-databases
    source_columns = get_all_columns(source_cursor, 'process_tags')
    target_columns = get_all_columns(target_cursor, 'process_tags')
    
    # מצא עמודות משותפות
    common_columns = [col for col in source_columns if col in target_columns]
    # הסר את tag_id כי זה AUTOINCREMENT
    if 'tag_id' in common_columns:
        common_columns.remove('tag_id')
    
    print(f"\nעמודות משותפות: {', '.join(common_columns)}")
    
    # שמור מיפוי של tag_id ישן לחדש
    tag_id_mapping = {}
    
    # קרא את כל ה-tag_ids המקוריים עם הנתונים
    columns_str = ', '.join(common_columns)
    source_cursor.execute(f"SELECT tag_id, {columns_str} FROM process_tags ORDER BY tag_id")
    all_tags_with_ids = source_cursor.fetchall()
    
    print(f"\nנמצאו {len(all_tags_with_ids)} תגים להעתקה...")
    
    # העתק כל תג
    placeholders = ', '.join(['?' for _ in common_columns])
    insert_query = f"INSERT INTO process_tags ({columns_str}) VALUES ({placeholders})"
    
    copied_count = 0
    for tag_row in all_tags_with_ids:
        try:
            old_tag_id = tag_row[0]
            tag_data = tag_row[1:]  # שאר הנתונים בלי tag_id
            target_cursor.execute(insert_query, tag_data)
            new_tag_id = target_cursor.lastrowid
            tag_id_mapping[old_tag_id] = new_tag_id
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת תג: {e}")
            print(f"נתונים: {tag_row}")
    
    target_conn.commit()
    
    # סטטיסטיקות
    target_cursor.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 0")
    open_tags = target_cursor.fetchone()[0]
    
    target_cursor.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 1")
    closed_tags = target_cursor.fetchone()[0]
    
    source_conn.close()
    target_conn.close()
    
    print(f"\n✅ הועתקו {copied_count} תגים בהצלחה!")
    print(f"   - תגים פתוחים: {open_tags}")
    print(f"   - תגים סגורים: {closed_tags}")
    
    return copied_count, tag_id_mapping

def copy_products(source_db_path, target_db_path):
    """מעתיק את כל המוצרים מה-database המקור ל-database היעד"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    # קרא את כל המוצרים
    source_cursor.execute("SELECT serial_number, sku, date_added FROM products")
    all_products = source_cursor.fetchall()
    
    if len(all_products) == 0:
        print("\nלא נמצאו מוצרים להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0
    
    print(f"\nנמצאו {len(all_products)} מוצרים להעתקה...")
    
    # העתק כל מוצר
    copied_count = 0
    for product in all_products:
        try:
            target_cursor.execute(
                "INSERT OR REPLACE INTO products (serial_number, sku, date_added) VALUES (?, ?, ?)",
                product
            )
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת מוצר: {e}")
    
    target_conn.commit()
    
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} מוצרים בהצלחה!")
    return copied_count

def copy_approved_skus(source_db_path, target_db_path):
    """מעתיק את כל המק"טים המאושרים"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    # בדוק אילו עמודות קיימות
    source_columns = get_all_columns(source_cursor, 'approved_skus')
    target_columns = get_all_columns(target_cursor, 'approved_skus')
    common_columns = [col for col in source_columns if col in target_columns]
    
    if 'sku_id' in common_columns:
        common_columns.remove('sku_id')
    
    if not common_columns:
        print("\n⚠️  אין עמודות משותפות ב-approved_skus")
        source_conn.close()
        target_conn.close()
        return 0
    
    columns_str = ', '.join(common_columns)
    source_cursor.execute(f"SELECT {columns_str} FROM approved_skus")
    all_skus = source_cursor.fetchall()
    
    if len(all_skus) == 0:
        print("\nלא נמצאו מק\"טים מאושרים להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0
    
    print(f"\nנמצאו {len(all_skus)} מק\"טים מאושרים להעתקה...")
    
    placeholders = ', '.join(['?' for _ in common_columns])
    insert_query = f"INSERT OR REPLACE INTO approved_skus ({columns_str}) VALUES ({placeholders})"
    
    copied_count = 0
    for sku in all_skus:
        try:
            target_cursor.execute(insert_query, sku)
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת מק\"ט: {e}")
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} מק\"טים מאושרים בהצלחה!")
    return copied_count

def copy_approved_issues(source_db_path, target_db_path):
    """מעתיק את כל התקלות המאושרות"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    source_columns = get_all_columns(source_cursor, 'approved_issues')
    target_columns = get_all_columns(target_cursor, 'approved_issues')
    common_columns = [col for col in source_columns if col in target_columns]
    
    if 'issue_id' in common_columns:
        common_columns.remove('issue_id')
    
    if not common_columns:
        print("\n⚠️  אין עמודות משותפות ב-approved_issues")
        source_conn.close()
        target_conn.close()
        return 0
    
    columns_str = ', '.join(common_columns)
    source_cursor.execute(f"SELECT {columns_str} FROM approved_issues")
    all_issues = source_cursor.fetchall()
    
    if len(all_issues) == 0:
        print("\nלא נמצאו תקלות מאושרות להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0
    
    print(f"\nנמצאו {len(all_issues)} תקלות מאושרות להעתקה...")
    
    placeholders = ', '.join(['?' for _ in common_columns])
    insert_query = f"INSERT OR REPLACE INTO approved_issues ({columns_str}) VALUES ({placeholders})"
    
    copied_count = 0
    for issue in all_issues:
        try:
            target_cursor.execute(insert_query, issue)
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת תקלה: {e}")
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} תקלות מאושרות בהצלחה!")
    return copied_count

def copy_spare_parts(source_db_path, target_db_path):
    """מעתיק את כל חלקי החילוף"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    source_columns = get_all_columns(source_cursor, 'spare_parts')
    target_columns = get_all_columns(target_cursor, 'spare_parts')
    common_columns = [col for col in source_columns if col in target_columns]
    
    if 'part_id' in common_columns:
        common_columns.remove('part_id')
    
    if not common_columns:
        print("\n⚠️  אין עמודות משותפות ב-spare_parts")
        source_conn.close()
        target_conn.close()
        return 0, {}
    
    # שמור מיפוי של part_id ישן לחדש
    part_id_mapping = {}
    
    # קרא את כל ה-part_ids המקוריים עם הנתונים
    columns_str = ', '.join(common_columns)
    source_cursor.execute(f"SELECT part_id, {columns_str} FROM spare_parts ORDER BY part_id")
    all_parts_with_ids = source_cursor.fetchall()
    
    if len(all_parts_with_ids) == 0:
        print("\nלא נמצאו חלקי חילוף להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0, {}
    
    print(f"\nנמצאו {len(all_parts_with_ids)} חלקי חילוף להעתקה...")
    
    placeholders = ', '.join(['?' for _ in common_columns])
    insert_query = f"INSERT OR REPLACE INTO spare_parts ({columns_str}) VALUES ({placeholders})"
    
    copied_count = 0
    for part_row in all_parts_with_ids:
        try:
            old_part_id = part_row[0]
            part_data = part_row[1:]  # שאר הנתונים בלי part_id
            target_cursor.execute(insert_query, part_data)
            new_part_id = target_cursor.lastrowid
            part_id_mapping[old_part_id] = new_part_id
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת חלק חילוף: {e}")
            print(f"נתונים: {part_row}")
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} חלקי חילוף בהצלחה!")
    return copied_count, part_id_mapping

def copy_spare_parts_usage(source_db_path, target_db_path, tag_id_mapping, part_id_mapping):
    """מעתיק את צריכת חלקי החילוף (דרוש מיפוי של tag_id ו-part_id)"""
    if not tag_id_mapping or not part_id_mapping:
        print("\n⚠️  לא ניתן להעתיק צריכת חלקי חילוף ללא מיפוי תגים וחלקים")
        return 0
    
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    source_columns = get_all_columns(source_cursor, 'spare_parts_usage')
    target_columns = get_all_columns(target_cursor, 'spare_parts_usage')
    common_columns = [col for col in source_columns if col in target_columns]
    
    if 'usage_id' in common_columns:
        common_columns.remove('usage_id')
    
    if not common_columns:
        print("\n⚠️  אין עמודות משותפות ב-spare_parts_usage")
        source_conn.close()
        target_conn.close()
        return 0
    
    # בדוק אם יש רשומות
    source_cursor.execute("SELECT COUNT(*) FROM spare_parts_usage")
    usage_count = source_cursor.fetchone()[0]
    
    if usage_count == 0:
        print("\nלא נמצאה צריכת חלקי חילוף להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0
    
    print(f"\nנמצאו {usage_count} רשומות צריכת חלקי חילוף להעתקה...")
    
    copied_count = 0
    skipped_count = 0
    
    # קרא את כל הרשומות עם שמות העמודות
    source_cursor.execute("SELECT * FROM spare_parts_usage")
    all_usage = source_cursor.fetchall()
    
    # מצא את המיקומים של tag_id ו-part_id
    tag_id_index = source_columns.index('tag_id') if 'tag_id' in source_columns else None
    part_id_index = source_columns.index('part_id') if 'part_id' in source_columns else None
    
    for usage in all_usage:
        try:
            # קרא את ה-tag_id ו-part_id הישנים
            old_tag_id = usage[tag_id_index] if tag_id_index is not None else None
            old_part_id = usage[part_id_index] if part_id_index is not None else None
            
            if old_tag_id is None or old_part_id is None:
                skipped_count += 1
                continue
                
            if old_tag_id not in tag_id_mapping or old_part_id not in part_id_mapping:
                skipped_count += 1
                continue
            
            new_tag_id = tag_id_mapping[old_tag_id]
            new_part_id = part_id_mapping[old_part_id]
            
            # בנה רשימת ערכים עם tag_id ו-part_id החדשים
            usage_values = []
            for col in common_columns:
                col_index = source_columns.index(col) if col in source_columns else None
                if col == 'tag_id':
                    usage_values.append(new_tag_id)
                elif col == 'part_id':
                    usage_values.append(new_part_id)
                elif col_index is not None:
                    usage_values.append(usage[col_index])
                else:
                    usage_values.append(None)
            
            columns_str = ', '.join(common_columns)
            placeholders = ', '.join(['?' for _ in common_columns])
            insert_query = f"INSERT INTO spare_parts_usage ({columns_str}) VALUES ({placeholders})"
            
            target_cursor.execute(insert_query, tuple(usage_values))
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת צריכת חלק חילוף: {e}")
            skipped_count += 1
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} רשומות צריכת חלקי חילוף בהצלחה!")
    if skipped_count > 0:
        print(f"⚠️  דולגו {skipped_count} רשומות (לא נמצאו תגים או חלקים מותאמים)")
    return copied_count

def copy_team_members(source_db_path, target_db_path):
    """מעתיק את כל חברי הצוות"""
    source_conn = sqlite3.connect(source_db_path)
    source_cursor = source_conn.cursor()
    
    target_conn = sqlite3.connect(target_db_path)
    target_cursor = target_conn.cursor()
    
    source_columns = get_all_columns(source_cursor, 'team_members')
    target_columns = get_all_columns(target_cursor, 'team_members')
    common_columns = [col for col in source_columns if col in target_columns]
    
    if 'member_id' in common_columns:
        common_columns.remove('member_id')
    
    if not common_columns:
        print("\n⚠️  אין עמודות משותפות ב-team_members")
        source_conn.close()
        target_conn.close()
        return 0
    
    columns_str = ', '.join(common_columns)
    source_cursor.execute(f"SELECT {columns_str} FROM team_members")
    all_members = source_cursor.fetchall()
    
    if len(all_members) == 0:
        print("\nלא נמצאו חברי צוות להעתקה.")
        source_conn.close()
        target_conn.close()
        return 0
    
    print(f"\nנמצאו {len(all_members)} חברי צוות להעתקה...")
    
    placeholders = ', '.join(['?' for _ in common_columns])
    insert_query = f"INSERT OR REPLACE INTO team_members ({columns_str}) VALUES ({placeholders})"
    
    copied_count = 0
    for member in all_members:
        try:
            target_cursor.execute(insert_query, member)
            copied_count += 1
        except Exception as e:
            print(f"שגיאה בהעתקת חבר צוות: {e}")
    
    target_conn.commit()
    source_conn.close()
    target_conn.close()
    
    print(f"✅ הועתקו {copied_count} חברי צוות בהצלחה!")
    return copied_count

def main():
    print("=" * 60)
    print("העתקת תגים מצוות קיים לצוות חדש")
    print("=" * 60)
    
    team_manager = TeamManager()
    
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
    
    # בחר צוות מקור
    print("\n--- בחירת צוות מקור ---")
    source_team_id = get_input("הכנס את מספר ה-ID של הצוות המקור", required=True)
    try:
        source_team_id = int(source_team_id)
    except ValueError:
        print("❌ שגיאה: מספר ID לא תקין")
        return
    
    source_team = team_manager.get_team_by_id(source_team_id)
    if not source_team:
        print(f"❌ שגיאה: צוות עם ID {source_team_id} לא נמצא")
        return
    
    source_db_path = team_manager.get_team_db_path(source_team_id)
    if not source_db_path or not os.path.exists(source_db_path):
        print(f"❌ שגיאה: קובץ database של הצוות לא נמצא: {source_db_path}")
        return
    
    print(f"✅ צוות מקור: {source_team[1]}")
    print(f"   נתיב database: {source_db_path}")
    
    # בדוק כמה תגים יש
    conn = sqlite3.connect(source_db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM process_tags")
    total_tags = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 0")
    open_tags = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 1")
    closed_tags = c.fetchone()[0]
    conn.close()
    
    print(f"\n📊 סטטיסטיקות בצוות המקור:")
    print(f"   - סה\"כ תגים: {total_tags}")
    print(f"   - תגים פתוחים: {open_tags}")
    print(f"   - תגים סגורים: {closed_tags}")
    
    # פרטי צוות חדש
    print("\n--- יצירת צוות חדש ---")
    new_team_name = get_input("שם הצוות החדש", required=True)
    
    # בדוק אם שם הצוות כבר קיים
    if team_manager.team_exists(new_team_name):
        print(f"❌ שגיאה: צוות בשם '{new_team_name}' כבר קיים")
        return
    
    admin_username = get_input("שם משתמש Admin", required=True)
    admin_password = get_input("סיסמת Admin", required=True)
    creation_code = get_input("קוד יצירת צוות", required=True)
    
    # בדוק את קוד היצירה
    code_validation = team_manager.validate_team_creation_code(creation_code)
    if not code_validation['valid']:
        print(f"❌ שגיאה: {code_validation['message']}")
        return
    
    # אישור
    print("\n--- אישור ---")
    print(f"האם אתה בטוח שברצונך:")
    print(f"1. ליצור צוות חדש: '{new_team_name}'")
    print(f"2. להעתיק {total_tags} תגים מצוות '{source_team[1]}' לצוות החדש")
    confirm = get_input("הקלד 'כן' לאישור או 'לא' לביטול", required=True)
    
    if confirm.lower() not in ['כן', 'yes', 'y', 'כן']:
        print("הפעולה בוטלה.")
        return
    
    # צור צוות חדש
    print("\n--- יצירת צוות חדש... ---")
    result = team_manager.create_team(new_team_name, admin_username, admin_password, creation_code)
    
    if not result['success']:
        print(f"❌ שגיאה ביצירת הצוות: {result['message']}")
        return
    
    new_team_id = result['team_id']
    new_db_path = team_manager.get_team_db_path(new_team_id)
    
    print(f"✅ צוות '{new_team_name}' נוצר בהצלחה!")
    print(f"   Team ID: {new_team_id}")
    print(f"   נתיב database: {new_db_path}")
    
    # העתק מוצרים
    print("\n--- העתקת מוצרים... ---")
    copy_products(source_db_path, new_db_path)
    
    # העתק מק"טים מאושרים
    print("\n--- העתקת מק\"טים מאושרים... ---")
    copy_approved_skus(source_db_path, new_db_path)
    
    # העתק תקלות מאושרות
    print("\n--- העתקת תקלות מאושרות... ---")
    copy_approved_issues(source_db_path, new_db_path)
    
    # העתק חברי צוות
    print("\n--- העתקת חברי צוות... ---")
    copy_team_members(source_db_path, new_db_path)
    
    # העתק חלקי חילוף
    print("\n--- העתקת חלקי חילוף... ---")
    part_id_mapping = {}
    try:
        _, part_id_mapping = copy_spare_parts(source_db_path, new_db_path)
    except:
        part_id_mapping = {}
    
    # העתק תגים (חייב להיות אחרי חלקי החילוף כדי לקבל מיפוי tag_id)
    print("\n--- העתקת תגים... ---")
    tag_id_mapping = {}
    try:
        _, tag_id_mapping = copy_process_tags(source_db_path, new_db_path)
    except:
        tag_id_mapping = {}
    
    # העתק צריכת חלקי חילוף (צריך מיפוי של tag_id ו-part_id)
    if tag_id_mapping and part_id_mapping:
        print("\n--- העתקת צריכת חלקי חילוף... ---")
        copy_spare_parts_usage(source_db_path, new_db_path, tag_id_mapping, part_id_mapping)
    
    print("\n" + "=" * 60)
    print("✅ הפעולה הושלמה בהצלחה!")
    print(f"צוות חדש '{new_team_name}' נוצר עם כל הנתונים מהצוות '{source_team[1]}':")
    print("   - תגים (פתוחים וסגורים)")
    print("   - מוצרים")
    print("   - מק\"טים מאושרים")
    print("   - תקלות מאושרות")
    print("   - חלקי חילוף")
    print("   - חברי צוות")
    print("=" * 60)

if __name__ == '__main__':
    main()

