#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סקריפט ליצירת משתמש admin במסד הנתונים הראשי
"""

import sqlite3
import hashlib
import os

def create_admin_user():
    """יוצר משתמש admin במסד הנתונים הראשי"""
    print("👑 יצירת משתמש admin")
    print("=" * 50)
    
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
        
        # בדוק אם משתמש admin קיים
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()[0] > 0
        
        if admin_exists:
            print("⚠️  משתמש admin כבר קיים")
            
            # עדכן סיסמה
            password = "eyal1234"
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("UPDATE users SET password = ?, role = 'admin' WHERE username = 'admin'", 
                         (hashed_password,))
            conn.commit()
            print("✅ סיסמת admin עודכנה")
        else:
            # צור משתמש admin חדש
            password = "eyal1234"
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                         ('admin', hashed_password, 'admin'))
            conn.commit()
            print("✅ משתמש admin נוצר")
        
        # בדוק את המשתמש
        cursor.execute("SELECT username, role FROM users WHERE username = 'admin'")
        user = cursor.fetchone()
        if user:
            print(f"👤 משתמש: {user[0]} ({user[1]})")
            print(f"🔑 סיסמה: eyal1234")
        
        conn.close()
        print("✅ יצירת משתמש admin הושלמה בהצלחה")
        
    except Exception as e:
        print(f"❌ שגיאה ביצירת משתמש admin: {e}")

if __name__ == "__main__":
    create_admin_user()
