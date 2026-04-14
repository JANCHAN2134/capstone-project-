import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
import requests

from db_utils import get_connection, get_schema
from schema_glossary import GLOSSARY

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# 🔹 Clean SQL (removes ```sql formatting)
def clean_sql(sql):
    sql = sql.strip()

    if sql.startswith("```"):
        sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


# 🔹 LLM Call Function
def call_llm(prompt):
    print("Calling LLM...")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        timeout=30
    )

    data = response.json()

    if "choices" not in data:
        raise Exception(f"API Error: {data}")

    return data["choices"][0]["message"]["content"]


# 🔹 Generate SQL
def generate_sql(user_query):
    schema = get_schema()

    prompt = f"""
You are an expert SQL generator.

Convert the following natural language question into a valid SQLite SQL query.

Database Schema:
{schema}

Glossary:
{GLOSSARY}

Rules:
- Use only the tables and columns provided
- Use proper JOINs where needed
- customer_state is in customers table, NOT orders
- Join orders and customers using customer_id
- Revenue = SUM(order_items.price)
- Return ONLY SQL (no explanation)

Question:
{user_query}
"""

    return call_llm(prompt).strip()


# 🔹 Run SQL
def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# 🔹 Fix SQL if error
def fix_sql(bad_query, error):
    prompt = f"""
The following SQL query is incorrect.

Query:
{bad_query}

Error:
{error}

Fix the query using correct relationships:
- customer_state is in customers table
- orders must join customers using customer_id
- revenue comes from order_items.price

Return ONLY corrected SQL.
"""

    return call_llm(prompt).strip()


# 🔹 Generate summary
def generate_summary(df):
    prompt = f"""
Summarize the following data in simple business language:

{df.head(10).to_string()}

Keep it short and clear.
"""

    return call_llm(prompt).strip()


# 🔹 Main pipeline
def process_query(user_query):
    sql = clean_sql(generate_sql(user_query))

    try:
        df = run_sql(sql)
    except Exception as e:
        sql = clean_sql(fix_sql(sql, str(e)))
        df = run_sql(sql)

    summary = generate_summary(df)

    return sql, df, summary


# 🔹 Test
if __name__ == "__main__":
    query = "Top 5 states by revenue"
    sql, df, summary = process_query(query)

    print("Generated SQL:")
    print(sql)

    print("\nResult:")
    print(df.head())

    print("\nSummary:")
    print(summary)