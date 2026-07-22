#!/usr/bin/env python3
"""
סקריפט ספציפי לתיקון בעיית הבודק והמבצע ב-database ישן
"""

import sqlite3
import os
import json
import re

def fix_performer_checker_data(db_path):
    """תקן את נתוני הבודק והמבצע ב-database"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🔧 מתקן נתוני בודק ומבצע ב: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק את המבנה הנוכחי
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        print(f"📋 עמודות: {', '.join(columns)}")
        
        # בדוק את המבנה של team_members
        c.execute("PRAGMA table_info(team_members)")
        team_columns = [col[1] for col in c.fetchall()]
        print(f"👥 עמודות team_members: {', '.join(team_columns)}")
        
        # בדוק כמה חברי צוות יש
        c.execute("SELECT COUNT(*) FROM team_members")
        team_count = c.fetchone()[0]
        print(f"👥 מספר חברי צוות: {team_count}")
        
        if team_count == 0:
            print("⚠️ אין חברי צוות! צריך להוסיף חברי צוות קודם")
            return False
        
        # הצג את חברי הצוות
        c.execute("SELECT member_id, name, id_number, role FROM team_members")
        team_members = c.fetchall()
        print(f"\n👥 חברי צוות:")
        for member in team_members:
            print(f"  {member[0]}: {member[1]} ({member[2]}) - {member[3]}")
        
        # בדוק את התגים הנוכחיים
        print(f"\n🏷️ בדיקת תגים:")
        c.execute("SELECT tag_id, performer, checker FROM process_tags LIMIT 5")
        tags = c.fetchall()
        
        for tag_id, performer, checker in tags:
            print(f"  תג {tag_id}:")
            print(f"    מבצע: '{performer}'")
            print(f"    בודק: '{checker}'")
        
        # תיקון 1: עדכן תגים עם מבצע לא תקין
        print(f"\n🔧 מתקן מבצעים...")
        c.execute("SELECT tag_id, performer FROM process_tags WHERE performer IS NULL OR performer = '' OR performer = 'לא מוגדר'")
        tags_without_performer = c.fetchall()
        
        for tag_id, performer in tags_without_performer:
            # בחר מבצע אקראי מהצוות
            c.execute("SELECT name, id_number FROM team_members WHERE role = 'מבצע' OR role = 'performer' LIMIT 1")
            performer_data = c.fetchone()
            
            if performer_data:
                name, id_number = performer_data
                new_performer = f"{name} ({id_number})"
                c.execute("UPDATE process_tags SET performer = ? WHERE tag_id = ?", (new_performer, tag_id))
                print(f"✅ עדכנתי תג {tag_id} עם מבצע: {new_performer}")
            else:
                # אם אין מבצעים, בחר כל חבר צוות
                c.execute("SELECT name, id_number FROM team_members LIMIT 1")
                performer_data = c.fetchone()
                if performer_data:
                    name, id_number = performer_data
                    new_performer = f"{name} ({id_number})"
                    c.execute("UPDATE process_tags SET performer = ? WHERE tag_id = ?", (new_performer, tag_id))
                    print(f"✅ עדכנתי תג {tag_id} עם מבצע: {new_performer}")
        
        # תיקון 2: עדכן תגים עם בודק לא תקין
        print(f"\n🔧 מתקן בודקים...")
        c.execute("SELECT tag_id, checker FROM process_tags WHERE checker IS NULL OR checker = '' OR checker = 'לא מוגדר'")
        tags_without_checker = c.fetchall()
        
        for tag_id, checker in tags_without_checker:
            # בחר בודק מהצוות
            c.execute("SELECT name, id_number FROM team_members WHERE role = 'בודק' OR role = 'checker' LIMIT 1")
            checker_data = c.fetchone()
            
            if checker_data:
                name, id_number = checker_data
                new_checker = f"{name} ({id_number})"
                c.execute("UPDATE process_tags SET checker = ? WHERE tag_id = ?", (new_checker, tag_id))
                print(f"✅ עדכנתי תג {tag_id} עם בודק: {new_checker}")
            else:
                # אם אין בודקים, בחר חבר צוות אחר
                c.execute("SELECT name, id_number FROM team_members WHERE role != 'מבצע' AND role != 'performer' LIMIT 1")
                checker_data = c.fetchone()
                if checker_data:
                    name, id_number = checker_data
                    new_checker = f"{name} ({id_number})"
                    c.execute("UPDATE process_tags SET checker = ? WHERE tag_id = ?", (new_checker, tag_id))
                    print(f"✅ עדכנתי תג {tag_id} עם בודק: {new_checker}")
        
        # תיקון 3: עדכן חתימות
        print(f"\n🔧 מתקן חתימות...")
        
        # עדכן חתימות מבצע
        c.execute("SELECT tag_id, performer FROM process_tags WHERE performer IS NOT NULL AND performer != ''")
        tags_with_performer = c.fetchall()
        
        for tag_id, performer in tags_with_performer:
            # חלץ מספר אישי מהמבצע
            id_match = re.search(r'\((\d+)\)', performer)
            if id_match:
                performer_id = id_match.group(1)
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (performer_id,))
                sig_result = c.fetchone()
                if sig_result:
                    signature = sig_result[0]
                    c.execute("UPDATE process_tags SET performer_signature = ? WHERE tag_id = ?", (signature, tag_id))
                    print(f"✅ עדכנתי חתימת מבצע לתג {tag_id}")
        
        # עדכן חתימות בודק
        c.execute("SELECT tag_id, checker FROM process_tags WHERE checker IS NOT NULL AND checker != ''")
        tags_with_checker = c.fetchall()
        
        for tag_id, checker in tags_with_checker:
            # חלץ מספר אישי מהבודק
            id_match = re.search(r'\((\d+)\)', checker)
            if id_match:
                checker_id = id_match.group(1)
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (checker_id,))
                sig_result = c.fetchone()
                if sig_result:
                    signature = sig_result[0]
                    c.execute("UPDATE process_tags SET checker_signature = ? WHERE tag_id = ?", (signature, tag_id))
                    print(f"✅ עדכנתי חתימת בודק לתג {tag_id}")
        
        conn.commit()
        print("✅ תיקון הושלם!")
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בתיקון: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🔧 סקריפט תיקון בודק ומבצע")
    print("=" * 50)
    
    database_path = input("הזן נתיב לקובץ ה-database שלך (או Enter לשימוש ב-database.db): ").strip()
    
    # אם לא הוזן נתיב, השתמש בברירת מחדל
    if not database_path:
        database_path = "database.db"
        print(f"🔧 משתמש בנתיב ברירת מחדל: {database_path}")
    
    # בדוק אם הקובץ קיים
    if not os.path.exists(database_path):
        print(f"❌ קובץ לא נמצא: {database_path}")
        print("💡 ודא שהנתיב נכון או שהקובץ קיים")
        return
    
    if fix_performer_checker_data(database_path):
        print("\n🎉 תיקון הושלם בהצלחה!")
        print("💡 עכשיו הבודק והמבצע אמורים להופיע נכון בהדפסה")
        print("💡 כולל השמות ומספרי התז שלהם")
    else:
        print("\n❌ תיקון נכשל")

if __name__ == "__main__":
    main()
