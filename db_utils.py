import sqlite3
import os
import requests

DB_PATH = "database/olist.db"


import sqlite3
import os
import requests

DB_PATH = "database/olist.db"


def build_database():
    if not os.path.exists("database"):
        os.makedirs("database")

    # Skip if already downloaded
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 1000000:
        print("Database already exists ✅")
        return

    print("Downloading database...")

    file_id = "1WjBYraA9QB5nD18ZMdQfWFTi9KD-ArC_"
    url = "https://drive.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(url, params={"id": file_id}, stream=True)

    # Handle Google Drive confirmation
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            response = session.get(url, params={"id": file_id, "confirm": value}, stream=True)

    # Save file
    with open(DB_PATH, "wb") as f:
        for chunk in response.iter_content(8192):
            if chunk:
                f.write(chunk)

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
