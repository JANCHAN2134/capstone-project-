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
            "model": "mistralai/mistral-7b-instruct",
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
    prompt = f"Summarize this:\n{df.head(10).to_string()}"
    return call_llm(prompt)


def process_query(user_query):
    sql = clean_sql(generate_sql(user_query))

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, str(e)

    summary = generate_summary(df)

    return sql, df, summary

def generate_sql(user_query):
    if "top 5 states" in user_query.lower():
        return """
        SELECT c.customer_state, SUM(oi.price) AS revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_state
        ORDER BY revenue DESC
        LIMIT 5;
        """
    return call_llm(user_query)
