import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'supplier'")
    print("Role column added successfully!")
except sqlite3.OperationalError:
    print("Role column already exists, skipping...")

conn.commit()
conn.close()
import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    role TEXT,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("✅ activity_log table created successfully!")
