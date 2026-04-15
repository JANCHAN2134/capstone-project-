import pandas as pd
import requests
import streamlit as st

from db_utils import get_connection, get_schema
from schema_glossary import GLOSSARY

OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", None)


# ---------- LLM CALL ----------
def call_llm(prompt):
    if not OPENROUTER_API_KEY:
        return None

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "QueryMind BI"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )

        data = response.json()

        if "choices" not in data:
            return None

        return data["choices"][0]["message"]["content"]

    except:
        return None


# ---------- CLEAN SQL ----------
def clean_sql(sql):
    if not sql:
        return None
    return sql.replace("```sql", "").replace("```", "").strip()


# ---------- GENERATE SQL (HYBRID) ----------
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
- Use proper JOINs
- Return ONLY SQL (no explanation)

Question:
{user_query}
"""

    # 🔹 Try LLM
    sql = call_llm(prompt)

    if sql and "select" in sql.lower():
        return clean_sql(sql)

    # 🔹 FALLBACK (if LLM fails)
    return "SELECT * FROM orders LIMIT 10;"


# ---------- RUN SQL ----------
def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ---------- SUMMARY ----------
def generate_summary(df):
    if df is None or df.empty:
        return "No data found."

    return f"Showing {len(df)} records based on your query."


# ---------- MAIN PIPELINE ----------
def process_query(user_query):
    sql = generate_sql(user_query)

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, str(e)

    summary = generate_summary(df)

    return sql, df, summary
