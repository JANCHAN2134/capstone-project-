import os
import sqlite3
import pandas as pd
import requests
import streamlit as st

from db_utils import get_connection, get_schema
from schema_glossary import GLOSSARY

# Get API key from Streamlit secrets
OPENROUTER_API_KEY = st.secrets["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"]


def call_llm(prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
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
        raise Exception(f"API Error: {data}")

    return data["choices"][0]["message"]["content"]


def clean_sql(sql):
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def generate_sql(user_query):
    schema = get_schema()

    prompt = f"""
You are an expert SQL generator.

Convert the following question into SQLite SQL.

Schema:
{schema}

Glossary:
{GLOSSARY}

Rules:
- Use correct joins
- Only use given columns
- Return only SQL

Question:
{user_query}
"""

    return call_llm(prompt)


def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def generate_summary(df):
    prompt = f"""
Summarize this data in simple business terms:

{df.head(10).to_string()}
"""

    return call_llm(prompt)


def process_query(user_query):
    sql = clean_sql(generate_sql(user_query))

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, f"Error: {e}"

    summary = generate_summary(df)

    return sql, df, summary


if __name__ == "__main__":
    sql, df, summary = process_query("Top 5 states by revenue")

    print(sql)
    print(df.head())
    print(summary)
