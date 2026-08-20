import sqlite3

def init_db(db_path="database.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # Tenders table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        deadline TEXT NOT NULL
    )
    """)

    # Bids table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER NOT NULL,
        supplier_name TEXT NOT NULL,
        amount REAL NOT NULL,
        document TEXT,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (tender_id) REFERENCES tenders(id)
    )
    """)

    # Activity log table (for auditors)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        role TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized with all tables including activity_log")
import sqlite3
from datetime import datetime

def log_activity(user, role, action, db_path="database.db"):
    """Log user activity into the activity_log table."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO activity_log (user, role, action, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user, role, action, datetime.now()))

        conn.commit()
    except sqlite3.Error as e:
        print(f"⚠️ Error logging activity: {e}")
    finally:
        conn.close()
