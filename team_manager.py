import sqlite3
import os
import json
import shutil
from datetime import datetime
import hashlib

class TeamManager:
    def __init__(self, teams_db_path='teams.db'):
        self.teams_db_path = teams_db_path
        self.teams_dir = 'teams_databases'
        self.init_teams_db()
        
    def init_teams_db(self):
        """מאתחל את מסד הנתונים של הצוותים"""
        try:
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            # צור טבלת צוותים
            cursor.execute('''CREATE TABLE IF NOT EXISTS teams
                             (team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                              team_name TEXT UNIQUE NOT NULL,
                              db_path TEXT NOT NULL,
                              created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                              is_active BOOLEAN DEFAULT 1,
                              global_username TEXT,
                              global_password TEXT)''')
            
            # הוסף עמודות global_username ו-global_password אם הן לא קיימות
            cursor.execute("PRAGMA table_info(teams)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'global_username' not in columns:
                cursor.execute("ALTER TABLE teams ADD COLUMN global_username TEXT")
            if 'global_password' not in columns:
                cursor.execute("ALTER TABLE teams ADD COLUMN global_password TEXT")
            
            conn.commit()
            
            # צור טבלת משתמשים לכל צוות
            cursor.execute('''CREATE TABLE IF NOT EXISTS team_users
                             (user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                              team_id INTEGER NOT NULL,
                              username TEXT NOT NULL,
                              password TEXT NOT NULL,
                              role TEXT DEFAULT 'user',
                              created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                              FOREIGN KEY (team_id) REFERENCES teams (team_id),
                              UNIQUE(team_id, username))''')
            
            # צור טבלת קודי יצירת צוותים חד פעמיים
            cursor.execute('''CREATE TABLE IF NOT EXISTS team_creation_codes
                             (code_id INTEGER PRIMARY KEY AUTOINCREMENT,
                              code TEXT UNIQUE NOT NULL,
                              created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                              is_used BOOLEAN DEFAULT 0,
                              used_date DATETIME,
                              used_by_team_id INTEGER,
                              FOREIGN KEY (used_by_team_id) REFERENCES teams (team_id))''')
            
            conn.commit()
            conn.close()
            
            # צור תיקיית מסדי נתונים אם לא קיימת
            if not os.path.exists(self.teams_dir):
                os.makedirs(self.teams_dir)
        except Exception as e:
            print(f"Error initializing teams database: {e}")
            # נמשיך גם אם יש שגיאה - אולי מסד הנתונים כבר קיים
            pass
    
    def create_team(self, team_name, admin_username, admin_password, creation_code):
        """יוצר צוות חדש עם מסד נתונים משלו"""
        try:
            # בדוק אם שם הצוות כבר קיים
            if self.team_exists(team_name):
                return {'success': False, 'message': 'שם הצוות כבר קיים'}
            
            # בדוק את קוד יצירת הצוות
            code_validation = self.validate_team_creation_code(creation_code)
            if not code_validation['valid']:
                return {'success': False, 'message': code_validation['message']}
            
            # צור שם קובץ למסד הנתונים
            safe_team_name = "".join(c for c in team_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            db_filename = f"{safe_team_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_path = os.path.join(self.teams_dir, db_filename)
            
            # צור מסד נתונים חדש
            self.create_new_database(db_path)
            
            # הוסף את הצוות למסד הנתונים
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''INSERT INTO teams (team_name, db_path, global_username, global_password) VALUES (?, ?, ?, ?)''', 
                         (team_name, db_path, admin_username, admin_password))
            team_id = cursor.lastrowid
            
            # צור משתמש admin עם הפרטים שהמשתמש בחר
            hashed_password = self.hash_password(admin_password)
            cursor.execute('''INSERT INTO team_users (team_id, username, password, role) 
                             VALUES (?, ?, ?, ?)''', 
                         (team_id, admin_username, hashed_password, 'admin'))
            
            conn.commit()
            conn.close()
            
            # סמן את הקוד כמשומש
            self.mark_code_as_used(creation_code, team_id)
            
            return {'success': True, 
                    'message': f'צוות {team_name} נוצר בהצלחה! משתמש Admin: {admin_username}, סיסמה: {admin_password}', 
                    'team_id': team_id}
            
        except Exception as e:
            return {'success': False, 'message': f'שגיאה ביצירת הצוות: {str(e)}'}
    
    def create_new_database(self, db_path):
        """יוצר מסד נתונים חדש עם כל הטבלאות הנדרשות"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # צור את כל הטבלאות כמו ב-init_db המקורי
        cursor.execute('''CREATE TABLE products
                         (serial_number TEXT, sku TEXT, date_added DATETIME,
                          PRIMARY KEY (serial_number, sku))''')
        
        cursor.execute('''CREATE TABLE process_tags
                         (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, serial_number TEXT,
                          fault_description TEXT, actions_taken TEXT, status TEXT,
                          date_updated DATETIME, is_closed INTEGER DEFAULT 0,
                          date_opened DATETIME, test_results TEXT, performer TEXT)''')
        
        cursor.execute('''CREATE TABLE approved_skus
                         (sku_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          sku_code TEXT UNIQUE NOT NULL,
                          description TEXT,
                          is_active BOOLEAN DEFAULT 1,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE approved_issues
                         (issue_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          issue_code TEXT UNIQUE NOT NULL,
                          description TEXT,
                          solution TEXT,
                          is_active BOOLEAN DEFAULT 1,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE spare_parts
                         (part_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          part_number TEXT UNIQUE NOT NULL,
                          description TEXT,
                          manufacturer TEXT,
                          is_active BOOLEAN DEFAULT 1,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE spare_parts_usage
                         (usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          tag_id INTEGER NOT NULL,
                          part_id INTEGER NOT NULL,
                          serial_number TEXT NOT NULL,
                          date_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY (tag_id) REFERENCES process_tags (tag_id),
                          FOREIGN KEY (part_id) REFERENCES spare_parts (part_id))''')
        
        cursor.execute('''CREATE TABLE team_members
                         (member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          id_number TEXT UNIQUE NOT NULL,
                          role TEXT NOT NULL CHECK (role IN ('performer', 'checker', 'both')),
                          signature TEXT,
                          is_active BOOLEAN DEFAULT 1,
                          date_created DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          username TEXT UNIQUE NOT NULL,
                          password TEXT NOT NULL,
                          role TEXT DEFAULT 'user')''')
        
        # הוסף עמודות נוספות לטבלת process_tags
        columns_to_add = [
            'checker', 'item_statuses', 'sku', 'performer_signature', 
            'checker_signature', 'priority'
        ]
        
        for column in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE process_tags ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                pass  # העמודה כבר קיימת
        
        # הוסף עמודה final_check_image לטבלת approved_skus
        try:
            cursor.execute("ALTER TABLE approved_skus ADD COLUMN final_check_image TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        conn.close()
    
    def get_all_teams(self):
        """מחזיר את כל הצוותים"""
        conn = sqlite3.connect(self.teams_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT team_id, team_name, created_date, is_active 
                         FROM teams ORDER BY team_name''')
        teams = cursor.fetchall()
        
        conn.close()
        return teams
    
    def get_team_by_id(self, team_id):
        """מחזיר מידע על צוות לפי ID"""
        conn = sqlite3.connect(self.teams_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''SELECT team_id, team_name, db_path, created_date, is_active 
                         FROM teams WHERE team_id = ?''', (team_id,))
        team = cursor.fetchone()
        
        conn.close()
        return team
    
    def get_team_db_path(self, team_id):
        """מחזיר את הנתיב למסד הנתונים של הצוות"""
        team = self.get_team_by_id(team_id)
        if not team:
            return None

        db_path = team[2]  # db_path שנשמר ב-teams.db

        # טיפול במקרה שבו הנתיב נשמר עם '\\' (וינדוס) ורצים עכשיו על לינוקס (Docker)
        # לדוגמה: 'teams_databases\\צוות בדיקה_20250826_162719.db'
        # בלינוקס זה צריך להיות 'teams_databases/צוות בדיקה_20250826_162719.db'
        if db_path and ('\\' in db_path) and (os.path.sep == '/'):
            db_path = db_path.replace('\\', '/')

        return db_path
    
    def team_exists(self, team_name):
        """בודק אם צוות קיים"""
        conn = sqlite3.connect(self.teams_db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM teams WHERE team_name = ?', (team_name,))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def authenticate_user(self, team_id, username, password):
        """מאמת משתמש לצוות ספציפי"""
        conn = sqlite3.connect(self.teams_db_path)
        cursor = conn.cursor()
        
        hashed_password = self.hash_password(password)
        cursor.execute('''SELECT user_id, username, role FROM team_users 
                         WHERE team_id = ? AND username = ? AND password = ?''', 
                     (team_id, username, hashed_password))
        user = cursor.fetchone()
        
        conn.close()
        return user
    
    def hash_password(self, password):
        """מצפין סיסמה"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def delete_team(self, team_id):
        """מוחק צוות ומסד הנתונים שלו"""
        try:
            team = self.get_team_by_id(team_id)
            if not team:
                return {'success': False, 'message': 'צוות לא נמצא'}
            
            db_path = team[2]
            
            # מחק את הצוות מהמסד נתונים
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM team_users WHERE team_id = ?', (team_id,))
            cursor.execute('DELETE FROM teams WHERE team_id = ?', (team_id,))
            
            conn.commit()
            conn.close()
            
            # מחק את קובץ מסד הנתונים
            if os.path.exists(db_path):
                os.remove(db_path)
            
            return {'success': True, 'message': 'צוות נמחק בהצלחה'}
            
        except Exception as e:
            return {'success': False, 'message': f'שגיאה במחיקת הצוות: {str(e)}'}
    
    def get_team_stats(self, team_id):
        """מחזיר סטטיסטיקות לצוות ספציפי"""
        try:
            db_path = self.get_team_db_path(team_id)
            if not db_path or not os.path.exists(db_path):
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # ספירת תגים פתוחים
            cursor.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 0")
            open_tags = cursor.fetchone()[0]
            
            # ספירת תגים סגורים
            cursor.execute("SELECT COUNT(*) FROM process_tags WHERE is_closed = 1")
            closed_tags = cursor.fetchone()[0]
            
            # ספירת משתמשים
            cursor.execute("SELECT COUNT(*) FROM team_users")
            users_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'open_tags': open_tags,
                'closed_tags': closed_tags,
                'total_tags': open_tags + closed_tags,
                'users_count': users_count
            }
            
        except Exception as e:
            print(f"Error getting team stats: {e}")
            return None

    def generate_team_creation_code(self):
        """מייצר קוד חד פעמי חדש ליצירת צוות"""
        import random
        import string
        
        try:
            # צור קוד רנדומלי באורך 8 תווים
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            # הוסף את הקוד לטבלה
            cursor.execute('''INSERT INTO team_creation_codes (code) VALUES (?)''', (code,))
            conn.commit()
            conn.close()
            
            return {'success': True, 'code': code}
            
        except Exception as e:
            return {'success': False, 'message': f'שגיאה ביצירת קוד: {str(e)}'}
    
    def get_all_team_creation_codes(self):
        """מחזיר את כל קודי יצירת הצוותים"""
        try:
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''SELECT code, created_date
                             FROM team_creation_codes 
                             ORDER BY created_date DESC''')
            codes = cursor.fetchall()
            
            conn.close()
            return codes
            
        except Exception as e:
            print(f"Error getting team creation codes: {e}")
            return []
    
    def validate_team_creation_code(self, code):
        """בודק אם קוד יצירת צוות תקין ולא בשימוש"""
        try:
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''SELECT code_id, is_used FROM team_creation_codes WHERE code = ?''', (code,))
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                return {'valid': False, 'message': 'קוד לא קיים'}
            
            if result[1]:  # is_used
                return {'valid': False, 'message': 'קוד כבר בשימוש'}
            
            return {'valid': True, 'code_id': result[0]}
            
        except Exception as e:
            return {'valid': False, 'message': f'שגיאה בבדיקת הקוד: {str(e)}'}
    
    def mark_code_as_used(self, code, team_id):
        """מסמן קוד כמשומש ומקשר אותו לצוות שנוצר"""
        try:
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            # מחק את הקוד לגמרי מהטבלה
            cursor.execute('''DELETE FROM team_creation_codes WHERE code = ?''', (code,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"Error marking code as used: {e}")
            return False
    
    def delete_used_codes(self):
        """מוחק קודים משומשים ישנים (לאחר 30 יום)"""
        try:
            conn = sqlite3.connect(self.teams_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''DELETE FROM team_creation_codes 
                             WHERE is_used = 1 
                             AND used_date < datetime('now', '-30 days')''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting used codes: {e}")
            return 0
