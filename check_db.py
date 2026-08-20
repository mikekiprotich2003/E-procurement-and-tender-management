import sqlite3

# Step 1: List all tables
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Tables in database:")
for row in tables:
    print(row[0])

conn.close()


# Step 2: Add missing columns to bids table
conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(bids)")
columns = [col[1] for col in cur.fetchall()]

if "document" not in columns:
    cur.execute("ALTER TABLE bids ADD COLUMN document TEXT")

if "status" not in columns:
    cur.execute("ALTER TABLE bids ADD COLUMN status TEXT DEFAULT 'Pending'")

conn.commit()
conn.close()

print("✅ bids table updated successfully!")
