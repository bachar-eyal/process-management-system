import sqlite3
import hashlib

# סיסמה אחידה
password = "eyal1234"
hashed_password = hashlib.sha256(password.encode()).hexdigest()

print("Fixing passwords...")
print(f"Password: {password}")
print(f"Hashed: {hashed_password}")

# תיקון מסד הנתונים הראשי
try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (hashed_password,))
    cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
    conn.commit()
    conn.close()
    print("Main database fixed")
except Exception as e:
    print(f"Error with main database: {e}")

# תיקון צוותים
try:
    conn = sqlite3.connect('teams.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE team_users SET password = ? WHERE username = 'admin'", (hashed_password,))
    conn.commit()
    conn.close()
    print("Teams database fixed")
except Exception as e:
    print(f"Error with teams database: {e}")

print("Done!")
