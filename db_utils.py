import sqlite3
import pandas as pd
import os
import zipfile
import urllib.request

DB_PATH = "database/olist.db"


def build_database():

    # ✅ Create folders
    if not os.path.exists("database"):
        os.makedirs("database")

    if not os.path.exists("data"):
        os.makedirs("data")

    zip_path = "data/olist.zip"

    # ✅ Download dataset if not exists
    if not os.path.exists(zip_path):
        print("Downloading dataset...")
        url = "https://github.com/olist/work-at-olist-data/raw/master/datasets/olist_public_dataset.zip"
        urllib.request.urlretrieve(url, zip_path)

        print("Extracting dataset...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("data")

    conn = sqlite3.connect(DB_PATH)

    print("Building database...")

    # ✅ Auto load ALL CSVs
    for file in os.listdir("data"):
        if file.endswith(".csv"):
            file_path = os.path.join("data", file)
            df = pd.read_csv(file_path)

            table_name = file.replace(".csv", "")
            df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.close()
    print("Database built successfully!")


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
