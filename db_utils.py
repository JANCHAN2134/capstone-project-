import sqlite3
import pandas as pd
import os

DB_PATH = "database/olist.db"

def build_database():
    conn = sqlite3.connect(DB_PATH)

    print("Building database...")

    # Load datasets
    customers = pd.read_csv("data/olist_customers_dataset.csv")
    geolocation = pd.read_csv("data/olist_geolocation_dataset.csv")
    order_items = pd.read_csv("data/olist_order_items_dataset.csv")
    payments = pd.read_csv("data/olist_order_payments_dataset.csv")
    reviews = pd.read_csv("data/olist_order_reviews_dataset.csv")
    orders = pd.read_csv("data/olist_orders_dataset.csv")
    products = pd.read_csv("data/olist_products_dataset.csv")
    sellers = pd.read_csv("data/olist_sellers_dataset.csv")
    category_translation = pd.read_csv("data/product_category_name_translation.csv")

    # Store in SQLite
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    geolocation.to_sql("geolocation", conn, if_exists="replace", index=False)
    order_items.to_sql("order_items", conn, if_exists="replace", index=False)
    payments.to_sql("payments", conn, if_exists="replace", index=False)
    reviews.to_sql("reviews", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    sellers.to_sql("sellers", conn, if_exists="replace", index=False)
    category_translation.to_sql("category_translation", conn, if_exists="replace", index=False)

    conn.close()
    print("Database built successfully!")

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_schema():
    conn = get_connection()
    cursor = conn.cursor()

    tables = [
        "customers", "geolocation", "order_items", "payments",
        "reviews", "orders", "products", "sellers", "category_translation"
    ]

    schema = {}

    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        schema[table] = [col[1] for col in cursor.fetchall()]

    conn.close()
    return schema


if __name__ == "__main__":
    build_database()