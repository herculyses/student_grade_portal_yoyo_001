import os
import sqlite3
from werkzeug.security import generate_password_hash

# Path to your database inside the instance folder
db_path = os.path.join("instance", "app.db")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print("📋 Tables found in database:", tables)

# ✅ Use the correct table name
table_name = "user"

print(f"✅ Found table '{table_name}'. Updating password hashes...")

# Check what columns exist
cursor.execute(f"PRAGMA table_info({table_name});")
columns = [c[1] for c in cursor.fetchall()]
print("📊 Columns in table:", columns)

if "password" not in columns:
    print("❌ Column 'password' not found — please tell me what it’s named.")
else:
    cursor.execute(f"SELECT id, password FROM {table_name}")
    rows = cursor.fetchall()

    for user_id, password in rows:
        if password and not password.startswith('pbkdf2:'):
            hashed = generate_password_hash(password)
            cursor.execute(f"UPDATE {table_name} SET password = ? WHERE id = ?", (hashed, user_id))
            print(f"🔐 Updated user ID {user_id}")

    conn.commit()
    print("✅ Passwords successfully hashed and updated!")

conn.close()
