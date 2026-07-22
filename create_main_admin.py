#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט ליצירת admin ראשי
"""

import sqlite3
import hashlib
import os

def create_main_admin():
    """יוצר admin ראשי עם פרטים שונים"""
    print("👑 יצירת Admin ראשי")
    print("=" * 50)
    
    # פרטי ה-admin הראשי
    main_admin_username = "superadmin"
    main_admin_password = "super1234"
    
    print(f"👤 שם משתמש: {main_admin_username}")
    print(f"🔑 סיסמה: {main_admin_password}")
    
    # בדוק אם קובץ database.db קיים
    if not os.path.exists('database.db'):
        print("❌ קובץ database.db לא קיים")
        print("🔧 יוצר מסד נתונים חדש...")
        
        # צור מסד נתונים חדש
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # צור טבלת משתמשים
        cursor.execute('''CREATE TABLE users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          password TEXT NOT NULL,
                          role TEXT DEFAULT 'user')''')
        
        conn.commit()
        conn.close()
        print("✅ מסד נתונים נוצר")
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # בדוק אם משתמש superadmin קיים
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (main_admin_username,))
        admin_exists = cursor.fetchone()[0] > 0
        
        if admin_exists:
            print("⚠️  משתמש superadmin כבר קיים")
            
            # עדכן סיסמה
            hashed_password = hashlib.sha256(main_admin_password.encode()).hexdigest()
            cursor.execute("UPDATE users SET password = ?, role = 'admin' WHERE username = ?", 
                         (hashed_password, main_admin_username))
            conn.commit()
            print("✅ סיסמת superadmin עודכנה")
        else:
            # צור משתמש superadmin חדש
            hashed_password = hashlib.sha256(main_admin_password.encode()).hexdigest()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                         (main_admin_username, hashed_password, 'admin'))
            conn.commit()
            print("✅ משתמש superadmin נוצר")
        
        # בדוק את המשתמש
        cursor.execute("SELECT username, role FROM users WHERE username = ?", (main_admin_username,))
        user = cursor.fetchone()
        if user:
            print(f"👤 משתמש: {user[0]} ({user[1]})")
            print(f"🔑 סיסמה: {main_admin_password}")
        
        conn.close()
        print("✅ יצירת Admin ראשי הושלמה בהצלחה")
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת Admin ראשי: {e}")

if __name__ == "__main__":
    create_main_admin()
