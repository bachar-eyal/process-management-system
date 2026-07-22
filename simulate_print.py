#!/usr/bin/env python3
"""
סקריפט לבדיקת איך הנתונים נראים בהדפסה
"""

import sqlite3
import os
import json

def simulate_print_data(db_path):
    """סמלץ איך הנתונים ייראו בהדפסה"""
    
    if not os.path.exists(db_path):
        print(f"❌ קובץ לא נמצא: {db_path}")
        return False
    
    print(f"🖨️ סמלץ הדפסה עבור: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # בדוק תג אחד
        c.execute("SELECT tag_id, serial_number, sku FROM process_tags LIMIT 1")
        tag_info = c.fetchone()
        
        if not tag_info:
            print("❌ לא נמצאו תגים")
            return False
        
        tag_id, serial_number, sku = tag_info
        print(f"📋 בודק תג {tag_id} (serial: {serial_number}, sku: {sku})")
        
        # שלוף את כל הנתונים כמו בהדפסה
        data = {}
        
        # products
        c.execute("SELECT * FROM products WHERE serial_number=? AND sku=?", (serial_number, sku))
        products_result = c.fetchall()
        data["products"] = products_result
        print(f"📦 products: {len(products_result)} רשומות")
        
        # process_tags
        c.execute("SELECT * FROM process_tags WHERE tag_id=?", (tag_id,))
        process_tags_result = c.fetchall()
        data["process_tags"] = process_tags_result
        print(f"🏷️ process_tags: {len(process_tags_result)} רשומות")
        
        if process_tags_result:
            tag = process_tags_result[0]
            print(f"  תג: {tag}")
            
            # בדוק את תיאור התקלה
            if len(tag) > 2:
                fault_desc = tag[2]
                print(f"  תיאור תקלה: '{fault_desc}'")
                if fault_desc:
                    print(f"    אורך: {len(fault_desc)}")
                    print(f"    מכיל \\n: {'\\n' in fault_desc}")
                    print(f"    מכיל \n: {'\n' in fault_desc}")
                    if '\n' in fault_desc:
                        parts = fault_desc.split('\n')
                        print(f"    חלקים: {len(parts)}")
                        for i, part in enumerate(parts):
                            print(f"      {i}: '{part}'")
        
        # approved_skus
        c.execute("SELECT * FROM approved_skus WHERE sku_code=?", (sku,))
        approved_skus_result = c.fetchall()
        data["approved_skus"] = approved_skus_result
        print(f"✅ approved_skus: {len(approved_skus_result)} רשומות")
        
        # team_members
        c.execute("SELECT * FROM team_members")
        team_members_result = c.fetchall()
        data["team_members"] = team_members_result
        print(f"👥 team_members: {len(team_members_result)} רשומות")
        
        # spare_parts_usage
        c.execute("""SELECT spu.usage_id, sp.part_number, sp.description, sp.manufacturer, spu.serial_number, spu.date_used
                     FROM spare_parts_usage spu 
                     JOIN spare_parts sp ON spu.part_id = sp.part_id 
                     WHERE spu.tag_id = ? 
                     ORDER BY spu.date_used DESC""", (tag_id,))
        spare_parts_usage_result = c.fetchall()
        data["spare_parts_usage"] = spare_parts_usage_result
        print(f"🔧 spare_parts_usage: {len(spare_parts_usage_result)} רשומות")
        
        # בדוק חתימות
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'performer_signature' in columns and 'checker_signature' in columns:
            c.execute("SELECT performer_signature, checker_signature FROM process_tags WHERE tag_id=?", (tag_id,))
            signatures = c.fetchone()
            if signatures:
                perf_sig, check_sig = signatures
                print(f"✍️ חתימות:")
                print(f"  מבצע: {'יש' if perf_sig else 'אין'}")
                print(f"  בודק: {'יש' if check_sig else 'אין'}")
        
        # הפוך את הנתונים לרשימה שטוחה כמו בהדפסה
        print(f"\n📋 נתונים שטוחים:")
        all_values = []
        for table, rows in data.items():
            for row in rows:
                for idx, value in enumerate(row):
                    all_values.append((f"{table}.{idx}", str(value) if value is not None else ""))
        
        # הדפס את השדות החשובים
        important_fields = [
            'process_tags.2',  # fault_description
            'process_tags.9',  # performer
            'process_tags.10', # checker
            'process_tags.8',  # test_results
            'process_tags.11', # item_statuses
        ]
        
        for field_name in important_fields:
            for var_name, value in all_values:
                if var_name == field_name:
                    print(f"  {field_name}: '{value}'")
                    break
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בסמלציה: {e}")
        return False
    finally:
        conn.close()

def main():
    """פונקציה ראשית"""
    print("🖨️ סקריפט סמלציית הדפסה")
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
    
    if simulate_print_data(database_path):
        print("\n✅ סמלציה הושלמה")
        print("💡 עכשיו אתה יכול לראות בדיוק איך הנתונים ייראו בהדפסה")
    else:
        print("\n❌ סמלציה נכשלה")

if __name__ == "__main__":
    main()
