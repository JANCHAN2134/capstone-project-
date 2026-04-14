import sqlite3
import os
import requests

DB_PATH = "database/olist.db"


def build_database():
    if not os.path.exists("database"):
        os.makedirs("database")

    # Skip if already exists
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 1000000:
        print("Database already exists ✅")
        return

    print("Downloading database...")

    url = "https://github.com/JANCHAN2134/capstone-project-/releases/download/v1.0/olist.db"

    response = requests.get(url, stream=True)

    with open(DB_PATH, "wb") as f:
        for chunk in response.iter_content(1024):
            if chunk:
                f.write(chunk)

    print("Database ready ✅")


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_schema():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall()]

    schema = {}

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        schema[table] = [col[1] for col in cursor.fetchall()]

    conn.close()
    return schema
