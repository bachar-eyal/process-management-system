from flask import Flask, request, render_template, redirect, url_for, jsonify, session, flash, make_response
import sqlite3
import json
import re
from datetime import datetime, date, timedelta
import sqlite3
import qrcode
from io import BytesIO
import xlsxwriter
import base64
import binascii
import os
import threading
import time
import urllib.parse
from collections import Counter, OrderedDict
from calendar import month_name
from functools import wraps
from dotenv import load_dotenv
from signature_on_image import print_signature_on_image
from team_manager import TeamManager

# טען משתני סביבה מקובץ .env
load_dotenv()

app = Flask(__name__)
# טען secret key מ-.env, אם לא קיים - השתמש ב-fallback (אבל זה לא בטוח!)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-in-production-' + os.urandom(32).hex())

# אתחל את מנהל הצוותים
team_manager = TeamManager()

FINAL_CHECK_SNAPSHOTS_DIR = os.path.join(app.root_path, 'static', 'final_checks_snapshots')
os.makedirs(FINAL_CHECK_SNAPSHOTS_DIR, exist_ok=True)

def validate_password_strength(password):
    """בודק את עוצמת הסיסמה"""
    if len(password) < 6:
        return False, "הסיסמה חייבת להיות לפחות 6 תווים"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "הסיסמה חייבת להכיל לפחות אות אחת"
    
    if not re.search(r'\d', password):
        return False, "הסיסמה חייבת להכיל לפחות מספר אחד"
    
    return True, "הסיסמה תקינה"

