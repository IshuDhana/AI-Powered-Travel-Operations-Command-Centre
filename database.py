import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode='require')
    else:
        # Local fallback using SQLite via environment
        import sqlite3
        return None

def get_db():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, sslmode='require')
    return None

def init_db():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id SERIAL PRIMARY KEY,
                timestamp TEXT,
                agent_type TEXT,
                input_text TEXT,
                category TEXT,
                language TEXT,
                priority TEXT,
                summary TEXT,
                output TEXT
            )
        """)
        conn.commit()
        conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect("inquiries.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                agent_type TEXT,
                input_text TEXT,
                category TEXT,
                language TEXT,
                priority TEXT,
                summary TEXT,
                output TEXT
            )
        """)
        conn.commit()
        conn.close()

def save_inquiry(agent_type, input_text, category, language, priority, summary, output):
    db_url = os.getenv("DATABASE_URL")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if db_url:
        conn = psycopg2.connect(db_url, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inquiries
            (timestamp, agent_type, input_text, category, language, priority, summary, output)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (timestamp, agent_type, input_text, category, language, priority, summary, output))
        conn.commit()
        conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect("inquiries.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inquiries
            (timestamp, agent_type, input_text, category, language, priority, summary, output)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, agent_type, input_text, category, language, priority, summary, output))
        conn.commit()
        conn.close()

def get_all_inquiries():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows
    else:
        import sqlite3
        conn = sqlite3.connect("inquiries.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inquiries ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

def get_stats():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url, sslmode='require')
        cursor = conn.cursor()
    else:
        import sqlite3
        conn = sqlite3.connect("inquiries.db")
        cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM inquiries")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT category, COUNT(*) FROM inquiries GROUP BY category")
    by_category = dict(cursor.fetchall())

    cursor.execute("SELECT language, COUNT(*) FROM inquiries GROUP BY language")
    by_language = dict(cursor.fetchall())

    cursor.execute("SELECT priority, COUNT(*) FROM inquiries GROUP BY priority")
    by_priority = dict(cursor.fetchall())

    cursor.execute("SELECT agent_type, COUNT(*) FROM inquiries GROUP BY agent_type")
    by_agent = dict(cursor.fetchall())

    conn.close()
    return {
        "total": total,
        "by_category": by_category,
        "by_language": by_language,
        "by_priority": by_priority,
        "by_agent": by_agent
    }