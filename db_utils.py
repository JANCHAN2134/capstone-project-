import sqlite3
import os
import requests

DB_PATH = "database/olist.db"

FILE_ID = "PASTE_YOUR_FILE_ID_HERE"


def download_db():
    if not os.path.exists("database"):
        os.makedirs("database")

    if not os.path.exists(DB_PATH):
        print("Downloading database...")

        url = f"https://drive.google.com/uc?export=download&id={1WjBYraA9QB5nD18ZMdQfWFTi9KD-ArC_}"

        response = requests.get(url)

        with open(DB_PATH, "wb") as f:
            f.write(response.content)

        print("Download complete!")


def build_database():
    download_db()


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
