#!/usr/bin/env python3
"""
סקריפט להשוואת מבנה database ישן וחדש
"""

import sqlite3
import os

def compare_databases(old_db, new_db):
    """השווה בין שני databases"""
    
    if not os.path.exists(old_db):
        print(f"❌ קובץ לא נמצא: {old_db}")
        return False
    
    if not os.path.exists(new_db):
        print(f"❌ קובץ לא נמצא: {new_db}")
        return False
    
    print(f"🔍 משווה בין:")
    print(f"  ישן: {old_db}")
    print(f"  חדש: {new_db}")
    
    # חיבור לdatabases
    old_conn = sqlite3.connect(old_db)
    new_conn = sqlite3.connect(new_db)
    
    old_c = old_conn.cursor()
    new_c = new_conn.cursor()
    
    try:
        # השווה מבנה process_tags
        print(f"\n📋 השוואת process_tags:")
        print("-" * 50)
        
        old_c.execute("PRAGMA table_info(process_tags)")
        old_columns = old_c.fetchall()
        
        new_c.execute("PRAGMA table_info(process_tags)")
        new_columns = new_c.fetchall()
        
        print(f"עמודות בישן ({len(old_columns)}):")
        for i, (cid, name, type_, notnull, default, pk) in enumerate(old_columns):
            print(f"  {i}: {name} ({type_})")
        
        print(f"\nעמודות בחדש ({len(new_columns)}):")
        for i, (cid, name, type_, notnull, default, pk) in enumerate(new_columns):
            print(f"  {i}: {name} ({type_})")
        
        # השווה שמות עמודות
        old_names = [col[1] for col in old_columns]
        new_names = [col[1] for col in new_columns]
        
        print(f"\n🔍 השוואת שמות עמודות:")
        print(f"  רק בישן: {set(old_names) - set(new_names)}")
        print(f"  רק בחדש: {set(new_names) - set(old_names)}")
        print(f"  משותפות: {set(old_names) & set(new_names)}")
        
        # השווה סדר עמודות
        print(f"\n📊 השוואת סדר עמודות:")
        common_columns = set(old_names) & set(new_names)
        
        for col in common_columns:
            old_pos = old_names.index(col)
            new_pos = new_names.index(col)
            if old_pos != new_pos:
                print(f"  ⚠️ {col}: ישן={old_pos}, חדש={new_pos}")
            else:
                print(f"  ✅ {col}: מיקום זהה ({old_pos})")
        
        # השווה נתונים לדוגמה
        print(f"\n📊 השוואת נתונים לדוגמה:")
        
        old_c.execute("SELECT * FROM process_tags LIMIT 1")
        old_sample = old_c.fetchone()
        
        new_c.execute("SELECT * FROM process_tags LIMIT 1")
        new_sample = new_c.fetchone()
        
        if old_sample and new_sample:
            print(f"תג לדוגמה בישן:")
            for i, (name, value) in enumerate(zip(old_names, old_sample)):
                print(f"  {i}: {name} = '{value}'")
            
            print(f"\nתג לדוגמה בחדש:")
            for i, (name, value) in enumerate(zip(new_names, new_sample)):
                print(f"  {i}: {name} = '{value}'")
        
        # השווה מבנה team_members
        print(f"\n👥 השוואת team_members:")
        print("-" * 50)
        
        old_c.execute("PRAGMA table_info(team_members)")
        old_team_columns = old_c.fetchall()
        
        new_c.execute("PRAGMA table_info(team_members)")
        new_team_columns = new_c.fetchall()
        
        old_team_names = [col[1] for col in old_team_columns]
        new_team_names = [col[1] for col in new_team_columns]
        
        print(f"עמודות בישן: {', '.join(old_team_names)}")
        print(f"עמודות בחדש: {', '.join(new_team_names)}")
        
        # השווה מבנה products
        print(f"\n📦 השוואת products:")
        print("-" * 50)
        
        old_c.execute("PRAGMA table_info(products)")
        old_products_columns = old_c.fetchall()
        
        new_c.execute("PRAGMA table_info(products)")
        new_products_columns = new_c.fetchall()
        
        old_products_names = [col[1] for col in old_products_columns]
        new_products_names = [col[1] for col in new_products_columns]
        
        print(f"עמודות בישן: {', '.join(old_products_names)}")
        print(f"עמודות בחדש: {', '.join(new_products_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ שגיאה בהשוואה: {e}")
        return False
    finally:
        old_conn.close()
        new_conn.close()

def main():
    """פונקציה ראשית"""
    print("🔍 סקריפט השוואת databases")
    print("=" * 50)
    
    old_db = input("הזן נתיב ל-database הישן (או Enter לשימוש ב-database.db): ").strip()
    if not old_db:
        old_db = "database.db"
    
    new_db = input("הזן נתיב ל-database החדש (או Enter לשימוש ב-process_tags.db): ").strip()
    if not new_db:
        new_db = "process_tags.db"
    
    # בדוק אם הקבצים קיימים
    if not os.path.exists(old_db):
        print(f"❌ קובץ לא נמצא: {old_db}")
        return
    
    if not os.path.exists(new_db):
        print(f"❌ קובץ לא נמצא: {new_db}")
        return
    
    if compare_databases(old_db, new_db):
        print("\n✅ השוואה הושלמה")
        print("💡 עכשיו אתה יכול לראות בדיוק מה ההבדלים")
    else:
        print("\n❌ השוואה נכשלה")

if __name__ == "__main__":
    main()