def log_activity(user_id, username, team_id, action, details=""):
    """מתעד פעילות משתמש"""
    try:
        conn = sqlite3.connect('teams.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      username TEXT,
                      team_id INTEGER,
                      action TEXT,
                      details TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''INSERT INTO activity_log (user_id, username, team_id, action, details)
                     VALUES (?, ?, ?, ?, ?)''', (user_id, username, team_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging activity: {e}")

def get_team_db_path():
    """מחזיר את נתיב מסד הנתונים של הצוות הנוכחי"""
    if 'team_id' in session:
        return team_manager.get_team_db_path(session['team_id'])
    return None

def chatbot_process_query(query):
    """מעבד שאילתה לבוט העוזר"""
    query = query.lower().strip()
    db_path = get_team_db_path()
    
    if not db_path:
        return "❌ לא ניתן לגשת למסד הנתונים.\n\nאנא התחבר מחדש למערכת."
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # חיפוש תגים לפי מספר סידורי
        if 'מספר סידורי' in query or 'serial' in query:
            serial_match = re.search(r'(\d+)', query)
            if serial_match:
                serial = serial_match.group(1)
                
                # בדיקה אם השאלה מבקשת רק תגים פתוחים או רק תגים סגורים
                is_open_only = 'פתוח' in query or 'open' in query
                is_closed_only = 'סגור' in query or 'closed' in query
                
                if is_open_only:
                    # חיפוש רק תגים פתוחים
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE serial_number = ? AND is_closed = 0
                        ORDER BY date_opened DESC
                    """, (serial,))
                    response_prefix = f"🔍 **נמצאו תגים פתוחים למספר הסידורי {serial}:**\n\n"
                elif is_closed_only:
                    # חיפוש רק תגים סגורים
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE serial_number = ? AND is_closed = 1
                        ORDER BY date_opened DESC
                    """, (serial,))
                    response_prefix = f"🔍 **נמצאו תגים סגורים למספר הסידורי {serial}:**\n\n"
                else:
                    # חיפוש כל התגים (פתוחים וסגורים)
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE serial_number = ?
                        ORDER BY date_opened DESC
                    """, (serial,))
                    response_prefix = f"🔍 **נמצאו תגים למספר הסידורי {serial}:**\n\n"
                
                results = c.fetchall()
                
                if results:
                    response = response_prefix
                    response += "─" * 50 + "\n\n"
                    
                    for i, tag in enumerate(results, 1):
                        status_icon = "✅" if tag[6] else "⏳"
                        status_text = "סגור" if tag[6] else "פתוח"
                        
                        response += f"**{i}. {status_icon} תג #{tag[0]}**\n"
                        response += f"📱 מספר סידורי: `{tag[1]}`\n"
                        response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                        response += f"📝 תיאור: {tag[3][:80]}{'...' if len(tag[3]) > 80 else ''}\n"
                        response += f"📅 נפתח: {tag[5][:10]}\n"
                        response += f"📊 סטטוס: {tag[4]} ({status_text})\n\n"
                        response += "─" * 30 + "\n\n"
                    
                    return response
                else:
                    if is_open_only:
                        return f"❌ **לא נמצאו תגים פתוחים למספר הסידורי {serial}**\n\nנסה לחפש עם מספר אחר או בדוק את הכתיב."
                    elif is_closed_only:
                        return f"❌ **לא נמצאו תגים סגורים למספר הסידורי {serial}**\n\nנסה לחפש עם מספר אחר או בדוק את הכתיב."
                    else:
                        return f"❌ **לא נמצאו תגים למספר הסידורי {serial}**\n\nנסה לחפש עם מספר אחר או בדוק את הכתיב."
        
        # חיפוש תגים לפי SKU
        elif 'sku' in query or 'מק"ט' in query or 'מקט' in query or 'פריט' in query:
            sku_match = re.search(r'(\d+)', query)
            if sku_match:
                sku = sku_match.group(1)
                
                # בדיקה אם השאלה מבקשת רק תגים פתוחים או רק תגים סגורים
                is_open_only = 'פתוח' in query or 'open' in query
                is_closed_only = 'סגור' in query or 'closed' in query
                
                if is_open_only:
                    # חיפוש רק תגים פתוחים
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE sku = ? AND is_closed = 0
                        ORDER BY date_opened DESC
                    """, (sku,))
                    response_prefix = f"🔍 **נמצאו תגים פתוחים למק\"ט {sku}:**\n\n"
                elif is_closed_only:
                    # חיפוש רק תגים סגורים
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE sku = ? AND is_closed = 1
                        ORDER BY date_opened DESC
                    """, (sku,))
                    response_prefix = f"🔍 **נמצאו תגים סגורים למק\"ט {sku}:**\n\n"
                else:
                    # חיפוש כל התגים (פתוחים וסגורים)
                    c.execute("""
                        SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                        FROM process_tags 
                        WHERE sku = ?
                        ORDER BY date_opened DESC
                    """, (sku,))
                    response_prefix = f"🔍 **נמצאו תגים למק\"ט {sku}:**\n\n"
                
                results = c.fetchall()
                
                if results:
                    response = response_prefix
                    response += "─" * 50 + "\n\n"
                    
                    for i, tag in enumerate(results, 1):
                        status_icon = "✅" if tag[6] else "⏳"
                        status_text = "סגור" if tag[6] else "פתוח"
                        
                        response += f"**{i}. {status_icon} תג #{tag[0]}**\n"
                        response += f"📱 מספר סידורי: `{tag[1]}`\n"
                        response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                        response += f"📝 תיאור: {tag[3][:80]}{'...' if len(tag[3]) > 80 else ''}\n"
                        response += f"📅 נפתח: {tag[5][:10]}\n"
                        response += f"📊 סטטוס: {tag[4]} ({status_text})\n\n"
                        response += "─" * 30 + "\n\n"
                    
                    return response
                else:
                    if is_open_only:
                        return f"❌ **לא נמצאו תגים פתוחים למק\"ט {sku}**\n\nנסה לחפש עם מק\"ט אחר או בדוק את הכתיב."
                    elif is_closed_only:
                        return f"❌ **לא נמצאו תגים סגורים למק\"ט {sku}**\n\nנסה לחפש עם מק\"ט אחר או בדוק את הכתיב."
                    else:
                        return f"❌ **לא נמצאו תגים למק\"ט {sku}**\n\nנסה לחפש עם מק\"ט אחר או בדוק את הכתיב."
        
        # סטטיסטיקות כללית
        elif 'סטטיסטיקות' in query or 'statistics' in query or 'כמה' in query:
            c.execute("SELECT COUNT(*) FROM process_tags")
            total_tags = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 0")
            open_tags = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 1")
            closed_tags = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM products")
            total_products = c.fetchone()[0]
            
            response = "📊 **סטטיסטיקות מערכת:**\n\n"
            response += "─" * 40 + "\n\n"
            response += f"🏷️ **סה\"כ תגים:** {total_tags:,}\n"
            response += f"⏳ **תגים פתוחים:** {open_tags:,}\n"
            response += f"✅ **תגים סגורים:** {closed_tags:,}\n"
            response += f"📦 **מוצרים במערכת:** {total_products:,}\n\n"
            
            if total_tags > 0:
                completion_rate = round((closed_tags / total_tags * 100), 1)
                response += f"📈 **אחוז השלמה:** {completion_rate}%\n"
            
            return response
        
        # תגים פתוחים
        elif 'פתוחים' in query or 'open' in query or 'פעילים' in query:
            c.execute("""
                SELECT tag_id, serial_number, sku, fault_description, status, date_opened
                FROM process_tags 
                WHERE is_closed = 0 
                ORDER BY date_opened DESC 
                LIMIT 10
            """)
            results = c.fetchall()
            
            if results:
                response = f"⏳ **תגים פתוחים ({len(results)}):**\n\n"
                response += "─" * 50 + "\n\n"
                
                for i, tag in enumerate(results, 1):
                    response += f"**{i}. 🔴 תג #{tag[0]}**\n"
                    response += f"📱 מספר סידורי: `{tag[1]}`\n"
                    response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                    response += f"📝 תיאור: {tag[3][:80]}{'...' if len(tag[3]) > 80 else ''}\n"
                    response += f"📅 נפתח: {tag[5][:10]}\n"
                    response += f"📊 סטטוס: {tag[4]}\n\n"
                    response += "─" * 30 + "\n\n"
                
                return response
            else:
                return "✅ **אין תגים פתוחים כרגע!**\n\nכל התגים במערכת סגורים."
        
        # תגים שנסגרו לאחרונה
        elif 'נסגרו' in query or 'closed' in query or 'הושלמו' in query:
            c.execute("""
                SELECT tag_id, serial_number, sku, fault_description, date_updated
                FROM process_tags 
                WHERE is_closed = 1 
                ORDER BY date_updated DESC 
                LIMIT 10
            """)
            results = c.fetchall()
            
            if results:
                response = f"✅ **תגים שנסגרו לאחרונה ({len(results)}):**\n\n"
                response += "─" * 50 + "\n\n"
                
                for i, tag in enumerate(results, 1):
                    response += f"**{i}. 🟢 תג #{tag[0]}**\n"
                    response += f"📱 מספר סידורי: `{tag[1]}`\n"
                    response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                    response += f"📝 תיאור: {tag[3][:80]}{'...' if len(tag[3]) > 80 else ''}\n"
                    response += f"📅 נסגר: {tag[4][:10]}\n\n"
                    response += "─" * 30 + "\n\n"
                
                return response
            else:
                return "❌ **אין תגים סגורים במערכת**\n\nכל התגים כרגע פתוחים."
        
        # חיפוש לפי תיאור תקלה
        elif 'תקלה' in query or 'בעיה' in query or 'issue' in query:
            keywords = re.findall(r'\b\w+\b', query)
            keywords = [k for k in keywords if len(k) > 2 and k not in ['תקלה', 'בעיה', 'issue', 'מה', 'איך', 'איפה']]
            
            if keywords:
                search_terms = ' OR '.join([f"fault_description LIKE '%{k}%'" for k in keywords])
                c.execute(f"""
                    SELECT tag_id, serial_number, sku, fault_description, status, date_opened, is_closed
                    FROM process_tags 
                    WHERE {search_terms}
                    ORDER BY date_opened DESC 
                    LIMIT 5
                """)
                results = c.fetchall()
                
                if results:
                    response = f"🔍 **נמצאו {len(results)} תגים עם מילות המפתח '{', '.join(keywords)}':**\n\n"
                    response += "─" * 50 + "\n\n"
                    
                    for i, tag in enumerate(results, 1):
                        status_icon = "✅" if tag[6] else "⏳"
                        status_text = "סגור" if tag[6] else "פתוח"
                        
                        response += f"**{i}. {status_icon} תג #{tag[0]}**\n"
                        response += f"📱 מספר סידורי: `{tag[1]}`\n"
                        response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                        response += f"📝 תיאור: {tag[3][:100]}{'...' if len(tag[3]) > 100 else ''}\n"
                        response += f"📅 נפתח: {tag[5][:10]}\n"
                        response += f"📊 סטטוס: {tag[4]} ({status_text})\n\n"
                        response += "─" * 30 + "\n\n"
                    
                    return response
                else:
                    return f"❌ **לא נמצאו תגים עם מילות המפתח '{', '.join(keywords)}'**\n\nנסה מילות מפתח אחרות או בדוק את הכתיב."
        
        # עזרה כללית
        elif 'עזרה' in query or 'help' in query or ('מה' in query and 'יכול' in query):
            response = "🤖 **איך אני יכול לעזור לך?**\n\n"
            response += "─" * 40 + "\n\n"
            
            response += "🔍 **חיפוש תגים:**\n"
            response += "• `חפש מספר סידורי 12345`\n"
            response += "• `חפש מק\"ט 67890`\n"
            response += "• `תגים עם תקלה אלקטרונית`\n\n"
            
            response += "📊 **סטטיסטיקות:**\n"
            response += "• `הראה סטטיסטיקות`\n"
            response += "• `כמה תגים יש?`\n\n"
            
            response += "⏳ **תגים פתוחים:**\n"
            response += "• `הראה תגים פתוחים`\n"
            response += "• `תגים פעילים`\n\n"
            
            response += "✅ **תגים סגורים:**\n"
            response += "• `תגים שנסגרו`\n"
            response += "• `תגים שהושלמו`\n\n"
            
            response += "📅 **תגים מהשבוע האחרון:**\n"
            response += "• `תגים מהשבוע`\n\n"
            
            response += "💡 **טיפ:** שאל אותי כל שאלה על התגים במערכת!"
            return response
        
        # תגים מהשבוע האחרון
        elif 'השבוע' in query or 'week' in query:
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            c.execute("""
                SELECT tag_id, serial_number, sku, fault_description, is_closed, date_opened
                FROM process_tags 
                WHERE date_opened >= ?
                ORDER BY date_opened DESC
            """, (week_ago,))
            results = c.fetchall()
            
            if results:
                response = f"📅 **תגים מהשבוע האחרון ({len(results)}):**\n\n"
                response += "─" * 50 + "\n\n"
                
                for i, tag in enumerate(results, 1):
                    status_icon = "✅" if tag[4] else "⏳"
                    status_text = "סגור" if tag[4] else "פתוח"
                    
                    response += f"**{i}. {status_icon} תג #{tag[0]}**\n"
                    response += f"📱 מספר סידורי: `{tag[1]}`\n"
                    response += f"🏷️ מק\"ט: `{tag[2] or 'לא מוגדר'}`\n"
                    response += f"📝 תיאור: {tag[3][:80]}{'...' if len(tag[3]) > 80 else ''}\n"
                    response += f"📅 נפתח: {tag[5][:10]}\n"
                    response += f"📊 סטטוס: {status_text}\n\n"
                    response += "─" * 30 + "\n\n"
                
                return response
            else:
                return "📅 **אין תגים מהשבוע האחרון**\n\nלא נוצרו תגים חדשים בשבוע האחרון."
        
        # אם לא נמצאה התאמה
        else:
            response = "🤔 **לא הבנתי את השאלה שלך.**\n\n"
            response += "נסה לשאול:\n\n"
            response += "• `עזרה` - לראות מה אני יכול לעשות\n"
            response += "• `חפש מספר סידורי 12345`\n"
            response += "• `הראה סטטיסטיקות`\n"
            response += "• `תגים פתוחים`\n\n"
            response += "💡 **טיפ:** השתמש במילים בעברית או באנגלית!"
            return response
        
        conn.close()
        
    except Exception as e:
        return f"❌ **שגיאה בעיבוד השאלה:**\n\n{str(e)}\n\nאנא נסה שוב או פנה למנהל המערכת."

def init_db(db_path='database.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # בדוק אם הטבלה קיימת
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
    table_exists = c.fetchone()
    
    if not table_exists:
        # יצירת טבלה חדשה עם PRIMARY KEY מורכב
        c.execute('''CREATE TABLE products
                     (serial_number TEXT, sku TEXT, date_added DATETIME,
                      PRIMARY KEY (serial_number, sku))''')
    else:
        # אם הטבלה קיימת, בדוק את המבנה הנוכחי
        c.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in c.fetchall()]
        
        # אם יש PRIMARY KEY על serial_number בלבד, נצטרך ליצור טבלה חדשה
        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'")
        create_sql = c.fetchone()[0]
        
        if 'PRIMARY KEY (serial_number)' in create_sql or 'serial_number TEXT PRIMARY KEY' in create_sql:
            # שמור את הנתונים הקיימים
            c.execute("SELECT serial_number, sku, date_added FROM products")
            existing_data = c.fetchall()
            
            # מחק את הטבלה הישנה
            c.execute("DROP TABLE products")
            
            # צור טבלה חדשה עם PRIMARY KEY מורכב
            c.execute('''CREATE TABLE products
                         (serial_number TEXT, sku TEXT, date_added DATETIME,
                          PRIMARY KEY (serial_number, sku))''')
            
            # החזר את הנתונים
            for row in existing_data:
                c.execute("INSERT OR IGNORE INTO products (serial_number, sku, date_added) VALUES (?, ?, ?)", row)

    c.execute('''CREATE TABLE IF NOT EXISTS process_tags
                 (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, serial_number TEXT,
                  fault_description TEXT, actions_taken TEXT, status TEXT,
                  date_updated DATETIME, is_closed INTEGER DEFAULT 0,
                  date_opened DATETIME, test_results TEXT, performer TEXT)''')

    # הוסף עמודות חסרות לטבלת process_tags (כולל חתימות פר תג)
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    try:
        if 'performer' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN performer TEXT")
        if 'checker' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN checker TEXT")
        if 'item_statuses' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN item_statuses TEXT")
        if 'sku' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN sku TEXT")
        if 'performer_signature' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN performer_signature TEXT")
        if 'checker_signature' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN checker_signature TEXT")
        if 'final_check_snapshot' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN final_check_snapshot TEXT")
    except sqlite3.OperationalError:
        pass

    # צור טבלת approved_skus אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS approved_skus
                 (sku_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  sku_code TEXT UNIQUE NOT NULL,
                  description TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # הוסף מק"טים ברירת מחדל אם הטבלה ריקה
    c.execute("SELECT COUNT(*) FROM approved_skus")
    if c.fetchone()[0] == 0:
        default_skus = []
        for sku_code, description in default_skus:
            c.execute("INSERT INTO approved_skus (sku_code, description) VALUES (?, ?)", (sku_code, description))

    # צור טבלת approved_issues אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS approved_issues
                 (issue_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  issue_code TEXT UNIQUE NOT NULL,
                  description TEXT,
                  solution TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # צור טבלת spare_parts אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS spare_parts
                 (part_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  part_number TEXT UNIQUE NOT NULL,
                  description TEXT,
                  manufacturer TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # צור טבלת spare_parts_usage אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS spare_parts_usage
                 (usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tag_id INTEGER NOT NULL,
                  part_id INTEGER NOT NULL,
                  serial_number TEXT NOT NULL,
                  date_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (tag_id) REFERENCES process_tags (tag_id),
                  FOREIGN KEY (part_id) REFERENCES spare_parts (part_id))''')
    
    # צור טבלת team_members אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS team_members
                 (member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  id_number TEXT UNIQUE NOT NULL,
                  role TEXT NOT NULL CHECK (role IN ('performer', 'checker', 'both')),
                  signature TEXT,
                  is_active BOOLEAN DEFAULT 1,
                  date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # בדוק אם יש עמודת signature ואם לא - הוסף אותה
    c.execute("PRAGMA table_info(team_members)")
    columns = [col[1] for col in c.fetchall()]
    if 'signature' not in columns:
        c.execute("ALTER TABLE team_members ADD COLUMN signature TEXT")
        conn.commit()
    
    # הוסף עמודת solution אם לא קיימת
    c.execute("PRAGMA table_info(approved_issues)")
    columns = [col[1] for col in c.fetchall()]
    
    try:
        if 'solution' not in columns:
            c.execute("ALTER TABLE approved_issues ADD COLUMN solution TEXT")
    except sqlite3.OperationalError:
        pass

    # הוסף תקלות ברירת מחדל אם הטבלה ריקה
    c.execute("SELECT COUNT(*) FROM approved_issues")
    if c.fetchone()[0] == 0:
        default_issues = []
        for issue_code, description in default_issues:
            c.execute("INSERT INTO approved_issues (issue_code, description) VALUES (?, ?)", (issue_code, description))
    
    # הוסף עובדי צוות ברירת מחדל אם הטבלה ריקה
    c.execute("SELECT COUNT(*) FROM team_members")
    if c.fetchone()[0] == 0:
        default_members = []
        for name, id_number, role in default_members:
            c.execute("INSERT INTO team_members (name, id_number, role) VALUES (?, ?, ?)", (name, id_number, role))

    # הוסף עמודות חסרות לטבלת process_tags
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    
    try:
        if 'priority' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN priority INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        if 'sku' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN sku TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        if 'final_check_snapshot' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN final_check_snapshot TEXT")
    except sqlite3.OperationalError:
        pass

    # הסר כל מחיקת טבלת users (אין DROP TABLE)
    # צור טבלת משתמשים אם לא קיימת
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )''')

    # הוסף משתמש admin רק אם לא קיים
    c.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "eyal1234", "admin"))

    # הוספת עמודה final_check_image לטבלת approved_skus אם לא קיימת
    c.execute("PRAGMA table_info(approved_skus)")
    sku_columns = [col[1] for col in c.fetchall()]
    if 'final_check_image' not in sku_columns:
        c.execute("ALTER TABLE approved_skus ADD COLUMN final_check_image TEXT")

    # הוספת עמודה manufacturer לטבלת spare_parts אם לא קיימת
    c.execute("PRAGMA table_info(spare_parts)")
    spare_parts_columns = [col[1] for col in c.fetchall()]
    if 'manufacturer' not in spare_parts_columns:
        c.execute("ALTER TABLE spare_parts ADD COLUMN manufacturer TEXT")

    conn.commit()
    conn.close()


def migrate_database_data():
    src_db = 'database test 1.db'
    dest_db = 'database.db'
    if not os.path.exists(src_db):
        return
    src_conn = sqlite3.connect(src_db)
    dest_conn = sqlite3.connect(dest_db)
    src_c = src_conn.cursor()
    dest_c = dest_conn.cursor()
    # קבל את כל שמות הטבלאות
    src_c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in src_c.fetchall() if row[0] != 'sqlite_sequence']
    for table in tables:
        # קבל את כל השורות מהטבלה
        src_c.execute(f"SELECT * FROM {table}")
        rows = src_c.fetchall()
        # קבל את שמות העמודות
        src_c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in src_c.fetchall()]
        col_str = ', '.join(columns)
        placeholders = ', '.join(['?'] * len(columns))
        # מחק נתונים קיימים בטבלה ביעד (כדי למנוע כפילויות)
        dest_c.execute(f"DELETE FROM {table}")
        # הוסף את כל השורות
        for row in rows:
            dest_c.execute(f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES ({placeholders})", row)
    dest_conn.commit()
    src_conn.close()
    dest_conn.close()
    # מחק את קובץ המקור
    os.remove(src_db)


def get_sku_by_description(description):
    """קבל קוד מק"ט לפי תיאור"""
    db_path = get_team_db_path()
    if not db_path:
        return None
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT sku_code FROM approved_skus WHERE description = ? AND is_active = 1", (description,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # בדוק אם המשתמש מחובר
        if 'user_id' not in session:
            # אם יש צוות נבחר, העבר לדף כניסה
            if 'selected_team_id' in session:
                return redirect(url_for('login'))
            # אחרת, העבר לבחירת צוות
            return redirect(url_for('team_selection'))
        
        # בדוק אם יש צוות נבחר
        if 'team_id' not in session:
            return redirect(url_for('team_selection'))
        
        # בדוק אם מסד הנתונים קיים
        db_path = get_team_db_path()
        if not db_path:
            session.clear()
            return redirect(url_for('team_selection'))
        
        # בדוק אם הקובץ קיים - אם לא, זה בעיה אבל לא ננסה ליצור אותו כאן (זה יקח זמן)
        # במקום זה, נאפשר גישה ונסמוך על init_db שיקרא במקום אחר
        if not os.path.exists(db_path):
            # רק נוודא שהתיקייה קיימת
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            # אם הקובץ לא קיים, זה בעיה - אבל לא ננסה ליצור אותו כאן כדי לא לגרום timeout
            # במקום זה, נאפשר את הבקשה והקוד יטופל במקום אחר
            pass
        
        return f(*args, **kwargs)
    return decorated_function

# ניהול צוותים
team_manager = TeamManager()

@app.route('/', methods=['GET', 'POST'])
def team_selection():
    """דף בחירת צוות - הדף הראשי"""
    if request.method == 'POST':
        team_id = request.form.get('team_id')
        if team_id:
            session['selected_team_id'] = int(team_id)
            return redirect(url_for('login'))
    
    # קבל את כל הצוותים
    teams = team_manager.get_all_teams()

    # ביצועים: חישוב סטטיסטיקות לכל צוות (פתיחת כל מסדי הנתונים) עלול להאט מאוד במיוחד בדוקר
    # לכן כרגע לא נחשב סטטיסטיקות כאן, אלא נעביר מילון ריק או נחשב בעתיד בצורה אסינכרונית/על פי דרישה
    team_stats = {}

    return render_template('team_selection.html', teams=teams, team_stats=team_stats)

@app.route('/create_team', methods=['POST'])
def create_team():
    """יצירת צוות חדש"""
    team_name = request.form.get('team_name')
    admin_username = request.form.get('admin_username')
    admin_password = request.form.get('admin_password')
    creation_code = request.form.get('creation_code')
    
    if not all([team_name, admin_username, admin_password, creation_code]):
        # קבל צוותים (ללא סטטיסטיקות – לשיפור ביצועים)
        teams = team_manager.get_all_teams()
        team_stats = {}
        
        return render_template('team_selection.html', 
                             teams=teams,
                             team_stats=team_stats,
                             error='יש למלא את כל השדות כולל קוד יצירת צוות')
    
    # בדוק את קוד יצירת הצוות
    code_validation = team_manager.validate_team_creation_code(creation_code)
    if not code_validation['valid']:
        # קבל צוותים (ללא סטטיסטיקות – לשיפור ביצועים)
        teams = team_manager.get_all_teams()
        team_stats = {}
        
        return render_template('team_selection.html', 
                             teams=teams,
                             team_stats=team_stats,
                             error=code_validation['message'])
    
    # צור את הצוות החדש
    result = team_manager.create_team(team_name, admin_username, admin_password, creation_code)
    
    # קבל צוותים וסטטיסטיקות
    teams = team_manager.get_all_teams()
    team_stats = {}
    for team in teams:
        stats = team_manager.get_team_stats(team[0])
        if stats:
            team_stats[team[0]] = stats
    
    if result['success']:
        flash(f"🎉 צוות '{team_name}' נוצר בהצלחה! ניתן כעת להתחבר לצוות החדש.", 'success')
        return redirect(url_for('team_selection'))
    else:
        flash(result['message'], 'error')
        return redirect(url_for('team_selection'))

@app.route('/select_team', methods=['POST'])
def select_team():
    """בחירת צוות והעברה לדף כניסה"""
    team_id = request.form.get('team_id')
    if team_id:
        session['selected_team_id'] = int(team_id)
        return redirect(url_for('login'))
    return redirect(url_for('team_selection'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """דף כניסה לצוות ספציפי"""
    try:
        # בדוק אם נבחר צוות
        if 'selected_team_id' not in session:
            return redirect(url_for('team_selection'))
        
        team_id = session['selected_team_id']
        team = team_manager.get_team_by_id(team_id)
        
        if not team:
            session.pop('selected_team_id', None)
            return redirect(url_for('team_selection'))
    except Exception as e:
        print(f"Error in login route: {e}")
        session.clear()
        return redirect(url_for('team_selection'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            if not username or not password:
                return render_template('login.html', 
                                     error='יש למלא שם משתמש וסיסמה',
                                     team_name=team[1])
            
            user = team_manager.authenticate_user(team_id, username, password)
            if user:
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[2]
                session['team_id'] = team_id
                session['team_name'] = team[1]
                
                # ודא שמסד הנתונים קיים - אם לא, צור אותו (אבל לא נחכה יותר מדי)
                db_path = team_manager.get_team_db_path(team_id)
                if db_path and not os.path.exists(db_path):
                    try:
                        # צור את מסד הנתונים - זה כבר יוצר את כל הטבלאות הבסיסיות
                        team_manager.create_new_database(db_path)
                        # רק נוסיף עמודות חסרות אם צריך (זה מהיר יותר)
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        # בדוק והוסף עמודות חסרות לטבלת process_tags
                        c.execute("PRAGMA table_info(process_tags)")
                        columns = [col[1] for col in c.fetchall()]
                        missing_columns = {
                            'final_check_snapshot': 'TEXT'
                        }
                        for col_name, col_type in missing_columns.items():
                            if col_name not in columns:
                                try:
                                    c.execute(f"ALTER TABLE process_tags ADD COLUMN {col_name} {col_type}")
                                except:
                                    pass
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        print(f"Error creating database: {e}")
                        # גם אם יש שגיאה, נמשיך - אולי מסד הנתונים כבר קיים
                        pass
                
                # תיעוד התחברות
                try:
                    log_activity(user[0], user[1], team_id, "התחברות למערכת")
                except:
                    pass  # לא קריטי אם זה נכשל
                
                return redirect(url_for('main_index'))
            else:
                return render_template('login.html', 
                                     error='שם משתמש או סיסמה שגויים',
                                     team_name=team[1])
        except Exception as e:
            print(f"Error in login POST: {e}")
            return render_template('login.html', 
                                 error='אירעה שגיאה בהתחברות. אנא נסה שוב.',
                                 team_name=team[1] if team else '')
    
    return render_template('login.html', team_name=team[1])



@app.route('/logout')
def logout():
    """התנתקות וחזרה לבחירת צוות"""
    session.clear()
    return redirect(url_for('team_selection'))

# עמוד ראשי
@app.route('/index', methods=['GET', 'POST'])
@login_required
def main_index():
    if request.method == 'POST':
        action = request.form.get('action')
        qr_code = request.form.get('qr_code', '').strip()
        sku_input = request.form.get('sku', '').strip()
        
        qr_code = re.sub(r'[^\w\-]', '', qr_code)
        
        print(f"Action: {action}, QR Code: {qr_code}, SKU Input: {sku_input}")
        
        # בדוק אם הקלט הוא תיאור מק"ט
        sku = sku_input
        if sku_input:
            print(f"DEBUG: Validating SKU input: '{sku_input}' (type: {type(sku_input)})")
            print(f"DEBUG: Input length: {len(sku_input)}")
            print(f"DEBUG: Input bytes: {sku_input.encode()}")
            
            # בדוק אם זה קוד מק"ט קיים - בדיקה מדויקת
            db_path = get_team_db_path()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # בדוק מה יש במסד הנתונים לפני הבדיקה
            c.execute("SELECT sku_code, description FROM approved_skus WHERE is_active = 1 ORDER BY CAST(sku_code AS INTEGER)")
            all_skus = c.fetchall()
            print(f"DEBUG: All active SKUs in DB: {all_skus}")
            
            # בדוק אם יש רווחים או תווים מיוחדים
            c.execute("SELECT sku_code, LENGTH(sku_code), HEX(sku_code) FROM approved_skus WHERE is_active = 1")
            sku_details = c.fetchall()
            print(f"DEBUG: SKU details: {sku_details}")
            
            c.execute("SELECT sku_code FROM approved_skus WHERE sku_code = ? AND is_active = 1", (sku_input,))
            result = c.fetchone()
            if result:
                # זה קוד מק"ט תקין
                sku = sku_input
                print(f"DEBUG: Exact SKU match found: {sku_input}")
            else:
                print(f"DEBUG: No exact SKU match for: {sku_input}")
                # נסה למצוא מק"ט לפי תיאור - בדיקה מדויקת
                c.execute("SELECT sku_code FROM approved_skus WHERE description = ? AND is_active = 1", (sku_input,))
                result = c.fetchone()
                if result:
                    sku = result[0]
                    print(f"DEBUG: Found SKU {sku} for description: {sku_input}")
                else:
                    print(f"DEBUG: No description match for: {sku_input}")
                    conn.close()
                    return render_template('index.html', error=f"המק\"ט '{sku_input}' לא קיים במערכת", qr_code=qr_code, sku=sku_input, approved_skus=get_active_skus())
            conn.close()
        
        if action == 'search' and (not qr_code or not sku):
            error_msg = "שני השדות 'מספר סידורי' ו-'מקט' חייבים להיות מלאים לחיפוש!"
            return render_template('index.html', error=error_msg, qr_code=qr_code, sku=sku_input, approved_skus=get_active_skus())
        
        if not qr_code:
            return render_template('index.html', error="מספר סידורי לא תקף", qr_code=qr_code, sku=sku_input, approved_skus=get_active_skus())
        
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (qr_code, sku))
        product = c.fetchone()
        
        if not product:
            c.execute("INSERT OR IGNORE INTO products (serial_number, sku, date_added) VALUES (?, ?, datetime('now'))",
                      (qr_code, sku))
            conn.commit()
            conn.close()
            if action == 'search':
                return redirect(url_for('new_tag', serial_number=qr_code, sku=sku))
            else:
                return render_template('index.html', error="מוצר חדש נוצר, אנא השתמש ב'חיפוש מוצר' תחילה", qr_code=qr_code, sku=sku_input, approved_skus=get_active_skus())
        
        conn.close()
        if action == 'search':
            return redirect(url_for('product', serial_number=qr_code, sku=sku))
        else:
            return redirect(url_for('close_tag', serial_number=qr_code, sku=sku))
    
    approved_skus_list = get_active_skus()
    print(f"DEBUG: SKUs being passed to template: {approved_skus_list}")
    return render_template('index.html', error=None, qr_code=None, sku=None, approved_skus=approved_skus_list)

@app.route('/print_signature/<int:tag_id>')
def print_signature_on_image_route(tag_id):

    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # משוך את הנתונים של התג לפי tag_id
    c.execute("SELECT serial_number, sku FROM process_tags WHERE tag_id = ?", (tag_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        return "תג לא נמצא במערכת", 404

    serial_number, sku = result

    # קריאה לפונקציה שלך עם tag_id ספציפי
    print_signature_on_image(serial_number, sku, tag_id)

    return redirect(url_for('product', serial_number=serial_number, sku=sku))


@app.route('/generate_qr', methods=['GET', 'POST'])
@login_required
def generate_qr():
    qr_image = None
    if request.method == 'POST':
        serial_number = request.form['serial_number']
        sku = request.form['sku']
        qr_data = f"{serial_number}:{sku}"  # פורמט QR

        # יצירת QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        # המרת ה-QR לתמונה
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return render_template('generate_qr.html', qr_image=qr_image, approved_skus=get_active_skus())

# תצוגת מוצר
@app.route('/product/<serial_number>/<sku>')
@login_required
def product(serial_number, sku):
    # נקה הודעת הצלחה מהסשן אחרי הצגה
    success_message = session.pop('success_message', None)
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # URL decode את ה-SKU (אם הוא מגיע כ-URL encoded)
    sku = urllib.parse.unquote(sku)
    
    c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
    product = c.fetchone()
    if not product:
        # אם המוצר לא נמצא, נסה למצוא SKU מהתגים או products
        # אם SKU הוא "לא מוגדר", נסה למצוא SKU אחר מהתגים
        if sku == 'לא מוגדר':
            # נסה למצוא SKU מהתגים
            c.execute("SELECT DISTINCT sku FROM process_tags WHERE serial_number = ? AND sku IS NOT NULL AND sku != '' AND sku != '0' LIMIT 1", (serial_number,))
            tag_sku_row = c.fetchone()
            if tag_sku_row and tag_sku_row[0] not in (None, '', '0', 'לא מוגדר'):
                sku = tag_sku_row[0]
                c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
                product = c.fetchone()
            else:
                # נסה למצוא SKU מ-products
                c.execute("SELECT sku FROM products WHERE serial_number = ? LIMIT 1", (serial_number,))
                product_sku_row = c.fetchone()
                if product_sku_row and product_sku_row[0] not in (None, '', '0', 'לא מוגדר'):
                    sku = product_sku_row[0]
                    c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
                    product = c.fetchone()
        
        # אם עדיין לא נמצא, יצור מוצר עם SKU זה
        if not product:
            # בדוק אם יש תגים עם serial_number הזה
            c.execute("SELECT COUNT(*) FROM process_tags WHERE serial_number = ?", (serial_number,))
            tag_count = c.fetchone()[0]
            if tag_count > 0:
                # יש תגים, אז יצור את המוצר
                c.execute("INSERT OR IGNORE INTO products (serial_number, sku, date_added) VALUES (?, ?, datetime('now'))", 
                         (serial_number, sku))
                conn.commit()
                c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
                product = c.fetchone()
            else:
                # אין תגים, המוצר באמת לא קיים
                conn.close()
                return render_template('index.html', error="מוצר לא נמצא"), 404
    # הביא את כל התגים לפי serial_number (בלי תלות ב-SKU) כדי לשמור על ההיסטוריה
    # בדוק אילו עמודות קיימות
    c.execute("PRAGMA table_info(process_tags)")
    columns_info = c.fetchall()
    column_names = [col[1] for col in columns_info]
    
    # בנה רשימת עמודות לשליפה - רק עמודות קיימות
    base_columns = ['tag_id', 'serial_number', 'fault_description', 'actions_taken', 'status', 
                    'date_updated', 'is_closed', 'date_opened', 'test_results', 'performer']
    optional_columns = ['sku', 'checker', 'item_statuses', 'performer_signature', 'checker_signature', 'priority', 'final_check_snapshot']
    
    select_columns = base_columns.copy()
    for col in optional_columns:
        if col in column_names:
            select_columns.append(col)
    
    # אם sku לא קיים, הוסף אותו כ-NULL
    if 'sku' not in column_names:
        select_columns.append("NULL as sku")
    
    columns_str = ', '.join(select_columns)
    c.execute(f"""
        SELECT {columns_str}
        FROM process_tags 
        WHERE serial_number = ? 
        ORDER BY date_updated DESC
    """, (serial_number,))
    tags = c.fetchall()
    
    # מצא את המיקום של sku בתוצאות
    sku_index = select_columns.index('sku') if 'sku' in select_columns else (select_columns.index('NULL as sku') if 'NULL as sku' in select_columns else None)
    final_check_snapshot_index = select_columns.index('final_check_snapshot') if 'final_check_snapshot' in select_columns else None
    c.execute("SELECT * FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", 
              (serial_number, sku))
    open_tag = c.fetchone()

    
    # קבל רשימת SKUs מאושרים
    c.execute("SELECT sku_code, description FROM approved_skus WHERE is_active = 1 ORDER BY sku_code")
    approved_skus = c.fetchall()
    
    conn.close()
    return render_template('product.html', product=product, tags=tags, open_tag=open_tag, 
                         serial_number=serial_number, sku=sku, success_message=success_message, 
                         approved_skus=approved_skus, sku_column_index=sku_index, final_check_snapshot_index=final_check_snapshot_index)

# יצירת תג תהליך חדש
@app.route('/new_tag/<serial_number>/<sku>', methods=['GET', 'POST'])
@login_required
def new_tag(serial_number, sku):
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
    product = c.fetchone()
    if not product:
        conn.close()
        return "מוצר לא נמצא", 404
    
    # בדוק אם יש כבר תג פתוח עם אותו serial_number ו-sku
    c.execute("SELECT tag_id FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 LIMIT 1", (serial_number, sku))
    existing_open_tag = c.fetchone()
    if existing_open_tag:
        team_members = get_performers()
        check_members = get_checkers()
        conn.close()
        return render_template('new_tag.html', 
                             serial_number=serial_number, 
                             sku=sku, 
                             team_members=team_members, 
                             check_members=check_members,
                             test_descriptions=[
                                 "אריזה", "שלמות מכנית", "צביעה/חלודה", "בדיקת היסטוריית הפריט", 
                                 "הלחמות", "שלוט", "ניקיון", "ברגים דסקיות", "ניירת מלווה", "היעדר גופים זרים"
                             ],
                             error=f'קיים כבר תג פתוח (מזהה תג: {existing_open_tag[0]}) עבור מוצר זה. אנא סגור את התג הקיים לפני פתיחת תג חדש.',
                             issues=get_active_issues())
    
    team_members = get_performers()
    check_members = get_checkers()

    test_descriptions = [
        "אריזה", "שלמות מכנית", "צביעה/חלודה", "בדיקת היסטוריית הפריט", 
        "הלחמות", "שלוט", "ניקיון", "ברגים דסקיות", "ניירת מלווה", "היעדר גופים זרים"
    ]
    
    if request.method == 'POST':
        print("Form data received (raw):", request.form)  # ניפוי מלא של הנתונים
        issue_input = request.form.get('issue_input', '').strip()
        additional_description = request.form.get('fault_description', '').strip()
        
        # בדוק אם התקלה מאושרת
        if issue_input:
            c.execute("SELECT COUNT(*) FROM approved_issues WHERE description = ?", (issue_input,))
            issue_exists = c.fetchone()[0] > 0
            if not issue_exists:
                return render_template('new_tag.html', 
                                     serial_number=serial_number, 
                                     sku=sku, 
                                     team_members=team_members, 
                                     check_members=check_members,
                                     test_descriptions=test_descriptions, 
                                     error=f'תיאור התקלה "{issue_input}" לא קיים במערכת. אנא בחר תקלה מהרשימה או הוסף אותה בדף ניהול תקלות.',
                                     issues=get_active_issues())
        
        # צור תיאור תקלה מלא
        if additional_description:
            fault_description = issue_input + '\n' + additional_description
        else:
            fault_description = issue_input
            
        test_results = request.form.getlist('test_results[]')
        print("test_results - ", test_results)
        
        test_results_json = json.dumps(test_results) if test_results else json.dumps([])
        
        status = ''
        print("status - ", status)
        
        performer = request.form.get('performer', '').strip()
        print("Received performer:", performer)
        if not performer:
            error_msg = "חובה לבחור מבצע!"
            return render_template('new_tag.html', serial_number=serial_number, sku=sku, team_members=team_members, check_members=check_members,
                                 test_descriptions=test_descriptions, error=error_msg)
        
        # הבודק ייבחר בסגירת התג, לא בפתיחה
        
        item_statuses = request.form.getlist('item_statuses[]')
        item_statuses_json = json.dumps(item_statuses) if item_statuses else json.dumps([])
        print("Received item_statuses (from getlist):", item_statuses, "JSON:", item_statuses_json)  # ניפוי נוסף
        
        # בדיקה נוספת של הנתונים
        if not item_statuses:
            print("Warning: item_statuses is empty, no statuses selected")
        else:
            print("item_statuses values:", [s for s in item_statuses if s])  # הדפס ערכים לא ריקים
        
        # בדוק שוב לפני יצירת תג (למקרה של double-click או refresh)
        c.execute("SELECT tag_id FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 LIMIT 1", (serial_number, sku))
        existing_open_tag = c.fetchone()
        if existing_open_tag:
            conn.close()
            session['success_message'] = f'תג פתוח כבר קיים (מזהה תג: {existing_open_tag[0]})'
            return redirect(url_for('product', serial_number=serial_number, sku=sku))
        
        actions_taken = ""
        try:
            # בדוק אם העמודות קיימות, אם לא - הוסף אותם
            c.execute("PRAGMA table_info(process_tags)")
            columns = [col[1] for col in c.fetchall()]
            if 'test_results' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN test_results TEXT")
                print("Added test_results column to process_tags table")
            if 'performer' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN performer TEXT")
                print("Added performer column to process_tags table")
            if 'checker' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN checker TEXT")
                print("Added checker column to process_tags table")
            if 'item_statuses' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN item_statuses TEXT")
                print("Added item_statuses column to process_tags table")
            if 'sku' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN sku TEXT")
                print("Added sku column to process_tags table")
            if 'performer_signature' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN performer_signature TEXT")
                print("Added performer_signature column to process_tags table")
            if 'checker_signature' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN checker_signature TEXT")
                print("Added checker_signature column to process_tags table")
            if 'final_check_snapshot' not in columns:
                c.execute("ALTER TABLE process_tags ADD COLUMN final_check_snapshot TEXT")
                print("Added final_check_snapshot column to process_tags table")
            conn.commit()
            
            # בדיקת תוכן לפני השמירה
            print("Saving to DB - item_statuses_json:", item_statuses_json)
            
            # שליפת חתימת מבצע מתוך team_members
            performer_signature = None
            try:
                # חילוץ מספר אישי מתוך המחרוזת "שם (מספר)"
                def extract_id_number(label):
                    if not label:
                        return None
                    m = re.search(r"\((\d+)\)", label)
                    return m.group(1) if m else None
                performer_id = extract_id_number(performer)
                if performer_id:
                    c.execute("SELECT signature FROM team_members WHERE id_number = ?", (performer_id,))
                    row = c.fetchone()
                    performer_signature = row[0] if row else None
            except Exception as e:
                print("Warning: failed to fetch performer signature:", str(e))

            c.execute("INSERT INTO process_tags (serial_number, sku, fault_description, actions_taken, status, date_updated, date_opened, is_closed, test_results, performer, item_statuses, performer_signature) "
                      "VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), 0, ?, ?, ?, ?)",
                      (serial_number, sku, fault_description, actions_taken, status, test_results_json, performer, item_statuses_json, performer_signature))
            conn.commit()
            
            # אימות השמירה - בדיקת הרשומה שנוספה
            c.execute("SELECT item_statuses FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", (serial_number, sku))
            saved_item_statuses = c.fetchone()
            print("Verified saved item_statuses from DB:", saved_item_statuses[0] if saved_item_statuses else "None")
            
            print("Tag saved successfully with performer:", performer, "item_statuses:", item_statuses)
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f"שגיאה בשמירה: {str(e)}"
            print("SQL Error Details:", e.args)
            return render_template('new_tag.html', serial_number=serial_number, sku=sku, team_members=team_members, check_members=check_members,
                                 test_descriptions=test_descriptions, error=error_msg)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return render_template('new_tag.html', serial_number=serial_number, sku=sku, team_members=team_members, check_members=check_members,
                                 test_descriptions=test_descriptions, error="שגיאה בלתי צפויה: " + str(e))
        finally:
            conn.close()
        
        # הוסף הודעת הצלחה לסשן
        session['success_message'] = 'התג נפתח בהצלחה!'
        return redirect(url_for('product', serial_number=serial_number, sku=sku))
    
    # קבל רשימת תקלות מאושרות
    issues = get_active_issues()
    conn.close()
    return render_template('new_tag.html', serial_number=serial_number, sku=sku, team_members=team_members, check_members=check_members, test_descriptions=test_descriptions, issues=issues)

@app.route('/edit_tag/<int:tag_id>', methods=['GET', 'POST'])
@login_required
def edit_tag(tag_id):
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM process_tags WHERE tag_id = ? AND is_closed = 0", (tag_id,))
    tag = c.fetchone()
    if not tag:
        conn.close()
        return "תג לא נמצא או סגור", 404
    
    # שלוף את ה-sku מהתג - בדוק את כל המיקומים האפשריים
    sku = None
    # נסה לקבל את ה-SKU מהעמודה sku (אם קיימת)
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    sku_column_index = None
    if 'sku' in columns:
        try:
            sku_column_index = columns.index('sku')
            if len(tag) > sku_column_index:
                sku = tag[sku_column_index]
        except:
            pass
    
    # אם לא מצאנו, נסה לקבל מה-products
    if not sku or sku in (None, '', 0, '0'):
        c2 = conn.cursor()
        # נסה לקבל מ-products
        c2.execute("SELECT sku FROM products WHERE serial_number = ? LIMIT 1", (tag[1],))
        product_sku_row = c2.fetchone()
        if product_sku_row and product_sku_row[0] not in (None, '', 0, '0'):
            sku = product_sku_row[0]
        # אם עדיין לא מצאנו, נסה מהטבלה process_tags ישירות
        if not sku or sku in (None, '', 0, '0'):
            c2.execute("SELECT sku FROM process_tags WHERE tag_id = ?", (tag[0],))
            sku_row = c2.fetchone()
            if sku_row and sku_row[0] not in (None, '', 0, '0'):
                sku = sku_row[0]
    
    # אם עדיין אין SKU, השתמש בערך ברירת מחדל
    if not sku or sku in (None, '', 0, '0'):
        sku = 'לא מוגדר'
    
    # בדוק אם העמודה is_verified_fault קיימת, אם לא - הוסף אותה
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    if 'is_verified_fault' not in columns:
        c.execute("ALTER TABLE process_tags ADD COLUMN is_verified_fault TEXT")
        conn.commit()
        print("Added is_verified_fault column to process_tags table")
    
    if request.method == 'POST':
        fault_parts = tag[2].split('\n') if tag[2] else ['']
        main_issue = fault_parts[0]
        additional_description = request.form.get('additional_description', '').strip()
        if additional_description:
            fault_description = main_issue + '\n' + additional_description
        else:
            fault_description = main_issue
        actions_input = request.form.get('actions_taken', '').strip()  # היסטוריה קיימת
        new_action = request.form.get('new_action', '').strip()  # פעולה חדשה
        status = request.form.get('status', '')
        current_actions = tag[3].split('\n') if tag[3] else []
        current_actions = [action.strip() for action in current_actions if action.strip()]
        updated_actions = current_actions
        if new_action:
            current_time = datetime.now().strftime('%H:%M %d/%m/%Y')
            new_action_with_time = f"{current_time}: {new_action}"
            if new_action_with_time not in current_actions:
                updated_actions.append(new_action_with_time)
        is_verified_fault = "כן" if 'is_verified_fault' in request.form else "לא"
        print("Received is_verified_fault:", is_verified_fault)
        c.execute("UPDATE process_tags SET fault_description = ?, actions_taken = ?, status = ?, date_updated = datetime('now'), is_verified_fault = ? "
                  "WHERE tag_id = ?", (fault_description, '\n'.join(updated_actions), status, is_verified_fault, tag_id))
        conn.commit()
        
        # לפני ה-redirect, ודא שיש SKU תקין
        if not sku or sku in (None, '', 0, '0'):
            # נסה לקבל SKU מהמוצר
            c.execute("SELECT sku FROM products WHERE serial_number = ? LIMIT 1", (tag[1],))
            product_row = c.fetchone()
            if product_row and product_row[0] not in (None, '', 0, '0'):
                sku = product_row[0]
            else:
                sku = 'לא מוגדר'
        
        conn.close()
        session['success_message'] = 'התג עודכן בהצלחה!'
        return redirect(url_for('product', serial_number=tag[1], sku=sku))
    
    # שליפת is_verified_fault לטעינה בטופס עם שאילתה ישירה
    c.execute("SELECT is_verified_fault FROM process_tags WHERE tag_id = ? AND is_closed = 0", (tag_id,))
    is_verified_fault_row = c.fetchone()
    is_verified_fault = is_verified_fault_row[0] if is_verified_fault_row and is_verified_fault_row[0] and is_verified_fault_row[0].strip() else "לא"
    print("Loaded is_verified_fault from DB:", is_verified_fault)
    
    fault_parts = tag[2].split('\n') if tag[2] else ['']
    
    # בדוק אם העמודה manufacturer קיימת בטבלת spare_parts, אם לא - הוסף אותה
    c.execute("PRAGMA table_info(spare_parts)")
    spare_parts_columns = [col[1] for col in c.fetchall()]
    if 'manufacturer' not in spare_parts_columns:
        c.execute("ALTER TABLE spare_parts ADD COLUMN manufacturer TEXT")
        conn.commit()
        print("Added manufacturer column to spare_parts table")
    
    # קבל רשימת חלקי חילוף זמינים
    c.execute("SELECT part_id, part_number, description, manufacturer FROM spare_parts WHERE is_active = 1 ORDER BY part_number")
    spare_parts = c.fetchall()
    
    # קבל צריכת חלפים קיימת לתג זה
    c.execute("""SELECT spu.usage_id, sp.part_number, sp.description, sp.manufacturer, spu.serial_number, spu.date_used
                 FROM spare_parts_usage spu 
                 JOIN spare_parts sp ON spu.part_id = sp.part_id 
                 WHERE spu.tag_id = ? 
                 ORDER BY spu.date_used DESC""", (tag_id,))
    used_parts = c.fetchall()
    
    conn.close()
    return render_template('edit_tag.html', tag=tag, is_verified_fault=is_verified_fault, sku=sku, fault_parts=fault_parts, spare_parts=spare_parts, used_parts=used_parts)
# סגירת תג תהליך
@app.route('/close_tag/<serial_number>/<sku>', methods=['GET', 'POST'])
@login_required
def close_tag(serial_number, sku):
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # DEBUG: הדפסת כל sku_code במסד
    c.execute("SELECT sku_code FROM approved_skus")
    all_skus = [str(row[0]) for row in c.fetchall()]
    print(f"DEBUG: all sku_code in DB: {all_skus}")
    print(f"DEBUG: incoming sku: {sku} (type={type(sku)})")
    c.execute("SELECT final_check_image FROM approved_skus WHERE sku_code = ?", (str(sku),))
    final_check_image_row = c.fetchone()
    final_check_image = final_check_image_row[0] if final_check_image_row and final_check_image_row[0] else None
    print(f"DEBUG: final_check_image={final_check_image}")
    if final_check_image:
        file_path = os.path.join('static', 'final_checks', final_check_image)
        print(f"DEBUG: file_path={file_path}, exists={os.path.exists(file_path)}")
    c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, sku))
    product = c.fetchone()
    if not product:
        conn.close()
        return render_template('close_tag.html', error="לא נמצא מוצר עם מספר סידורי זה ומקט זה", serial_number=serial_number, sku=sku, final_check_image=final_check_image, check_members=[], final_check_snapshot=None)
    
    # בדוק אם יש תג פתוח
    c.execute("SELECT * FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", 
              (serial_number, sku))
    tag = c.fetchone()
    if not tag:
        # בדוק אם יש תג סגור עם אותו serial_number ו-sku
        c.execute("SELECT * FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 1 ORDER BY date_updated DESC LIMIT 1", 
                  (serial_number, sku))
        closed_tag = c.fetchone()
        if closed_tag:
            # התג כבר סגור - העבר חזרה למוצר עם הודעה
            conn.close()
            session['success_message'] = f'התג (מזהה: {closed_tag[0]}) כבר סגור'
            return redirect(url_for('product', serial_number=serial_number, sku=sku))
        else:
            # אין תג בכלל
            conn.close()
            return render_template('close_tag.html', error="אין תג פתוח לסגירה", serial_number=serial_number, sku=sku, final_check_image=final_check_image, check_members=[], final_check_snapshot=None)
    
    # שליפת test_results ו-item_statuses מהמסד נתונים עם טיפול בנתונים ריקים
    test_results = json.loads(tag[8]) if tag[8] and tag[8].strip() else []
    print("Loaded test_results from DB:", test_results)
    
    # שליפה ישירה של item_statuses מהשאילתה
    c.execute("SELECT item_statuses FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", (serial_number, sku))
    item_statuses_row = c.fetchone()
    item_statuses_json = item_statuses_row[0] if item_statuses_row and item_statuses_row[0] and item_statuses_row[0].strip() else "[]"
    try:
        item_statuses = json.loads(item_statuses_json)
    except json.JSONDecodeError:
        print("JSON Decode Error for item_statuses:", item_statuses_json)
        item_statuses = []
    print("Loaded item_statuses from DB (JSON):", item_statuses_json, "Parsed:", item_statuses)
    
    # בדוק אם העמודה is_verified_fault קיימת, אם לא - הוסף אותה
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    if 'is_verified_fault' not in columns:
        c.execute("ALTER TABLE process_tags ADD COLUMN is_verified_fault TEXT")
        conn.commit()
        print("Added is_verified_fault column to process_tags table")
    
    # שליפת is_verified_fault
    c.execute("SELECT is_verified_fault FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", (serial_number, sku))
    is_verified_fault_row = c.fetchone()
    is_verified_fault = is_verified_fault_row[0] if is_verified_fault_row and is_verified_fault_row[0] and is_verified_fault_row[0].strip() else "לא"
    print("Loaded is_verified_fault from DB:", is_verified_fault)
    
    # אימות נוסף של השליפה (לא חובה, אבל שומר על ניפוי)
    c.execute("SELECT item_statuses FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", (serial_number, sku))
    verified_item_statuses = c.fetchone()
    print("Verified item_statuses from DB query:", verified_item_statuses[0] if verified_item_statuses else "None")
    
    # ודא ש-item_statuses הוא רשימה תקינה
    if not isinstance(item_statuses, list):
        item_statuses = []
    
    # שליפת שם המבצע ובהודק מהעמודה 'performer' ו-'checker' עם טיפול בנתונים חסרים
    c.execute("SELECT performer, checker FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", 
              (serial_number, sku))
    performer_row = c.fetchone()
    performer = performer_row[0] if performer_row and performer_row[0] is not None else "לא זמין"
    checker = performer_row[1] if performer_row and performer_row[1] is not None else "לא זמין"
    
    # בדוק אם העמודה date_opened קיימת, אם לא - נסה לקבל אותה מ-date_updated (אם התג נפתח באותו יום)
    c.execute("PRAGMA table_info(process_tags)")
    columns = [col[1] for col in c.fetchall()]
    date_opened = ''
    
    if 'date_opened' in columns:
        # שליפת תאריך הפתיחה ישירות מהמסד נתונים
        c.execute("SELECT date_opened FROM process_tags WHERE serial_number = ? AND sku = ? AND is_closed = 0 ORDER BY date_updated DESC LIMIT 1", 
                  (serial_number, sku))
        date_opened_row = c.fetchone()
        if date_opened_row and date_opened_row[0] is not None:
            date_opened_val = str(date_opened_row[0]).strip()
            # בדוק שזה לא 'None' או empty
            date_opened = date_opened_val if date_opened_val and date_opened_val.lower() != 'none' else ''
        else:
            date_opened = ''
        print(f"DEBUG: date_opened column exists, retrieved: '{date_opened}' (raw: {date_opened_row[0] if date_opened_row else 'None'})")
    else:
        print("DEBUG: date_opened column does not exist in table")
    
    # אם לא מצאנו date_opened, נסה לקבל אותו מ-tag[4] או מ-date_updated (fallback)
    if not date_opened:
        if tag and len(tag) > 4:
            date_opened = tag[4] if tag[4] else ''
        
        # אם עדיין אין, נסה לקבל מ-date_updated (הנחה שהתג נפתח ביום הראשון שהיה לו date_updated)
        if not date_opened:
            c.execute("SELECT MIN(date_updated) FROM process_tags WHERE serial_number = ? AND sku = ?", 
                      (serial_number, sku))
            min_date_row = c.fetchone()
            if min_date_row and min_date_row[0]:
                date_opened = min_date_row[0]
                print(f"DEBUG: Using MIN(date_updated) as date_opened fallback: '{date_opened}'")
    
    print(f"DEBUG: Final date_opened: '{date_opened}' (type: {type(date_opened)})")

    final_check_snapshot = None
    if tag:
        try:
            c.execute("SELECT final_check_snapshot FROM process_tags WHERE tag_id = ?", (tag[0],))
            snapshot_row = c.fetchone()
            final_check_snapshot = snapshot_row[0] if snapshot_row and snapshot_row[0] else None
            print(f"DEBUG: final_check_snapshot for tag {tag[0]}: {final_check_snapshot}")
        except sqlite3.Error as snapshot_err:
            print(f"DEBUG: Failed to fetch final_check_snapshot for tag {tag[0]}: {snapshot_err}")
    
    # שליפת רשימת הבודקים - צריך לפני ה-POST כדי שיהיה זמין גם בשגיאות
    check_members = get_checkers()
    
    if request.method == 'POST':
        status = request.form.get('status', '').strip()
        if not status:
            error_msg = "חובה לבחור סטטוס סופי!"
            return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
        
        checker = request.form.get('checker', '').strip()
        if not checker:
            error_msg = "חובה לבחור בודק!"
            return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
        
        try:
            # שליפת חתימת הבודק
            checker_signature = None
            try:
                def extract_id_number(label):
                    if not label:
                        return None
                    m = re.search(r"\((\d+)\)", label)
                    return m.group(1) if m else None
                checker_id = extract_id_number(checker)
                if checker_id:
                    c.execute("SELECT signature FROM team_members WHERE id_number = ?", (checker_id,))
                    row = c.fetchone()
                    checker_signature = row[0] if row else None
            except Exception as e:
                print("Warning: failed to fetch checker signature:", str(e))
            
            # Retro close support: if a retro date was provided, use it instead of now()
            retro_date = request.form.get('retro_close_date')
            if retro_date:
                try:
                    dt_obj = datetime.strptime(retro_date, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    
                    print(f"DEBUG: Retro close requested. retro_date={retro_date}, dt_obj={dt_obj}, date_opened variable='{date_opened}'")
                    
                    # בדיקה שהתאריך לא עתידי
                    if dt_obj > today:
                        error_msg = "לא ניתן לסגור תג בתאריך עתידי. יש לבחור תאריך בעבר או היום."
                        print(f"DEBUG: Blocking - retro date is in the future")
                        return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
                    
                    # בדיקה שהתאריך לא לפני תאריך הפתיחה - חובה לבצע בדיקה זו
                    date_opened_parsed = None
                    
                    # אם date_opened עדיין ריק, נסה לקבל אותו מ-date_updated המינימלי של התג הזה
                    if not date_opened or (isinstance(date_opened, str) and not date_opened.strip()):
                        print(f"WARNING: date_opened is empty or None! Trying to get from MIN(date_updated)")
                        try:
                            # בדוק אם העמודה date_updated קיימת
                            c.execute("PRAGMA table_info(process_tags)")
                            columns = [col[1] for col in c.fetchall()]
                            if 'date_updated' in columns:
                                c.execute("SELECT MIN(date_updated) FROM process_tags WHERE serial_number = ? AND sku = ?", 
                                          (serial_number, sku))
                                min_date_row = c.fetchone()
                                if min_date_row and min_date_row[0]:
                                    date_opened = min_date_row[0]
                                    print(f"DEBUG: Got date_opened from MIN(date_updated): '{date_opened}'")
                            else:
                                print("WARNING: date_updated column does not exist either!")
                        except Exception as e:
                            print(f"ERROR: Failed to get MIN(date_updated): {e}")
                    
                    # אם עדיין אין תאריך פתיחה אחרי ה-fallback, נדלג על בדיקת תאריך הפתיחה (רק נבדוק תאריך עתידי)
                    skip_date_opened_check = False
                    if not date_opened or (isinstance(date_opened, str) and not date_opened.strip()):
                        print(f"WARNING: date_opened is still empty after all fallbacks! Allowing retro close without date_opened validation (only future date check)")
                        skip_date_opened_check = True
                        date_opened_parsed = None
                    else:
                        # יש תאריך פתיחה - ננסה לפרסר אותו
                        # המר ל-string אם צריך
                        if not isinstance(date_opened, str):
                            date_opened = str(date_opened) if date_opened else ''
                        
                        date_str = date_opened.strip() if date_opened else ''
                        print(f"DEBUG: date_opened (raw)='{date_opened}', date_str='{date_str}'")
                        
                        if len(date_str) >= 10:
                            # נסה פורמט YYYY-MM-DD HH:MM:SS (כפי ששמור ב-DB)
                            try:
                                if ' ' in date_str:
                                    date_opened_parsed = datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
                                else:
                                    date_opened_parsed = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                                print(f"DEBUG: Successfully parsed date_opened as YYYY-MM-DD: {date_opened_parsed}")
                            except ValueError as e1:
                                try:
                                    # נסה פורמט DD/MM/YYYY
                                    date_opened_parsed = datetime.strptime(date_str[:10], "%d/%m/%Y").date()
                                    print(f"DEBUG: Successfully parsed date_opened as DD/MM/YYYY: {date_opened_parsed}")
                                except ValueError as e2:
                                    try:
                                        # נסה פורמט DD-MM-YYYY
                                        date_opened_parsed = datetime.strptime(date_str[:10], "%d-%m-%Y").date()
                                        print(f"DEBUG: Successfully parsed date_opened as DD-MM-YYYY: {date_opened_parsed}")
                                    except ValueError as e3:
                                        print(f"ERROR: Could not parse date_opened '{date_opened}' in any format. Errors: {e1}, {e2}, {e3}")
                                        date_opened_parsed = None
                                        skip_date_opened_check = True
                        
                        # אם הצלחנו לפרסר - נבדוק את התאריך
                        if not skip_date_opened_check and date_opened_parsed:
                            print(f"DEBUG: Comparing dates: retro_date={dt_obj} ({type(dt_obj)}), date_opened={date_opened_parsed} ({type(date_opened_parsed)}), comparison={dt_obj < date_opened_parsed}")
                            if dt_obj < date_opened_parsed:
                                error_msg = f"לא ניתן לסגור תג בתאריך שקדם לפתיחתו. תאריך הפתיחה: {date_opened}. יש לבחור תאריך מ-{date_opened_parsed.strftime('%d/%m/%Y')} ואילך."
                                print(f"DEBUG: BLOCKING retro close - retro date {dt_obj} is BEFORE opened date {date_opened_parsed}")
                                return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
                            print(f"DEBUG: Retro date validation passed. dt_obj={dt_obj} is >= date_opened={date_opened_parsed}")
                        elif not skip_date_opened_check:
                            # לא הצלחנו לפרסר אבל יש ערך - נדלג על הבדיקה (זה DB ישן)
                            print(f"WARNING: Could not parse date_opened '{date_opened}', but allowing retro close (old DB)")
                    
                    # אם דילגנו על בדיקת תאריך הפתיחה, רק נוודא שעברנו את בדיקת התאריך העתידי
                    if skip_date_opened_check:
                        print(f"DEBUG: Skipped date_opened validation (old DB without date_opened). Only future date check was performed.")
                    
                    print(f"DEBUG: Retro date validation passed. dt_obj={dt_obj}")
                    retro_dt_str = dt_obj.strftime("%Y-%m-%d 14:10:00")
                except Exception as ex:
                    error_msg = "תאריך הסגירה לא תקין. יש לבחור תאריך תקני."
                    return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
                # If table has date_closed column, update it too
                c.execute('PRAGMA table_info(process_tags)')
                cols = [row[1] for row in c.fetchall()]
                if 'date_closed' in cols:
                    c.execute("UPDATE process_tags SET status = ?, checker = ?, checker_signature = ?, is_closed = 1, date_updated = ?, date_closed = ? WHERE tag_id = ?", (status, checker, checker_signature, retro_dt_str, retro_dt_str, tag[0]))
                else:
                    c.execute("UPDATE process_tags SET status = ?, checker = ?, checker_signature = ?, is_closed = 1, date_updated = ? WHERE tag_id = ?", (status, checker, checker_signature, retro_dt_str, tag[0]))
            else:
                c.execute("UPDATE process_tags SET status = ?, checker = ?, checker_signature = ?, is_closed = 1, date_updated = datetime('now') WHERE tag_id = ?", (status, checker, checker_signature, tag[0]))
            conn.commit()
            print("Tag closed successfully with checker:", checker)
        except sqlite3.Error as e:
            conn.rollback()
            error_msg = f"שגיאה בסגירה: {str(e)}"
            print("SQL Error Details:", e.args)
            return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=error_msg, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)
        finally:
            conn.close()
        return redirect(url_for('product', serial_number=serial_number, sku=sku))
    
    # check_members ו-date_opened כבר הוגדרו לפני ה-POST
    
    conn.close()
    return render_template('close_tag.html', tag=tag, serial_number=serial_number, sku=sku, error=None, test_results=test_results, performer=performer, checker=checker, item_statuses=item_statuses, is_verified_fault=is_verified_fault, final_check_image=final_check_image, check_members=check_members, date_opened=date_opened, final_check_snapshot=final_check_snapshot)

@app.route('/save_final_check_snapshot/<int:tag_id>', methods=['POST'])
@login_required
def save_final_check_snapshot(tag_id):
    db_path = get_team_db_path()
    if not db_path:
        return jsonify({'success': False, 'error': 'לא נמצא מסד נתונים פעיל לצוות.'}), 400

    payload = request.get_json(silent=True) or {}
    image_data = payload.get('image_data')
    if not image_data:
        return jsonify({'success': False, 'error': 'לא התקבלו נתוני תמונה לשמירה.'}), 400

    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]

    try:
        image_bytes = base64.b64decode(image_data)
    except (binascii.Error, ValueError) as decode_err:
        print(f"DEBUG: Failed to decode final check snapshot for tag {tag_id}: {decode_err}")
        return jsonify({'success': False, 'error': 'קובץ התמונה שנשלח אינו תקין.'}), 400

    filename = f'final_check_tag_{tag_id}.png'
    filepath = os.path.join(FINAL_CHECK_SNAPSHOTS_DIR, filename)

    try:
        with open(filepath, 'wb') as image_file:
            image_file.write(image_bytes)
    except OSError as file_err:
        print(f"DEBUG: Failed to write final check snapshot for tag {tag_id}: {file_err}")
        return jsonify({'success': False, 'error': 'נכשלה שמירת קובץ התמונה במערכת.'}), 500

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("PRAGMA table_info(process_tags)")
        columns = [col[1] for col in c.fetchall()]
        if 'final_check_snapshot' not in columns:
            c.execute("ALTER TABLE process_tags ADD COLUMN final_check_snapshot TEXT")
        c.execute("UPDATE process_tags SET final_check_snapshot = ? WHERE tag_id = ?", (filename, tag_id))
        if c.rowcount == 0:
            conn.close()
            try:
                os.remove(filepath)
            except OSError:
                pass
            return jsonify({'success': False, 'error': 'תג לא נמצא. לא ניתן לשמור את דף הבדיקות.'}), 404
        conn.commit()
    except sqlite3.Error as db_err:
        if conn:
            conn.rollback()
        print(f"DEBUG: Failed to update final_check_snapshot for tag {tag_id}: {db_err}")
        try:
            os.remove(filepath)
        except OSError:
            pass
        return jsonify({'success': False, 'error': 'שגיאה בעת עדכון התג במערכת.'}), 500
    finally:
        if conn:
            conn.close()

    public_url = url_for('static', filename=f'final_checks_snapshots/{filename}')
    return jsonify({'success': True, 'snapshot_url': public_url})

@app.route('/final_check_print/<int:tag_id>')
@login_required
def final_check_print_view(tag_id):
    db_path = get_team_db_path()
    if not db_path:
        return render_template('error.html', message="לא נמצא מסד נתונים פעיל לצוות."), 400

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT serial_number, sku, final_check_snapshot, is_closed FROM process_tags WHERE tag_id = ?", (tag_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return render_template('error.html', message="תג לא נמצא במערכת."), 404

    serial_number, sku, snapshot_filename, is_closed = row
    if not snapshot_filename:
        return render_template('error.html', message="לא נשמר דף בדיקות סופיות עבור תג זה."), 404

    snapshot_path = os.path.join(FINAL_CHECK_SNAPSHOTS_DIR, snapshot_filename)
    if not os.path.exists(snapshot_path):
        return render_template('error.html', message="קובץ הבדיקות הסופיות לא נמצא בשרת."), 404

    snapshot_url = url_for('static', filename=f'final_checks_snapshots/{snapshot_filename}')

    return render_template('final_check_print.html',
                           tag_id=tag_id,
                           serial_number=serial_number,
                           sku=sku,
                           snapshot_url=snapshot_url,
                           is_closed=is_closed)

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    sku_filter = request.form.get('sku', '').strip()
    tag_status = request.form.get('tag_status', 'all')

    query = """
        SELECT t.tag_id, t.serial_number, t.fault_description, t.status, 
               t.date_updated, t.is_closed, t.date_opened, t.sku AS product_sku
        FROM process_tags t 
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND t.date_opened >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.date_opened <= ?"
        params.append(end_date)
    if sku_filter:
        query += " AND t.sku = ?"
        params.append(sku_filter)
    if tag_status == 'open':
        query += " AND t.is_closed = 0"
    elif tag_status == 'closed':
        query += " AND t.is_closed = 1"

    query += " ORDER BY t.date_updated DESC"
    c.execute(query, params)
    tags = c.fetchall()

    # --- AI Insights Calculation ---
    from datetime import datetime, timedelta
    today = datetime.today()
    current_year = today.year
    current_month = today.month
    
    # חישוב החודש הנוכחי והקודם
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    
    month_names = ['','ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']
    current_month_name = month_names[current_month]
    prev_month_name = month_names[prev_month]
    
    # שלוף את כל התגים של החודש הנוכחי והקודם
    c.execute("SELECT fault_description, sku, date_opened FROM process_tags WHERE strftime('%Y', date_opened) = ? AND strftime('%m', date_opened) = ?", (str(current_year), f'{current_month:02d}'))
    tags_current_month = c.fetchall()
    c.execute("SELECT fault_description, sku, date_opened FROM process_tags WHERE strftime('%Y', date_opened) = ? AND strftime('%m', date_opened) = ?", (str(prev_year), f'{prev_month:02d}'))
    tags_prev_month = c.fetchall()

    # ספירת תקלות עיקריות
    def main_fault(desc):
        return desc.split('\n')[0].strip() if desc else 'לא ידוע'
    faults_current = Counter([main_fault(t[0]) for t in tags_current_month])
    faults_prev = Counter([main_fault(t[0]) for t in tags_prev_month])
    # ספירת מק"טים
    skus_current = Counter([t[1] for t in tags_current_month if t[1]])
    skus_prev = Counter([t[1] for t in tags_prev_month if t[1]])

    ai_insights = []
    temp_insights = []

    period_text = f'בחודש {current_month_name} לעומת {prev_month_name}'
    # תובנות תקלות - רק אם יש נתונים בשני החודשים (לפחות 2 בכל חודש)
    for fault in set(faults_current.keys()).intersection(faults_prev.keys()):
        count_now = faults_current.get(fault, 0)
        count_prev = faults_prev.get(fault, 0)
        if count_prev >= 2 and count_now >= 2:
            change = ((count_now - count_prev) / count_prev) * 100
            direction = 'עלייה' if change > 0 else 'ירידה'
            temp_insights.append({
                'type': 'fault_change',
                'value': abs(change),
                'text': f"{period_text}: חלה {direction} של {abs(int(change))}% בדיווחים על '{fault}' ({count_now} לעומת {count_prev})."
            })
    # תובנות מק"טים - רק אם יש נתונים בשני החודשים (לפחות 2 בכל חודש)
    for sku in set(skus_current.keys()).intersection(skus_prev.keys()):
        count_now = skus_current.get(sku, 0)
        count_prev = skus_prev.get(sku, 0)
        if count_prev >= 2 and count_now >= 2:
            change = ((count_now - count_prev) / count_prev) * 100
            direction = 'עלייה' if change > 0 else 'ירידה'
            temp_insights.append({
                'type': 'sku_change',
                'value': abs(change),
                'text': f"{period_text}: במק\"ט {sku} חלה {direction} של {abs(int(change))}% במספר התקלות ({count_now} לעומת {count_prev})."
            })
    # מיון לפי שינוי אחוזי/כמות והצגת לפחות תובנה אחת אם יש
    def insight_sort_key(insight):
        return (insight['value'],)
    temp_insights.sort(key=insight_sort_key, reverse=True)
    if temp_insights:
        ai_insights = [ins['text'] for ins in temp_insights[:3]]
        # תמיד הצג לפחות תובנה אחת
        if len(ai_insights) == 0:
            ai_insights = [temp_insights[0]['text']]
    else:
        ai_insights = []
    # --- END AI Insights ---

    # סיכום כולל
    total_open = sum(1 for tag in tags if tag[5] == 0)
    total_closed = sum(1 for tag in tags if tag[5] == 1)

    # ממוצע זמן טיפול כללי
    processing_times = []
    for tag in tags:
        if tag[5] == 1 and tag[6] and tag[4]:
            try:
                opened = datetime.strptime(tag[6], '%Y-%m-%d %H:%M:%S')
                updated = datetime.strptime(tag[4], '%Y-%m-%d %H:%M:%S')
                days = (updated - opened).days
                processing_times.append(days)
            except Exception:
                continue
    avg_processing_time = round(sum(processing_times) / len(processing_times), 2) if processing_times else 0

    # סיכום לפי מק"ט
    sku_summary = {}
    for tag in tags:
        sku = tag[7]
        if sku not in sku_summary:
            sku_summary[sku] = {'total': 0, 'open': 0, 'closed': 0, 'open_tags': {}}
        sku_summary[sku]['total'] += 1
        if tag[5] == 0:
            sku_summary[sku]['open'] += 1
            if tag[6]:
                try:
                    opened_date = datetime.strptime(tag[6], '%Y-%m-%d %H:%M:%S').date()
                    days_open = (date.today() - opened_date).days
                    sku_summary[sku]['open_tags'][tag[1]] = days_open
                except Exception:
                    continue
        else:
            sku_summary[sku]['closed'] += 1

    sku_summary_keys = sorted(sku_summary.keys(), key=lambda x: sku_summary[x]['total'], reverse=True)
    opened_counts = [sku_summary[sku]['total'] for sku in sku_summary_keys]
    closed_counts = [sku_summary[sku]['closed'] for sku in sku_summary_keys]

    # חישוב סטטוסים
    status_counts = {}
    for tag in tags:
        if tag[5] == 1:
            status = tag[3] if tag[3] else 'ללא סטטוס'
            status_counts[status] = status_counts.get(status, 0) + 1

    status_percentages = {status: (count / total_closed * 100) if total_closed > 0 else 0 
                         for status, count in status_counts.items()}

    # פילוח לפי חודשים - רק תגים פתוחים (is_closed = 0)
    time_grouping = {}
    current_year = date.today().year
    current_month = date.today().month
    for month in range(1, 13):
        time_grouping[f"{current_year}-{month:02d}"] = None
    c.execute("SELECT t.tag_id, t.date_opened, t.is_closed FROM process_tags t WHERE t.is_closed = 0")
    for tag in c.fetchall():
        if tag[1]:
            try:
                date_opened = datetime.strptime(tag[1], '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if date_opened.year == current_year and date_opened.month <= current_month:
                month_year = date_opened.strftime('%Y-%m')
                if time_grouping[month_year] is None:
                    time_grouping[month_year] = 0
                time_grouping[month_year] += 1

    time_labels = sorted(time_grouping.keys())
    time_data = [time_grouping[label] if time_grouping[label] is not None else None for label in time_labels]

    # --- חישוב ערכי חודש נוכחי וחודש קודם ---
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1
    month_names = ['','ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']
    current_month_name = month_names[current_month]
    prev_month_name = month_names[prev_month]

    # שלוף את כל התגים של החודש הנוכחי והקודם
    c.execute("SELECT tag_id, is_closed, date_opened, date_updated FROM process_tags WHERE strftime('%Y', date_opened) = ? AND strftime('%m', date_opened) = ?", (str(current_year), f'{current_month:02d}'))
    tags_current = c.fetchall()
    c.execute("SELECT tag_id, is_closed, date_opened, date_updated FROM process_tags WHERE strftime('%Y', date_opened) = ? AND strftime('%m', date_opened) = ?", (str(prev_year), f'{prev_month:02d}'))
    tags_prev = c.fetchall()

    # פתוחים/סגורים
    total_open_current = sum(1 for t in tags_current if t[1] == 0)
    total_closed_current = sum(1 for t in tags_current if t[1] == 1)
    total_open_prev = sum(1 for t in tags_prev if t[1] == 0)
    total_closed_prev = sum(1 for t in tags_prev if t[1] == 1)

    # ממוצע זמן טיפול
    proc_times_current = []
    for t in tags_current:
        if t[1] == 1 and t[2] and t[3]:
            try:
                opened = datetime.strptime(t[2], '%Y-%m-%d %H:%M:%S')
                updated = datetime.strptime(t[3], '%Y-%m-%d %H:%M:%S')
                days = (updated - opened).days
                proc_times_current.append(days)
            except Exception:
                continue
    avg_proc_time_current = round(sum(proc_times_current) / len(proc_times_current), 2) if proc_times_current else 0

    proc_times_prev = []
    for t in tags_prev:
        if t[1] == 1 and t[2] and t[3]:
            try:
                opened = datetime.strptime(t[2], '%Y-%m-%d %H:%M:%S')
                updated = datetime.strptime(t[3], '%Y-%m-%d %H:%M:%S')
                days = (updated - opened).days
                proc_times_prev.append(days)
            except Exception:
                continue
    avg_proc_time_prev = round(sum(proc_times_prev) / len(proc_times_prev), 2) if proc_times_prev else 0

    conn.close()
    return render_template('report.html',
                           tags=tags,
                           status_counts=status_counts,
                           status_percentages=status_percentages,
                           total_open=total_open,
                           total_closed=total_closed,
                           avg_processing_time=avg_processing_time,
                           sku_summary=sku_summary,
                           sku_summary_keys=sku_summary_keys,
                           opened_counts=opened_counts,
                           closed_counts=closed_counts,
                           time_labels=time_labels,
                           time_data=time_data,
                           start_date=start_date,
                           end_date=end_date,
                           sku=sku_filter,
                           tag_status=tag_status,
                           ai_insights=ai_insights,
                           total_open_current=total_open_current,
                           total_closed_current=total_closed_current,
                           avg_proc_time_current=avg_proc_time_current,
                           total_open_prev=total_open_prev,
                           total_closed_prev=total_closed_prev,
                           avg_proc_time_prev=avg_proc_time_prev,
                           current_month_name=current_month_name,
                           prev_month_name=prev_month_name,
                           current_year=current_year,
                           prev_year=prev_year)

@app.route('/open_tags', methods=['GET', 'POST'])
@login_required
def open_tags():
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    if request.method == 'POST':
        qr_code = request.form.get('qr_code', '').strip()
        qr_code = re.sub(r'[^\w\-]', '', qr_code)
        print(f"Search History QR Code: {qr_code}")
        
        # אם qr_code ריק לאחר איפוס, הצג את כל התגים הפתוחים
        if not qr_code:
            c.execute("SELECT t.tag_id, t.serial_number, t.fault_description, t.actions_taken, t.status, t.date_updated, t.is_closed, t.date_opened, t.test_results, t.performer, t.sku FROM process_tags t WHERE t.is_closed = 0 ORDER BY t.date_updated DESC")
            tags = c.fetchall()
        else:
            c.execute("SELECT * FROM products WHERE serial_number = ?", (qr_code,))
            product = c.fetchone()
            conn.close()
            if product:
                return redirect(url_for('product', serial_number=qr_code, sku=product[1]))
            return render_template('open_tags.html', error="מוצר לא נמצא", qr_code=qr_code, tags=[])
    
    else:  # GET request
        c.execute("SELECT t.tag_id, t.serial_number, t.fault_description, t.actions_taken, t.status, t.date_updated, t.is_closed, t.date_opened, t.test_results, t.performer, t.sku FROM process_tags t WHERE t.is_closed = 0 ORDER BY t.date_updated DESC")
        tags = c.fetchall()
    
    # עיבוד התגים ליצירת שדות נפרדים עבור מק"ט, תאריך וימים פתוחים
    formatted_tags = []
    for tag in tags:
        formatted_tag = list(tag)
        # טיפול במק"ט
        formatted_mkt = str(tag[10]) if tag[10] is not None else 'לא זמין'  # המרת המק"ט למחרוזת
        # טיפול בתאריך וימים פתוחים
        if tag[7] and isinstance(tag[7], str):  # בדיקה שתאריך פתיחה קיים והוא מחרוזת
            try:
                dt = datetime.strptime(tag[7], '%Y-%m-%d %H:%M:%S')  # תאריך פתיחה
                date_time = dt.strftime('%d/%m/%Y')  # תאריך מעוצב ללא שעה
                date_iso = dt.strftime('%Y-%m-%d')   # תאריך ISO למיון
                days_open = (date.today() - dt.date()).days  # חישוב ימים פתוחים
                days_open_sort = days_open if days_open >= 0 else -1  # ערך מספרי למיון
            except (ValueError, TypeError):
                date_time = 'לא זמין'
                date_iso = '9999-12-31'  # ערך ברירת מחדל למיון תאריכים
                days_open = 'לא זמין'
                days_open_sort = -1  # ערך ברירת מחדל למיון ימים פתוחים
        else:
            date_time = 'לא זמין'
            date_iso = '9999-12-31'  # ערך ברירת מחדל למיון תאריכים
            days_open = 'לא זמין'
            days_open_sort = -1  # ערך ברירת מחדל למיון ימים פתוחים
        formatted_tag.append(formatted_mkt)      # אינדקס 11
        formatted_tag.append(date_time)          # אינדקס 12
        formatted_tag.append(days_open)          # אינדקס 13
        formatted_tag.append(date_iso)           # אינדקס 14
        formatted_tag.append(days_open_sort)     # אינדקס 15
        formatted_tags.append(tuple(formatted_tag))
    
    c.execute("SELECT status, COUNT(*) FROM process_tags WHERE is_closed = 0 GROUP BY status")
    status_counts = dict(c.fetchall())
    total_open = len(formatted_tags)
    unique_devices = len(set(tag[1] for tag in formatted_tags))
    
    status_percentages = {}
    if total_open > 0:
        for status, count in status_counts.items():
            status_percentages[status] = (count / total_open * 100)
    
    conn.close()
    
    return render_template('open_tags.html', 
                         tags=formatted_tags,
                         status_counts=status_counts,
                         status_percentages=status_percentages,
                         total_open=total_open,
                         total_closed=0,
                         unique_devices=unique_devices,
                         start_date='',
                         end_date='',
                         sku='',
                         tag_status='open',
                         search_query='',
                         error=None,
                         qr_code=None)




@app.route('/export_open_tags_inventory_excel', methods=['GET'])
@login_required
def export_open_tags_inventory_excel():
    """ייצוא כקובץ Excel עם טבלה: עמודה לכל מק"ט, שורה ראשונה = מק"ט, שורות נוספות = מספרים סידוריים, שורה אחרונה = ספירה."""
    db_path = get_team_db_path()
    if not db_path:
        return make_response('Team database not found', 400)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """
        SELECT t.serial_number, t.sku
        FROM process_tags t
        WHERE t.is_closed = 0
        ORDER BY t.sku ASC, t.serial_number ASC
        """
    )
    rows = c.fetchall()
    conn.close()

    # ארגון הנתונים לפי SKU
    sku_to_serials = {}
    for serial, sku in rows:
        sku_str = str(sku) if sku is not None else 'לא מוגדר'
        sku_to_serials.setdefault(sku_str, []).append(str(serial))

    # יצירת קובץ Excel
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('ספירת מלאי')
    
    # הגדרת עיצובים
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4CAF50',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'font_size': 12
    })
    
    serial_format = workbook.add_format({
        'bg_color': '#e8f5e8',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'font_size': 11
    })
    
    count_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FF9800',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'font_size': 12
    })
    
    empty_format = workbook.add_format({
        'bg_color': '#f9f9f9',
        'font_color': '#999999',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    # כתיבת כותרת הדף
    worksheet.merge_range(0, 0, 0, len(sku_to_serials) - 1, 
                         f'📊 ספירת מלאי - תגי תהליך פתוחים - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                         workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'}))
    
    worksheet.merge_range(1, 0, 1, len(sku_to_serials) - 1, 
                         f'סה"כ תגים פתוחים: {len(rows)}',
                         workbook.add_format({'font_size': 12, 'align': 'center', 'italic': True}))
    
    skus = sorted(sku_to_serials.keys())
    max_serials = max((len(v) for v in sku_to_serials.values()), default=0)
    
    # כתיבת כותרות המק"ט (שורה 3)
    for col, sku in enumerate(skus):
        worksheet.write(3, col, f'מק"ט: {sku}', header_format)
        worksheet.set_column(col, col, 15)  # רוחב עמודה
    
    # כתיבת המספרים הסידוריים
    for row in range(max_serials):
        for col, sku in enumerate(skus):
            serials = sku_to_serials[sku]
            if row < len(serials):
                worksheet.write(4 + row, col, serials[row], serial_format)
            else:
                worksheet.write(4 + row, col, '-', empty_format)
    
    # כתיבת שורת הספירה
    count_row = 4 + max_serials
    for col, sku in enumerate(skus):
        count = len(sku_to_serials[sku])
        worksheet.write(count_row, col, f'סה"כ: {count}', count_format)
    
    # הוספת מידע נוסף בתחתית
    worksheet.write(count_row + 2, 0, 'קובץ נוצר אוטומטית על ידי מערכת ניהול תגי תהליך',
                   workbook.add_format({'italic': True, 'font_color': '#666666'}))
    
    workbook.close()
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=open_tags_inventory.xlsx'
    return response

@app.route('/save_priorities', methods=['POST'])
@login_required
def save_priorities():
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    data = request.get_json()
    for serial, is_urgent in data.items():
        c.execute("UPDATE process_tags SET is_urgent = ? WHERE serial_number = ?", (int(is_urgent), serial))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# Old backup system removed - using BackupManager instead

# Old team backup system removed - using BackupManager instead

def update_existing_tags_with_sku():
    """עדכן תגים קיימים עם ה-sku שלהם מהמוצר המתאים"""
    # עדכן את מסד הנתונים של הצוות הנוכחי
    db_path = get_team_db_path()
    if not db_path:
        return
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # בדוק אם יש תגים ללא sku
    c.execute("SELECT tag_id, serial_number FROM process_tags WHERE sku IS NULL OR sku = ''")
    tags_without_sku = c.fetchall()
    
    for tag_id, serial_number in tags_without_sku:
        # חפש את ה-sku מהמוצר
        c.execute("SELECT sku FROM products WHERE serial_number = ?", (serial_number,))
        sku_result = c.fetchone()
        if sku_result:
            sku = sku_result[0]
            c.execute("UPDATE process_tags SET sku = ? WHERE tag_id = ?", (sku, tag_id))
            print(f"Updated tag {tag_id} with SKU {sku}")
    
    conn.commit()
    conn.close()

@app.route('/manage_skus', methods=['GET', 'POST'])
def manage_skus():
    """דף ניהול המק"טים המאושרים"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            sku_code = request.form.get('sku_code', '').strip()
            description = request.form.get('description', '').strip()
            
            if not sku_code:
                return jsonify({'success': False, 'error': "קוד המק\"ט הוא שדה חובה"})
            
            try:
                c.execute("INSERT INTO approved_skus (sku_code, description) VALUES (?, ?)", (sku_code, description))
                conn.commit()
                
                # קבל את המידע של המק"ט החדש
                c.execute("SELECT sku_id, sku_code, description, final_check_image FROM approved_skus WHERE sku_code = ?", (sku_code,))
                new_sku = c.fetchone()
                
                conn.close()
                return jsonify({
                    'success': True,
                    'message': "המק\"ט נוסף בהצלחה",
                    'sku': {
                        'sku_id': new_sku[0],
                        'sku_code': new_sku[1],
                        'description': new_sku[2],
                        'final_check_image': new_sku[3]
                    }
                })
            except sqlite3.IntegrityError:
                conn.close()
                return jsonify({'success': False, 'error': "קוד המק\"ט כבר קיים במערכת"})
        
        elif action == 'update':
            sku_id = request.form.get('sku_id')
            sku_code = request.form.get('sku_code', '').strip()
            description = request.form.get('description', '').strip()
            is_active = 'is_active' in request.form
            
            if not sku_code:
                return render_template('approved_skus.html', error="קוד המק\"ט הוא שדה חובה", skus=get_all_skus_for_team())
            
            try:
                c.execute("UPDATE approved_skus SET sku_code = ?, description = ?, is_active = ? WHERE sku_id = ?", 
                          (sku_code, description, is_active, sku_id))
                conn.commit()
                conn.close()
                return render_template('approved_skus.html', message="המק\"ט עודכן בהצלחה", skus=get_all_skus_for_team())
            except sqlite3.IntegrityError:
                conn.close()
                return render_template('approved_skus.html', error="קוד המק\"ט כבר קיים במערכת", skus=get_all_skus_for_team())
        
        elif action == 'delete':
            sku_id = request.form.get('sku_id')
            
            # בדוק אם המק"ט בשימוש
            c.execute("SELECT sku_code FROM approved_skus WHERE sku_id = ?", (sku_id,))
            sku_code = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM products WHERE sku = ?", (sku_code,))
            if c.fetchone()[0] > 0:
                c.execute("SELECT serial_number FROM products WHERE sku = ? LIMIT 5", (sku_code,))
                products = c.fetchall()
                product_list = ", ".join([p[0] for p in products])
                error = f"לא ניתן למחוק מק\"ט {sku_code} - נמצא בשימוש במוצרים: {product_list}"
                conn.close()
                return jsonify({'success': False, 'error': error})
            else:
                c.execute("DELETE FROM approved_skus WHERE sku_id = ?", (sku_id,))
                conn.commit()
                conn.close()
                return jsonify({'success': True, 'message': "המק\"ט נמחק בהצלחה"})
    conn.close()
    skus = get_all_skus_for_team()
    return render_template('approved_skus.html', skus=skus)

def get_all_skus(cursor):
    """קבל את כל המק"טים המאושרים"""
    cursor.execute("SELECT sku_id, sku_code, description, is_active, date_created FROM approved_skus ORDER BY sku_code")
    return cursor.fetchall()

def get_all_skus_for_team():
    """קבל את כל המק"טים המאושרים לצוות הנוכחי"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT sku_id, sku_code, description, final_check_image FROM approved_skus ORDER BY sku_code")
    skus = c.fetchall()
    conn.close()
    return skus

def get_team_db_path():
    """מחזיר את נתיב מסד הנתונים של הצוות הנוכחי"""
    if 'team_id' in session:
        try:
            # צור instance חדש של TeamManager
            tm = TeamManager()
            db_path = tm.get_team_db_path(session['team_id'])
            if db_path and os.path.exists(db_path):
                return db_path
        except Exception as e:
            print(f"שגיאה בקבלת נתיב מסד נתונים: {e}")
    
    # אם אין צוות נבחר, החזר None
    return None

def get_active_skus():
    """קבל רק את המק"טים הפעילים"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT sku_code, description FROM approved_skus WHERE is_active = 1 ORDER BY CAST(sku_code AS INTEGER)")
    skus = c.fetchall()
    print(f"DEBUG: get_active_skus returned: {skus}")
    conn.close()
    return skus

def secure_filename(filename):
    filename = os.path.basename(filename)  # הסרת נתיב
    filename = re.sub(r'[^A-Za-z0-9_.-]', '_', filename)  # תווים לא חוקיים מוחלפים ב-_
    return filename

@app.route('/approved_skus', methods=['GET', 'POST'])
@login_required
def approved_skus():
    if session.get('role') != 'admin':
        return render_template('error.html', message='אין הרשאות לעמוד הזה, אנא תפנה לאחראי.')
    
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    message = None
    error = None
    upload_dir = os.path.join('static', 'final_checks')
    os.makedirs(upload_dir, exist_ok=True)

    if request.method == 'POST':
        print('POST /approved_skus', dict(request.form))
        print('FILES:', request.files)
        if 'final_check_image' in request.files and request.files['final_check_image'].filename:
            sku_id = request.form.get('sku_id')
            file = request.files.get('final_check_image')
            print('file:', file)
            print('file.filename:', getattr(file, 'filename', None))
            print('request.files.keys():', list(request.files.keys()))
            if file:
                print('file.filename:', file.filename)
            else:
                print('No file uploaded')
            if not file or file.filename == '':
                error = 'יש לבחור קובץ להעלאה'
            else:
                orig_filename = file.filename
                safe_filename = secure_filename(orig_filename)
                if not safe_filename:
                    ext = os.path.splitext(orig_filename)[1] or '.bin'
                    safe_filename = f'file{ext}'
                filename = f"sku_{sku_id}_final_{safe_filename}"
                print('Final filename to save:', filename)
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                c.execute("UPDATE approved_skus SET final_check_image=? WHERE sku_id=?", (filename, sku_id))
                conn.commit()
                message = 'קובץ בדיקות סופיות נשמר בהצלחה'
        elif 'delete_final_check' in request.form:
            sku_id = request.form.get('sku_id')
            c.execute("SELECT final_check_image FROM approved_skus WHERE sku_id=?", (sku_id,))
            row = c.fetchone()
            if row and row[0]:
                file_path = os.path.join(upload_dir, row[0])
                if os.path.exists(file_path):
                    os.remove(file_path)
                c.execute("UPDATE approved_skus SET final_check_image=NULL WHERE sku_id=?", (sku_id,))
                conn.commit()
                message = 'קובץ הבדיקות נמחק'
    c.execute("SELECT sku_id, sku_code, description, final_check_image FROM approved_skus ORDER BY sku_code")
    skus = c.fetchall()
    conn.close()
    return render_template('approved_skus.html', skus=skus, message=message, error=error)

@app.route('/team_members', methods=['GET', 'POST'])
@login_required
def team_members():
    if session.get('role') != 'admin':
        return render_template('error.html', message='אין הרשאות לעמוד הזה, אנא תפנה לאחראי.')
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    message = None
    error = None
    
    if request.method == 'POST':
        print("DEBUG: POST request received")
        print("DEBUG: form data:", dict(request.form))
        if 'add_member' in request.form:
            name = request.form.get('name', '').strip()
            id_number = request.form.get('id_number', '').strip()
            role = request.form.get('role', '').strip()
            signature = request.form.get('signature', '').strip()
            
            if not name or not id_number or not role:
                return jsonify({
                    'success': False,
                    'error': "יש למלא את כל השדות"
                })
            else:
                try:
                    c.execute("INSERT INTO team_members (name, id_number, role, signature) VALUES (?, ?, ?, ?)", (name, id_number, role, signature))
                    conn.commit()
                    
                    # קבל את המידע של העובד החדש
                    c.execute("SELECT member_id, name, id_number, role, signature FROM team_members WHERE id_number = ?", (id_number,))
                    new_member = c.fetchone()
                    
                    return jsonify({
                        'success': True,
                        'message': "העובד נוסף בהצלחה",
                        'member': {
                            'member_id': new_member[0],
                            'name': new_member[1],
                            'id_number': new_member[2],
                            'role': new_member[3],
                            'signature': new_member[4]
                        }
                    })
                except sqlite3.IntegrityError:
                    return jsonify({
                        'success': False,
                        'error': "מספר תעודת זהות כבר קיים במערכת"
                    })
        elif 'update_signature' in request.form:
            member_id = request.form.get('member_id')
            signature = request.form.get('signature', '').strip()
            
            if not member_id or not signature:
                return jsonify({
                    'success': False,
                    'error': "חסרים נתונים לעדכון"
                })
            
            try:
                print("[SIG][REQ] update_signature called | member_id=", member_id, " | signature_len=", len(signature))
                # עדכן חתימה בטבלת העובדים
                c.execute("UPDATE team_members SET signature = ? WHERE member_id = ?", (signature, member_id))
                conn.commit()

                # שלוף מספר אישי ושם העובד כדי לעדכן תגים פתוחים
                c.execute("SELECT id_number, name FROM team_members WHERE member_id = ?", (member_id,))
                row = c.fetchone()
                updated_performer_count = 0
                updated_checker_count = 0
                if row:
                    id_number, name = row[0], row[1]
                    print(f"[SIG][MEMBER] name='{name}' | id_number='{id_number}'")
                    # ודא שעמודות החתימה קיימות
                    c.execute("PRAGMA table_info(process_tags)")
                    cols_info = c.fetchall()
                    cols = [col[1] for col in cols_info]
                    print("[SIG][PRAGMA] process_tags columns:", cols)
                    if 'performer_signature' not in cols:
                        print("[SIG][MIGRATE] Adding performer_signature column")
                        c.execute("ALTER TABLE process_tags ADD COLUMN performer_signature TEXT")
                    if 'checker_signature' not in cols:
                        print("[SIG][MIGRATE] Adding checker_signature column")
                        c.execute("ALTER TABLE process_tags ADD COLUMN checker_signature TEXT")
                    conn.commit()

                    # עדכן חתימות בתגים פתוחים שבהם העובד הוא מבצע/בודק לפי הדפוס "שם (מספר)" או לפי שם
                    like_id = f"%({id_number})%"
                    like_name = f"%{name} (%"
                    print(f"[SIG][PATTERN] like_id='{like_id}' | like_name='{like_name}'")
                    # דוגמית לפני עדכון
                    c.execute("SELECT tag_id, performer, checker FROM process_tags WHERE is_closed = 0 AND (performer LIKE ? OR performer LIKE ?) LIMIT 5", (like_id, like_name))
                    sample_perf = c.fetchall()
                    c.execute("SELECT tag_id, performer, checker FROM process_tags WHERE is_closed = 0 AND (checker LIKE ? OR checker LIKE ?) LIMIT 5", (like_id, like_name))
                    sample_check = c.fetchall()
                    print("[SIG][MATCH] performer sample:", sample_perf)
                    print("[SIG][MATCH] checker   sample:", sample_check)
                    c.execute(
                        "UPDATE process_tags SET performer_signature = ?, date_updated = datetime('now') WHERE is_closed = 0 AND (performer LIKE ? OR performer LIKE ?)",
                        (signature, like_id, like_name)
                    )
                    updated_performer_count = c.rowcount if hasattr(c, 'rowcount') else 0
                    c.execute(
                        "UPDATE process_tags SET checker_signature = ?, date_updated = datetime('now') WHERE is_closed = 0 AND (checker LIKE ? OR checker LIKE ?)",
                        (signature, like_id, like_name)
                    )
                    updated_checker_count = c.rowcount if hasattr(c, 'rowcount') else 0
                    print(f"[SIG][UPDATED] performer_rows={updated_performer_count} | checker_rows={updated_checker_count}")
                    conn.commit()
                else:
                    print("[SIG][ERROR] member not found after update")
                # הרץ סנכרון כללי כדי לוודא תאימות גם על תגים שלא נתפסו בתבניות ה-LIKE
                totals = resync_all_open_tags_signatures()
                print(f"[RESYNC][TOTALS] performer={totals['performer']} | checker={totals['checker']}")
                
                return jsonify({
                    'success': True,
                    'message': "החתימה עודכנה בהצלחה",
                    'updated_open_tags_performer': updated_performer_count,
                    'updated_open_tags_checker': updated_checker_count
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f"שגיאה בעדכון החתימה: {str(e)}"
                })
        elif 'delete_member' in request.form:
            print("DEBUG: delete_member action received")
            member_id = request.form.get('member_id')
            print(f"DEBUG: member_id = {member_id}")
            
            # בדוק אם העובד בשימוש
            c.execute("SELECT name, id_number FROM team_members WHERE member_id = ?", (member_id,))
            result = c.fetchone()
            if not result:
                return jsonify({
                    'success': False,
                    'error': "עובד לא נמצא"
                })
            name, id_number = result
            print(f"DEBUG: name = {name}, id_number = {id_number}")
            
            # בדוק מה יש במסד הנתונים
            c.execute("SELECT performer, checker FROM process_tags WHERE is_closed = 0 LIMIT 5")
            sample_tags = c.fetchall()
            print(f"DEBUG: Sample tags in DB: {sample_tags}")
            
            # בדוק אם יש תגים פתוחים עם עובד זה
            # הערך נשמר בפורמט: "שם העובד (מספר תעודת זהות)"
            # השתמש ב-LIKE עם סוגריים כדי למצוא מספר תעודת זהות מדויק
            c.execute("SELECT COUNT(*) FROM process_tags WHERE (performer LIKE ? OR checker LIKE ?) AND is_closed = 0", 
                     (f"%({id_number})%", f"%({id_number})%"))
            open_tags_count = c.fetchone()[0]
            print(f"DEBUG: open_tags_count = {open_tags_count}")
            print(f"DEBUG: Searching for exact pattern: %({id_number})%")
            
            if open_tags_count > 0:
                return jsonify({
                    'success': False,
                    'error': f"לא ניתן למחוק עובד {name} - קיימים תגים פתוחים עם עובד זה"
                })
            else:
                c.execute("DELETE FROM team_members WHERE member_id = ?", (member_id,))
                conn.commit()
                print(f"DEBUG: Member {name} deleted successfully")
                return jsonify({
                    'success': True,
                    'message': f"העובד {name} נמחק בהצלחה"
                })
    
    c.execute("SELECT member_id, name, id_number, role, signature FROM team_members ORDER BY name")
    members = c.fetchall()
    conn.close()
    return render_template('team_members.html', members=members, message=message, error=error)

@app.route('/spare_parts', methods=['GET', 'POST'])
@login_required
def spare_parts():
    """ניהול חלקי חילוף"""
    if session.get('role') != 'admin':
        return render_template('error.html', message='אין הרשאות לעמוד הזה, אנא תפנה לאחראי.')
    
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    message = None
    error = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            part_number = request.form.get('part_number', '').strip()
            description = request.form.get('description', '').strip()
            manufacturer = request.form.get('manufacturer', '').strip()
            
            if not part_number:
                return jsonify({'success': False, 'error': 'מספר חלק הוא שדה חובה'})
            
            try:
                c.execute("INSERT INTO spare_parts (part_number, description, manufacturer) VALUES (?, ?, ?)", 
                         (part_number, description, manufacturer))
                conn.commit()
                
                # קבל את החלק החדש שנוסף
                c.execute("SELECT part_id, part_number, description, manufacturer FROM spare_parts WHERE part_number = ?", (part_number,))
                new_part = c.fetchone()
                
                conn.close()
                return jsonify({
                    'success': True,
                    'message': 'חלק החילוף נוסף בהצלחה',
                    'part': {
                        'part_id': new_part[0],
                        'part_number': new_part[1],
                        'description': new_part[2],
                        'manufacturer': new_part[3]
                    }
                })
            except sqlite3.IntegrityError:
                conn.close()
                return jsonify({'success': False, 'error': 'מספר החלק כבר קיים במערכת'})
        
        elif action == 'delete':
            part_id = request.form.get('part_id')
            
            # קבל את מספר החלק לפני המחיקה
            c.execute("SELECT part_number FROM spare_parts WHERE part_id = ?", (part_id,))
            part_row = c.fetchone()
            if not part_row:
                conn.close()
                return jsonify({'success': False, 'error': 'חלק לא נמצא'})
            
            part_number = part_row[0]
            
            # מחק את החלק
            c.execute("DELETE FROM spare_parts WHERE part_id = ?", (part_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': f'חלק החילוף {part_number} נמחק בהצלחה'})
    
    # קבל את כל חלקי החילוף
    c.execute("SELECT part_id, part_number, description, manufacturer FROM spare_parts WHERE is_active = 1 ORDER BY part_number")
    parts = c.fetchall()
    conn.close()
    return render_template('spare_parts.html', parts=parts, message=message, error=error)

@app.route('/add_spare_usage', methods=['POST'])
@login_required
def add_spare_usage():
    """הוספת צריכת חלק חילוף לתג"""
    try:
        data = request.get_json()
        tag_id = data.get('tag_id')
        part_id = data.get('part_id')
        serial_number = data.get('serial_number', '').strip()
        
        if not all([tag_id, part_id, serial_number]):
            return jsonify({'success': False, 'error': 'יש למלא את כל השדות'})
        
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # בדוק שהתג קיים ופתוח
        c.execute("SELECT tag_id FROM process_tags WHERE tag_id = ? AND is_closed = 0", (tag_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'תג לא נמצא או סגור'})
        
        # בדוק שחלק החילוף קיים
        c.execute("SELECT part_number, description, manufacturer FROM spare_parts WHERE part_id = ? AND is_active = 1", (part_id,))
        part_info = c.fetchone()
        if not part_info:
            conn.close()
            return jsonify({'success': False, 'error': 'חלק חילוף לא נמצא'})
        
        # הוסף את הצריכה
        c.execute("INSERT INTO spare_parts_usage (tag_id, part_id, serial_number) VALUES (?, ?, ?)", 
                 (tag_id, part_id, serial_number))
        conn.commit()
        
        # קבל את הרשומה החדשה
        usage_id = c.lastrowid
        c.execute("SELECT date_used FROM spare_parts_usage WHERE usage_id = ?", (usage_id,))
        date_used = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'חלק החילוף {part_info[0]} נוסף בהצלחה',
            'usage': {
                'usage_id': usage_id,
                'part_number': part_info[0],
                'description': part_info[1] or '',
                'manufacturer': part_info[2] or '',
                'serial_number': serial_number,
                'date_used': date_used
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'שגיאה: {str(e)}'})

@app.route('/delete_spare_usage', methods=['POST'])
@login_required
def delete_spare_usage():
    """מחיקת צריכת חלק חילוף"""
    try:
        data = request.get_json()
        usage_id = data.get('usage_id')
        
        if not usage_id:
            return jsonify({'success': False, 'error': 'מזהה צריכה חסר'})
        
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # קבל פרטי הצריכה לפני המחיקה
        c.execute("""SELECT sp.part_number, spu.serial_number 
                     FROM spare_parts_usage spu 
                     JOIN spare_parts sp ON spu.part_id = sp.part_id 
                     WHERE spu.usage_id = ?""", (usage_id,))
        usage_info = c.fetchone()
        
        if not usage_info:
            conn.close()
            return jsonify({'success': False, 'error': 'צריכה לא נמצאה'})
        
        # מחק את הצריכה
        c.execute("DELETE FROM spare_parts_usage WHERE usage_id = ?", (usage_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'צריכת חלק {usage_info[0]} (ס"ד: {usage_info[1]}) נמחקה בהצלחה'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'שגיאה: {str(e)}'})

@app.route('/change_product_sku', methods=['POST'])
def change_product_sku():
    """שינוי SKU של מוצר ספציפי"""
    print("=== change_product_sku endpoint called ===")
    try:
        data = request.get_json()
        print("Received data:", data)
        
        serial_number = data.get('serial_number')
        current_sku = data.get('current_sku')
        new_sku = data.get('new_sku')
        
        print(f"Serial: {serial_number}, Current SKU: {current_sku}, New SKU: {new_sku}")
        
        if not all([serial_number, current_sku, new_sku]):
            print("Missing required data")
            return jsonify({
                'success': False,
                'error': 'חסרים פרטים נדרשים'
            })
        
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        try:
            # בדוק אם ה-SKU החדש מאושר
            c.execute("SELECT sku_code FROM approved_skus WHERE sku_code = ? AND is_active = 1", (new_sku,))
            if not c.fetchone():
                print("New SKU not approved")
                return jsonify({
                    'success': False,
                    'error': 'המק"ט החדש לא מאושר במערכת'
                })
            
            print("New SKU is approved")
            
            # בדוק אם המוצר קיים
            c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, current_sku))
            if not c.fetchone():
                print("Product not found")
                return jsonify({
                    'success': False,
                    'error': 'המוצר לא נמצא'
                })
            
            print("Product found")
            
            # בדוק אם יש מוצר עם אותו SKU חדש
            c.execute("SELECT * FROM products WHERE serial_number = ? AND sku = ?", (serial_number, new_sku))
            if c.fetchone():
                print("Product with new SKU already exists")
                return jsonify({
                    'success': False,
                    'error': 'כבר קיים מוצר עם המק"ט החדש'
                })
            
            print("No conflict with new SKU")
            
            # עדכן את ה-SKU במוצר
            c.execute("UPDATE products SET sku = ? WHERE serial_number = ? AND sku = ?", 
                     (new_sku, serial_number, current_sku))
            
            # עדכן את ה-SKU בכל התגים (פתוחים וסגורים) כדי לשמור על ההיסטוריה
            c.execute("UPDATE process_tags SET sku = ? WHERE serial_number = ? AND sku = ?", 
                     (new_sku, serial_number, current_sku))
            
            conn.commit()
            print("Database updated successfully")
            
            response_data = {
                'success': True,
                'message': f'המק"ט שונה בהצלחה מ-{current_sku} ל-{new_sku}'
            }
            print("Returning success response:", response_data)
            
            # הוסף הודעת הצלחה ל-session כדי להציג אותה בדף המוצר
            session['success_message'] = response_data['message']
            
            return jsonify(response_data)
            
        except sqlite3.Error as e:
            conn.rollback()
            print(f"SQL Error: {e}")
            return jsonify({
                'success': False,
                'error': f'שגיאה במסד הנתונים: {str(e)}'
            })
        finally:
            conn.close()
        
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({
            'success': False,
            'error': f'שגיאה בשינוי המק"ט: {str(e)}'
        })

@app.route('/approved_issues', methods=['GET', 'POST'])
@login_required
def approved_issues():
    if session.get('role') != 'admin':
        return render_template('error.html', message='אין הרשאות לעמוד הזה, אנא תפנה לאחראי.')
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    message = None
    error = None
    
    if request.method == 'POST':
        print("DEBUG: POST request received")
        print("DEBUG: form data:", dict(request.form))
        if 'add_issue' in request.form:
            description = request.form.get('description', '').strip()
            if not description:
                return jsonify({
                    'success': False,
                    'error': "יש להזין תיאור תקלה"
                })
            else:
                try:
                    # צור קוד תקלה אוטומטי
                    c.execute("SELECT MAX(CAST(issue_code AS INTEGER)) FROM approved_issues WHERE issue_code GLOB '[0-9]*'")
                    max_code = c.fetchone()[0]
                    new_code = str((max_code or 0) + 1).zfill(3)
                    
                    solution = request.form.get('solution', '').strip()
                    c.execute("INSERT INTO approved_issues (issue_code, description, solution) VALUES (?, ?, ?)", (new_code, description, solution))
                    conn.commit()
                    
                    # קבל את המידע של התקלה החדשה
                    c.execute("SELECT issue_id, issue_code, description, solution FROM approved_issues WHERE issue_code = ?", (new_code,))
                    new_issue = c.fetchone()
                    
                    return jsonify({
                        'success': True,
                        'message': "התקלה נוספה בהצלחה",
                        'issue': {
                            'issue_id': new_issue[0],
                            'issue_code': new_issue[1],
                            'description': new_issue[2],
                            'solution': new_issue[3]
                        }
                    })
                except sqlite3.IntegrityError:
                    return jsonify({
                        'success': False,
                        'error': "התקלה כבר קיימת"
                    })
        elif 'delete_issue' in request.form:
            print("DEBUG: delete_issue action received")
            issue_id = request.form.get('issue_id')
            print(f"DEBUG: issue_id = {issue_id}")
            
            # בדוק אם התקלה בשימוש
            c.execute("SELECT issue_code FROM approved_issues WHERE issue_id = ?", (issue_id,))
            result = c.fetchone()
            if not result:
                return jsonify({
                    'success': False,
                    'error': "תקלה לא נמצאה"
                })
            issue_code = result[0]
            print(f"DEBUG: issue_code = {issue_code}")
            
            # בדוק אם יש תגים פתוחים עם תקלה זו
            c.execute("SELECT COUNT(*) FROM process_tags WHERE fault_description LIKE ? AND is_closed = 0", (f"%{issue_code}%",))
            open_tags_count = c.fetchone()[0]
            print(f"DEBUG: open_tags_count = {open_tags_count}")
            
            if open_tags_count > 0:
                return jsonify({
                    'success': False,
                    'error': f"לא ניתן למחוק תקלה {issue_code} - קיימים תגים פתוחים עם תקלה זו"
                })
            else:
                c.execute("DELETE FROM approved_issues WHERE issue_id = ?", (issue_id,))
                conn.commit()
                print(f"DEBUG: Issue {issue_code} deleted successfully")
                return jsonify({
                    'success': True,
                    'message': f"התקלה נמחקה בהצלחה"
                })
        elif 'edit_solution' in request.form:
            issue_id = request.form.get('issue_id')
            solution = request.form.get('solution', '').strip()
            
            if not issue_id:
                return jsonify({
                    'success': False,
                    'error': "לא נמצא מזהה תקלה"
                })
            
            try:
                c.execute("UPDATE approved_issues SET solution = ? WHERE issue_id = ?", (solution, issue_id))
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': "הפתרון נשמר בהצלחה"
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f"שגיאה בשמירת הפתרון: {str(e)}"
                })
    c.execute("SELECT issue_id, issue_code, description, solution FROM approved_issues ORDER BY description")
    issues = c.fetchall()
    conn.close()
    return render_template('approved_issues.html', issues=issues, message=message, error=error)

def get_active_issues():
    """קבל רק את התקלות הפעילות"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT issue_code, description FROM approved_issues WHERE is_active = 1 ORDER BY description")
    issues = [(row[0], row[1]) for row in c.fetchall()]
    conn.close()
    return issues

def resync_all_open_tags_signatures():
    """סנכרון כל התגים הפתוחים לחתימות העדכניות מטבלת team_members"""
    try:
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # ודא עמודות
        c.execute("PRAGMA table_info(process_tags)")
        cols = [col[1] for col in c.fetchall()]
        if 'performer_signature' not in cols:
            c.execute("ALTER TABLE process_tags ADD COLUMN performer_signature TEXT")
        if 'checker_signature' not in cols:
            c.execute("ALTER TABLE process_tags ADD COLUMN checker_signature TEXT")
        conn.commit()

        # הבא את כל התגים הפתוחים
        c.execute("SELECT tag_id, performer, checker FROM process_tags WHERE is_closed = 0")
        tags = c.fetchall()
        updated_performer = 0
        updated_checker = 0

        for tag_id, performer, checker in tags:
            # חלץ מספר אישי
            perf_id = None
            check_id = None
            try:
                m = re.search(r"\((\d+)\)", performer or '')
                perf_id = m.group(1) if m else None
            except Exception:
                pass
            try:
                m = re.search(r"\((\d+)\)", checker or '')
                check_id = m.group(1) if m else None
            except Exception:
                pass

            # שלוף חתימות עדכניות
            perf_sig = None
            check_sig = None
            if perf_id:
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (perf_id,))
                row = c.fetchone()
                perf_sig = row[0] if row else None
            if check_id:
                c.execute("SELECT signature FROM team_members WHERE id_number = ?", (check_id,))
                row = c.fetchone()
                check_sig = row[0] if row else None

            # עדכן
            if perf_sig is not None:
                c.execute("UPDATE process_tags SET performer_signature = ?, date_updated = datetime('now') WHERE tag_id = ?", (perf_sig, tag_id))
                updated_performer += c.rowcount if hasattr(c, 'rowcount') else 0
            if check_sig is not None:
                c.execute("UPDATE process_tags SET checker_signature = ?, date_updated = datetime('now') WHERE tag_id = ?", (check_sig, tag_id))
                updated_checker += c.rowcount if hasattr(c, 'rowcount') else 0

        conn.commit()
        conn.close()
        return {"performer": updated_performer, "checker": updated_checker}
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        print("[RESYNC][ERROR]", str(e))
        return {"performer": 0, "checker": 0}

def get_team_members():
    """קבל את כל עובדי הצוות הפעילים"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, id_number, role, signature FROM team_members WHERE is_active = 1 ORDER BY name")
    members = [{"name": row[0], "id_number": row[1], "role": row[2]} for row in c.fetchall()]
    conn.close()
    return members

def get_performers():
    """קבל רק את המבצעים (performer או both)"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, id_number, signature FROM team_members WHERE is_active = 1 AND (role = 'performer' OR role = 'both') ORDER BY name")
    performers = [{"name": row[0], "id_number": row[1]} for row in c.fetchall()]
    conn.close()
    return performers

def get_checkers():
    """קבל רק את הבודקים (checker או both)"""
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, id_number, signature FROM team_members WHERE is_active = 1 AND (role = 'checker' OR role = 'both') ORDER BY name")
    checkers = [{"name": row[0], "id_number": row[1]} for row in c.fetchall()]
    conn.close()
    return checkers

@app.route('/get_solution', methods=['POST'])
def get_solution():
    """קבל פתרון לתקלה לפי תיאור התקלה"""
    try:
        data = request.get_json()
        fault_description = data.get('fault_description', '')
        
        if not fault_description:
            return jsonify({'success': False, 'error': 'לא הועבר תיאור תקלה'})
        
        db_path = get_team_db_path()
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # קבל את כל התקלות המאושרות
        c.execute("SELECT issue_code, description, solution FROM approved_issues WHERE is_active = 1")
        issues = c.fetchall()
        
        solution = None
        for issue_code, description, issue_solution in issues:
            # בדוק אם קוד התקלה או התיאור מופיעים בתיאור התקלה המורחב
            if (issue_code in fault_description) or (description and description in fault_description):
                if issue_solution:
                    solution = issue_solution
                break
        
        conn.close()
        
        if solution:
            return jsonify({'success': True, 'solution': solution})
        else:
            return jsonify({'success': False, 'solution': None})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/more_report', methods=['GET', 'POST'])
@login_required
def more_report():
    import sqlite3
    from datetime import datetime, date
    from collections import OrderedDict
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    sku_filter = request.form.get('sku', '').strip()

    query = """
        SELECT t.tag_id, t.serial_number, t.fault_description, t.status, 
               t.date_updated, t.is_closed, t.date_opened, t.sku AS product_sku
        FROM process_tags t 
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND t.date_opened >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.date_opened <= ?"
        params.append(end_date)
    if sku_filter:
        query += " AND t.sku = ?"
        params.append(sku_filter)
    query += " ORDER BY t.date_updated DESC"
    c.execute(query, params)
    tags = c.fetchall()

        # סיכום כללי
    total_opened = len(tags)  # כל התגים שנפתחו בטווח הסינון
    total_closed = 0
    total_in_progress = 0
    for tag in tags:
        if tag[5] == 1:
            total_closed += 1
        else:
            total_in_progress += 1
            
    # פילוח סטטוסים
    status_counts = {}
    total_closed = 0
    for tag in tags:
        if tag[5] == 1:
            status = tag[3] if tag[3] else 'ללא סטטוס'
            status_counts[status] = status_counts.get(status, 0) + 1
            total_closed += 1
    status_percentages = {status: (count / total_closed * 100) if total_closed > 0 else 0 for status, count in status_counts.items()}

    # סיכום לפי מק"ט
    sku_summary = {}
    for tag in tags:
        sku = tag[7]
        if sku not in sku_summary:
            sku_summary[sku] = {'total': 0, 'open': 0, 'closed': 0, 'open_tags': {}}
        sku_summary[sku]['total'] += 1
        if tag[5] == 0:
            sku_summary[sku]['open'] += 1
            if tag[6]:
                try:
                    opened_date = datetime.strptime(tag[6], '%Y-%m-%d %H:%M:%S').date()
                    days_open = (date.today() - opened_date).days
                    sku_summary[sku]['open_tags'][tag[1]] = days_open
                except Exception:
                    continue
        else:
            sku_summary[sku]['closed'] += 1
    sku_summary_keys = sorted(sku_summary.keys(), key=lambda x: sku_summary[x]['total'], reverse=True)
    opened_counts = [sku_summary[sku]['total'] for sku in sku_summary_keys]
    closed_counts = [sku_summary[sku]['closed'] for sku in sku_summary_keys]

    # פילוח לפי חודשים (לגרפים, אם צריך)
    time_grouping = OrderedDict()
    current_year = date.today().year
    current_month = date.today().month
    for month in range(1, 13):
        time_grouping[f"{current_year}-{month:02d}"] = None
    c.execute("SELECT t.tag_id, t.date_opened FROM process_tags t")
    for tag in c.fetchall():
        if tag[1]:
            try:
                date_opened = datetime.strptime(tag[1], '%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
            if date_opened.year == current_year and date_opened.month <= current_month:
                month_year = date_opened.strftime('%Y-%m')
                if time_grouping[month_year] is None:
                    time_grouping[month_year] = 0
                time_grouping[month_year] += 1
    time_labels = sorted(time_grouping.keys())
    time_data = [time_grouping[label] if time_grouping[label] is not None else None for label in time_labels]

    conn.close()
    return render_template('more_report.html',
        sku_summary=sku_summary,
        status_counts=status_counts,
        status_percentages=status_percentages,
        sku_summary_keys=sku_summary_keys,
        opened_counts=opened_counts,
        closed_counts=closed_counts,
        tags=tags,
        total_closed=total_closed,
        start_date=start_date,
        end_date=end_date,
        sku=sku_filter,
        time_labels=time_labels,
        total_opened=total_opened,
        total_in_progress=total_in_progress,
        time_data=time_data
    )



@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if session.get('role') != 'admin':
        return render_template('error.html', error='אין לך הרשאות מתאימות')
    error = None
    success = None
    team_id = session.get('team_id')
    
    if request.method == 'POST':
        if 'delete_user_id' in request.form:
            user_id = request.form['delete_user_id']
            # מחק משתמש מטבלת team_users
            conn = sqlite3.connect('teams.db')
            c = conn.cursor()
            c.execute('SELECT username FROM team_users WHERE user_id=? AND team_id=?', (user_id, team_id))
            user = c.fetchone()
            if user and user[0] != 'admin':
                c.execute('DELETE FROM team_users WHERE user_id=? AND team_id=?', (user_id, team_id))
                conn.commit()
                success = 'המשתמש נמחק בהצלחה!'
            conn.close()
        else:
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            if not username or not password or role not in ['admin', 'user']:
                error = 'יש למלא את כל השדות'
            else:
                # הוסף משתמש לטבלת team_users
                conn = sqlite3.connect('teams.db')
                c = conn.cursor()
                c.execute('SELECT * FROM team_users WHERE team_id=? AND username=?', (team_id, username))
                if c.fetchone():
                    error = 'שם המשתמש כבר קיים'
                else:
                    hashed_password = team_manager.hash_password(password)
                    c.execute('INSERT INTO team_users (team_id, username, password, role) VALUES (?, ?, ?, ?)', 
                             (team_id, username, hashed_password, role))
                    conn.commit()
                    success = 'המשתמש נוסף בהצלחה!'
                    
                    # תיעוד הוספת משתמש
                    log_activity(session.get('user_id'), session.get('username'), team_id, 
                               "הוספת משתמש", f"נוסף משתמש: {username}")
                conn.close()
    
    # קבל משתמשים מטבלת team_users
    conn = sqlite3.connect('teams.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, role FROM team_users WHERE team_id=? AND username != "admin"', (team_id,))
    users = c.fetchall()
    conn.close()
    
    return render_template('add_user.html', error=error, success=success, users=users)

@app.route('/export_chatbot_excel', methods=['POST'])
@login_required
def export_chatbot_excel():
    """ייצוא נתוני הבוט לקובץ Excel"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return make_response('No content provided', 400)
        
        # ניקוי URL encoding
        import urllib.parse
        content = urllib.parse.unquote(content)
        
        print(f"DEBUG: Original content length: {len(content)}")
        print(f"DEBUG: First 200 chars: {content[:200]}")
        
        # ניתוח התוכן להפקת נתונים טבלאיים
        lines = content.split('\n')
        table_data = []
        
        print(f"DEBUG: Processing content with {len(lines)} lines")
        print(f"DEBUG: First few lines: {lines[:3]}")
        
        # חיפוש נתונים בפורמט של הבוט
        current_tag = {}
        for line in lines:
            line = line.strip()
            
            # חיפוש תגים חדשים - מחפש את הפורמט "1. ✅ תג #123"
            if 'תג #' in line and ('**' in line or '✅' in line or '⏳' in line):
                if current_tag:
                    # שמירת התג הקודם
                    table_data.append([
                        current_tag.get('tag_id', ''),
                        current_tag.get('serial', ''),
                        current_tag.get('sku', ''),
                        current_tag.get('description', ''),
                        current_tag.get('date', ''),
                        current_tag.get('status', '')
                    ])
                # התחלת תג חדש
                tag_match = re.search(r'תג #(\d+)', line)
                current_tag = {'tag_id': tag_match.group(1) if tag_match else ''}
                print(f"DEBUG: Found new tag: {current_tag}")
            
            # חיפוש מספר סידורי - מחפש "📱 מספר סידורי: `12345`"
            elif 'מספר סידורי:' in line:
                serial_match = re.search(r'מספר סידורי: `([^`]+)`', line)
                if serial_match:
                    current_tag['serial'] = serial_match.group(1)
                    print(f"DEBUG: Found serial: {serial_match.group(1)}")
            
            # חיפוש מק"ט - מחפש "🏷️ מק"ט: `123`"
            elif 'מק"ט:' in line:
                sku_match = re.search(r'מק"ט: `([^`]+)`', line)
                if sku_match:
                    current_tag['sku'] = sku_match.group(1)
                    print(f"DEBUG: Found SKU: {sku_match.group(1)}")
            
            # חיפוש תיאור - מחפש "📝 תיאור: ..."
            elif 'תיאור:' in line:
                desc_match = re.search(r'תיאור: (.+)', line)
                if desc_match:
                    current_tag['description'] = desc_match.group(1)
                    print(f"DEBUG: Found description: {desc_match.group(1)[:50]}...")
            
            # חיפוש תאריך - מחפש "📅 נפתח: ..."
            elif 'נפתח:' in line:
                date_match = re.search(r'נפתח: (.+)', line)
                if date_match:
                    current_tag['date'] = date_match.group(1)
                    print(f"DEBUG: Found date: {date_match.group(1)}")
            
            # חיפוש סטטוס - מחפש "📊 סטטוס: ..."
            elif 'סטטוס:' in line:
                status_match = re.search(r'סטטוס: (.+)', line)
                if status_match:
                    current_tag['status'] = status_match.group(1)
                    print(f"DEBUG: Found status: {status_match.group(1)}")
        
        # הוספת התג האחרון
        if current_tag:
            table_data.append([
                current_tag.get('tag_id', ''),
                current_tag.get('serial', ''),
                current_tag.get('sku', ''),
                current_tag.get('description', ''),
                current_tag.get('date', ''),
                current_tag.get('status', '')
            ])
        
        print(f"DEBUG: Found {len(table_data)} tags")
        
        # אם לא נמצאו נתונים טבלאיים, ננסה לחלץ נתונים בצורה אחרת
        if not table_data:
            # חיפוש נתונים בצורה של רשימות
            for line in lines:
                line = line.strip()
                if ('תג תהליך:' in line or 'מספר סידורי:' in line or 
                    'מק"ט:' in line or 'סטטוס:' in line or 'תאריך:' in line):
                    clean_line = line.replace('**', '').replace('📊', '').replace('🔍', '').replace('✅', '').replace('❌', '')
                    parts = [part.strip() for part in clean_line.split(':') if part.strip()]
                    if len(parts) >= 2:
                        table_data.append(parts)
        
        # אם עדיין אין נתונים טבלאיים, ננסה לחלץ סטטיסטיקות
        if not table_data:
            stats_data = []
            for line in lines:
                line = line.strip()
                # חיפוש סטטיסטיקות כמו "📊 תגים פתוחים: 5"
                if ('📊' in line or '📈' in line) and ':' in line:
                    clean_line = line.replace('📊', '').replace('📈', '').replace('**', '').strip()
                    parts = [part.strip() for part in clean_line.split(':') if part.strip()]
                    if len(parts) >= 2:
                        stats_data.append(parts)
            
            if stats_data:
                table_data = stats_data
        
        # יצירת קובץ Excel
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('נתוני בוט')
        
        # הגדרת עיצובים
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 12
        })
        
        data_format = workbook.add_format({
            'bg_color': '#f8f9fa',
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'font_size': 11
        })
        
        # כתיבת הנתונים
        if table_data:
            # בדיקה אם אלו נתוני תגים או סטטיסטיקות
            if len(table_data) > 0 and len(table_data[0]) == 6 and table_data[0][0].isdigit():
                # נתוני תגים - יש לנו 6 עמודות
                headers = ['מספר תג', 'מספר סידורי', 'מק"ט', 'תיאור', 'תאריך פתיחה', 'סטטוס']
                for col_idx, header in enumerate(headers):
                    worksheet.write(0, col_idx, header, header_format)
                
                # כתיבת הנתונים
                for row_idx, row in enumerate(table_data):
                    for col_idx, cell in enumerate(row):
                        if col_idx < len(headers):  # וידוא שלא חורגים מהעמודות
                            worksheet.write(row_idx + 1, col_idx, cell, data_format)
                
                # התאמת רוחב העמודות
                worksheet.set_column(0, 0, 12)  # מספר תג
                worksheet.set_column(1, 1, 15)  # מספר סידורי
                worksheet.set_column(2, 2, 12)  # מק"ט
                worksheet.set_column(3, 3, 30)  # תיאור
                worksheet.set_column(4, 4, 15)  # תאריך
                worksheet.set_column(5, 5, 15)  # סטטוס
            else:
                # סטטיסטיקות או נתונים אחרים
                headers = ['פרט', 'ערך']
                for col_idx, header in enumerate(headers):
                    worksheet.write(0, col_idx, header, header_format)
                
                # כתיבת הנתונים
                for row_idx, row in enumerate(table_data):
                    for col_idx, cell in enumerate(row):
                        if col_idx < 2:  # מקסימום 2 עמודות
                            worksheet.write(row_idx + 1, col_idx, cell, data_format)
                
                # התאמת רוחב העמודות
                worksheet.set_column(0, 0, 25)  # פרט
                worksheet.set_column(1, 1, 15)  # ערך
        else:
            # אם אין נתונים טבלאיים, נכתוב את כל התוכן בצורה נקייה
            # ניקוי התוכן מתווים מיוחדים
            clean_content = content.replace('🔍', '').replace('📊', '').replace('📈', '').replace('✅', '').replace('❌', '').replace('⏳', '')
            clean_content = clean_content.replace('**', '').replace('`', '').replace('─', '-')
            
            worksheet.write(0, 0, 'תוכן הבוט', header_format)
            worksheet.write(1, 0, clean_content, data_format)
            worksheet.set_column(0, 0, 50)
        
        workbook.close()
        output.seek(0)
        
        # החזרת הקובץ
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = f'attachment; filename=chatbot_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        return response
        
    except Exception as e:
        print(f"Error in export_chatbot_excel: {str(e)}")
        return make_response(f'Error creating Excel file: {str(e)}', 500)

@app.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if session.get('role') != 'admin':
        return render_template('error.html', message='אין לך הרשאות מתאימות')
    db_path = get_team_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        # לא לאפשר מחיקת admin הראשי
        c.execute('SELECT username FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
        if user and user[0] != 'admin':
            c.execute('DELETE FROM users WHERE id=?', (user_id,))
            conn.commit()
    c.execute('SELECT id, username, role FROM users WHERE username != "admin"')
    users = c.fetchall()
    conn.close()
    return render_template('manage_users.html', users=users)

@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot():
    """דף הבוט העוזר"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            query = data.get('query', '').strip()
            
            if not query:
                return jsonify({'error': 'יש להזין שאלה'})
            
            # תיעוד פעילות
            log_activity(session.get('user_id'), session.get('username'), 
                        session.get('team_id'), "שאילתת בוט", query)
            
            # עיבוד השאלה
            response = chatbot_process_query(query)
            
            return jsonify({'response': response})
            
        except Exception as e:
            return jsonify({'error': f'שגיאה בעיבוד השאלה: {str(e)}'})
    
    return render_template('chatbot.html')

@app.route('/get_teams_for_management', methods=['GET'])
def get_teams_for_management():
    """קבל רשימת צוותים לניהול"""
    # בדוק אם המשתמש הוא Super Admin
    if 'user_id' not in session or session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'אין הרשאה'})
    
    try:
        conn = sqlite3.connect('teams.db')
        c = conn.cursor()
        c.execute('SELECT team_id, team_name, created_date, global_username, global_password FROM teams ORDER BY created_date DESC')
        teams = []
        for row in c.fetchall():
            teams.append({
                'id': row[0],
                'name': row[1],
                'created_date': row[2],
                'global_username': row[3],
                'global_password': row[4]
            })
        conn.close()
        return jsonify({'success': True, 'teams': teams})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/edit_team', methods=['POST'])
def edit_team():
    """ערוך שם צוות"""
    # בדוק אם המשתמש הוא Super Admin
    if 'user_id' not in session or session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'אין הרשאה'})
    
    try:
        print("=" * 50)
        print("התחלת עדכון צוות")
        print("=" * 50)
        
        data = request.get_json()
        team_id = data.get('team_id')
        new_name = data.get('new_name', '').strip()
        
        print(f"נתונים שהתקבלו: team_id={team_id}, new_name='{new_name}'")
        
        if not new_name:
            print("שגיאה: שם הצוות ריק")
            return jsonify({'success': False, 'error': 'שם הצוות לא יכול להיות ריק'})
        
        print("מתחבר למסד הנתונים...")
        conn = sqlite3.connect('teams.db')
        c = conn.cursor()
        
        # בדוק אם השם כבר קיים (למעט הצוות הנוכחי)
        print(f"בודק אם השם '{new_name}' כבר קיים...")
        c.execute('SELECT team_id FROM teams WHERE team_name=? AND team_id!=?', (new_name, team_id))
        existing_team = c.fetchone()
        print(f"בדיקת שם קיים: שם='{new_name}', team_id={team_id}, קיים={existing_team}")
        
        if existing_team:
            conn.close()
            print(f"שגיאה: שם הצוות '{new_name}' כבר קיים עבור צוות {existing_team[0]}")
            return jsonify({'success': False, 'error': 'שם הצוות כבר קיים'})
        
        print("השם זמין לעדכון")
        
        # בדוק שהצוות קיים
        print(f"בודק שהצוות {team_id} קיים...")
        c.execute('SELECT team_id FROM teams WHERE team_id=?', (team_id,))
        team_exists = c.fetchone()
        if not team_exists:
            conn.close()
            print(f"שגיאה: הצוות {team_id} לא נמצא")
            return jsonify({'success': False, 'error': 'הצוות לא נמצא'})
        
        print(f"הצוות {team_id} קיים")
        
        # עדכן את שם הצוות
        print(f"מבצע עדכון: SET team_name='{new_name}' WHERE team_id={team_id}")
        c.execute('UPDATE teams SET team_name=? WHERE team_id=?', (new_name, team_id))
        rows_affected = c.rowcount
        print(f"מספר שורות שהושפעו: {rows_affected}")
        
        conn.commit()
        print("השינויים נשמרו במסד הנתונים")
        conn.close()
        print("החיבור למסד הנתונים נסגר")
        
        print(f"עדכון צוות: team_id={team_id}, new_name={new_name}, rows_affected={rows_affected}")
        
        if rows_affected == 0:
            print("שגיאה: לא בוצע עדכון - הצוות לא נמצא")
            return jsonify({'success': False, 'error': 'לא בוצע עדכון - הצוות לא נמצא'})
        
        print(f"עדכון הצלח! צוות {team_id} עודכן לשם '{new_name}'")
        print("=" * 50)
        print("סיום עדכון צוות - הצלחה")
        print("=" * 50)
        return jsonify({'success': True})
    except Exception as e:
        print("=" * 50)
        print("שגיאה בעדכון צוות:")
        print(f"Error: {str(e)}")
        print("=" * 50)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_team', methods=['POST'])
def delete_team():
    """מחק צוות וכל הנתונים שלו"""
    # בדוק אם המשתמש הוא Super Admin
    if 'user_id' not in session or session.get('role') != 'super_admin':
        return jsonify({'success': False, 'error': 'אין הרשאה'})
    
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        
        conn = sqlite3.connect('teams.db')
        c = conn.cursor()
        
        # קבל את שם הצוות ונתיב מסד הנתונים
        c.execute('SELECT team_name, db_path FROM teams WHERE team_id=?', (team_id,))
        team = c.fetchone()
        if not team:
            conn.close()
            return jsonify({'success': False, 'error': 'הצוות לא נמצא'})
        
        team_name = team[0]
        db_path = team[1]
        
        print(f"מחיקת צוות: team_id={team_id}, team_name={team_name}, db_path={db_path}")
        
        # מחק את הצוות מטבלת teams
        c.execute('DELETE FROM teams WHERE team_id=?', (team_id,))
        teams_deleted = c.rowcount
        
        # מחק את כל המשתמשים של הצוות
        c.execute('DELETE FROM team_users WHERE team_id=?', (team_id,))
        users_deleted = c.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"נמחקו {teams_deleted} צוותים ו-{users_deleted} משתמשים")
        
        # מחק את קובץ מסד הנתונים של הצוות
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                print(f"נמחק קובץ מסד נתונים: {db_path}")
            except Exception as e:
                print(f"שגיאה במחיקת קובץ מסד נתונים {db_path}: {e}")
        
        # מחק גיבויים של הצוות
        backup_dir = "backups"
        if os.path.exists(backup_dir):
            try:
                for backup_file in os.listdir(backup_dir):
                    if backup_file.startswith(f"{team_name}_") and backup_file.endswith(".db"):
                        backup_path = os.path.join(backup_dir, backup_file)
                        os.remove(backup_path)
                        print(f"נמחק גיבוי: {backup_path}")
            except Exception as e:
                print(f"שגיאה במחיקת גיבויים: {e}")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate_team_code', methods=['POST'])
def generate_team_code():
    """מייצר קוד חד פעמי חדש ליצירת צוות"""
    try:
        # בדוק אם המשתמש הוא Super Admin
        if 'user_id' not in session or session.get('role') != 'super_admin':
            return jsonify({'success': False, 'error': 'אין הרשאה'})
        
        result = team_manager.generate_team_creation_code()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_team_codes', methods=['GET'])
def get_team_codes():
    """מחזיר את כל קודי יצירת הצוותים"""
    try:
        # בדוק אם המשתמש הוא Super Admin
        if 'user_id' not in session or session.get('role') != 'super_admin':
            return jsonify({'success': False, 'error': 'אין הרשאה'})
        
        codes = team_manager.get_all_team_creation_codes()
        return jsonify({'success': True, 'codes': codes})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_used_codes', methods=['POST'])
def delete_used_codes():
    """מוחק קודים משומשים ישנים"""
    try:
        # בדוק אם המשתמש הוא Super Admin
        if 'user_id' not in session or session.get('role') != 'super_admin':
            return jsonify({'success': False, 'error': 'אין הרשאה'})
        
        deleted_count = team_manager.delete_used_codes()
        return jsonify({'success': True, 'deleted_count': deleted_count})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin_login', methods=['POST'])
def admin_login():
    """כניסת מנהל עליון"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # בדוק פרטי מנהל עליון
        if username == 'admin' and password == '9077269':
            # הגדר session למנהל עליון
            session['user_id'] = 'admin'
            session['username'] = 'admin'
            session['role'] = 'super_admin'
            session['is_admin'] = True
            
            return jsonify({'success': True, 'message': 'התחברת בהצלחה כמנהל עליון'})
        else:
            return jsonify({'success': False, 'error': 'שם משתמש או סיסמה שגויים'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/inventory_count')
@login_required
def inventory_count():
    """דף ספירת מלאי"""
    try:
        # השתמש ב-DATABASE_PATH של הצוות הנבחר
        from team_manager import TeamManager
        import os
        
        team_manager = TeamManager()
        db_path = team_manager.get_team_db_path(session.get('selected_team_id'))
        
        if not db_path or not os.path.exists(db_path):
            return render_template('error.html', error="מסד נתונים לא נמצא")
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # קבל את כל התגים הפתוחים - מניעת כפילות על ידי בחירת תג אחד לכל מספר סידורי
        # אם יש כמה תגים פתוחים עם אותו מספר סידורי, נבחר את האחרון (הכי מעודכן)
        c.execute("""
            SELECT pt.tag_id, pt.serial_number, pt.fault_description, pt.status, 
                   pt.date_opened, pt.performer, pt.checker, COALESCE(pt.sku, p.sku, 'לא מוגדר') as sku
            FROM process_tags pt
            LEFT JOIN products p ON pt.serial_number = p.serial_number 
                AND (pt.sku = p.sku OR pt.sku IS NULL)
            WHERE pt.is_closed = 0
            AND pt.tag_id IN (
                SELECT MAX(tag_id) 
                FROM process_tags 
                WHERE is_closed = 0 
                GROUP BY serial_number
            )
            ORDER BY pt.date_opened DESC
        """)
        
        open_tags = c.fetchall()
        conn.close()
        
        return render_template('inventory_count.html', tags=open_tags)
        
    except Exception as e:
        print(f"שגיאה בטעינת ספירת מלאי: {e}")
        return render_template('error.html', error="שגיאה בטעינת ספירת מלאי")

@app.route('/update_inventory_status', methods=['POST'])
@login_required
def update_inventory_status():
    """עדכן סטטוס ספירת מלאי"""
    try:
        data = request.get_json()
        
        # בדוק אם זה בקשה לניקוי כל הספירה
        if data.get('clear_all'):
            # השתמש ב-DATABASE_PATH של הצוות הנבחר
            from team_manager import TeamManager
            import os
            
            team_manager = TeamManager()
            db_path = team_manager.get_team_db_path(session.get('selected_team_id'))
            
            if not db_path:
                return jsonify({'error': 'מסד נתונים לא נמצא'}), 500
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute("DROP TABLE IF EXISTS inventory_count")
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
        
        tag_id = data.get('tag_id')
        is_present = data.get('is_present')
        
        # השתמש ב-DATABASE_PATH של הצוות הנבחר
        from team_manager import TeamManager
        import os
        
        team_manager = TeamManager()
        db_path = team_manager.get_team_db_path(session.get('selected_team_id'))
        
        if not db_path:
            return jsonify({'error': 'מסד נתונים לא נמצא'}), 500
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # עדכן את הסטטוס בטבלה זמנית או בטבלה נפרדת
        # נשתמש בטבלה זמנית לספירת מלאי
        c.execute("""
            CREATE TABLE IF NOT EXISTS inventory_count (
                tag_id INTEGER,
                is_present INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (tag_id)
            )
        """)
        
        c.execute("""
            INSERT OR REPLACE INTO inventory_count (tag_id, is_present)
            VALUES (?, ?)
        """, (tag_id, 1 if is_present else 0))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"שגיאה בעדכון סטטוס ספירת מלאי: {e}")
        return jsonify({'error': 'שגיאה בעדכון סטטוס'}), 500

@app.route('/get_inventory_status')
@login_required
def get_inventory_status():
    """קבל סטטוס ספירת מלאי נוכחי"""
    try:
        # השתמש ב-DATABASE_PATH של הצוות הנבחר
        from team_manager import TeamManager
        import os
        
        team_manager = TeamManager()
        db_path = team_manager.get_team_db_path(session.get('selected_team_id'))
        
        if not db_path:
            return jsonify({'error': 'מסד נתונים לא נמצא'}), 500
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # קבל את כל התגים הפתוחים עם הסטטוס שלהם - מניעת כפילות
        c.execute("""
            SELECT pt.tag_id, pt.serial_number, pt.fault_description, pt.status, 
                   pt.date_opened, pt.performer, pt.checker, COALESCE(pt.sku, p.sku, 'לא מוגדר') as sku,
                   COALESCE(ic.is_present, 0) as is_present
            FROM process_tags pt
            LEFT JOIN products p ON pt.serial_number = p.serial_number 
                AND (pt.sku = p.sku OR pt.sku IS NULL)
            LEFT JOIN inventory_count ic ON pt.tag_id = ic.tag_id
            WHERE pt.is_closed = 0
            AND pt.tag_id IN (
                SELECT MAX(tag_id) 
                FROM process_tags 
                WHERE is_closed = 0 
                GROUP BY serial_number
            )
            ORDER BY pt.date_opened DESC
        """)
        
        tags_with_status = c.fetchall()
        conn.close()
        
        return jsonify({'tags': tags_with_status})
        
    except Exception as e:
        print(f"שגיאה בקבלת סטטוס ספירת מלאי: {e}")
        return jsonify({'error': 'שגיאה בקבלת סטטוס'}), 500

if __name__ == '__main__':
    init_db()
    # אתחל את מסד הנתונים של הצוותים
    team_manager.init_teams_db()
    # update_existing_tags_with_sku()  # הוסר - לא נדרש יותר
    # migrate_database_data()  # בוטל לפי בקשת המשתמש
    # Old backup systems removed - using BackupManager instead
    app.run(host='0.0.0.0', port=5000, debug=True)