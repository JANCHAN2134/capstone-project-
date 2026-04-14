import sqlite3
import os
import urllib.request

DB_PATH = "database/olist.db"

def build_database():
    if not os.path.exists("database"):
        os.makedirs("database")

    # If DB already exists → skip
    if os.path.exists(DB_PATH):
        print("Database already exists ✅")
        return

    print("Downloading database...")

    url = "https://drive.google.com/uc?export=download&id=1WjBYraA9QB5nD18ZMdQfWFTi9KD-ArC_"
    urllib.request.urlretrieve(url, DB_PATH)

    print("Database downloaded ✅")


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
