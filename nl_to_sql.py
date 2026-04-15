import pandas as pd
import requests
import streamlit as st

from db_utils import get_connection, get_schema
from schema_glossary import GLOSSARY

OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]


def call_llm(prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://streamlit.app",
            "X-Title": "QueryMind BI"
        },
        json={
            "model": "openchat/openchat-3.5-0106",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    data = response.json()

    if "choices" not in data:
        return f"API Error: {data}"

    return data["choices"][0]["message"]["content"]

def clean_sql(sql):
    return sql.replace("```sql", "").replace("```", "").strip()


def generate_sql(user_query):
    schema = get_schema()

    prompt = f"""
Convert this question into SQLite SQL.

Schema:
{schema}

Glossary:
{GLOSSARY}

Question:
{user_query}

Return only SQL.
"""

    return call_llm(prompt)


def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def generate_summary(df):
    if df is None or df.empty:
        return "No data found."

    return f"Showing {len(df)} records based on your query."


def process_query(user_query):
    sql = clean_sql(generate_sql(user_query))

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, str(e)

    summary = generate_summary(df)

    return sql, df, summary
def generate_sql(user_query):
    q = user_query.lower()

    # 🔹 Define synonym groups
    revenue_words = ["revenue", "sales", "income", "earnings"]
    state_words = ["state", "region", "location"]
    customer_words = ["customer", "buyer", "user"]
    order_words = ["order", "purchase"]
    trend_words = ["trend", "month", "time", "growth"]
    avg_words = ["average", "avg", "mean"]

    # -------- STATE + REVENUE --------
    if any(w in q for w in state_words) and any(w in q for w in revenue_words):
        return """
        SELECT c.customer_state, SUM(oi.price) AS revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_state
        ORDER BY revenue DESC
        LIMIT 5;
        """

    # -------- ORDER + REVENUE --------
    elif any(w in q for w in order_words) and any(w in q for w in revenue_words):
        return """
        SELECT o.order_id, SUM(oi.price) AS revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY revenue DESC
        LIMIT 5;
        """

    # -------- CUSTOMER --------
    elif any(w in q for w in customer_words):
        return """
        SELECT c.customer_id, COUNT(o.order_id) AS orders,
               SUM(oi.price) AS total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 10;
        """

    # -------- TREND --------
    elif any(w in q for w in trend_words):
        return """
        SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month,
               SUM(oi.price) AS revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY month
        ORDER BY month;
        """

    # -------- AVERAGE --------
    elif any(w in q for w in avg_words):
        return """
        SELECT c.customer_state,
               AVG(oi.price) AS avg_order_value
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_state
        ORDER BY avg_order_value DESC
        LIMIT 5;
        """

    return "SELECT * FROM orders LIMIT 10;"
