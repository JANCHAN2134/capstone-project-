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

    except Exception:
        return None


# ---------- CLEAN SQL ----------
def clean_sql(sql):
    if not sql:
        return None
    return sql.replace("```sql", "").replace("```", "").strip()


# ---------- FORMAT SCHEMA FOR PROMPT ----------
def format_schema(schema: dict) -> str:
    """Convert schema dict to a readable string for the LLM prompt."""
    lines = []
    for table, columns in schema.items():
        lines.append(f"Table: {table}")
        lines.append(f"  Columns: {', '.join(columns)}")
    return "\n".join(lines)


# ---------- GENERATE SQL (HYBRID) ----------
# BUG FIX: Removed duplicate generate_sql definition.
# The original code had two functions with the same name — Python
# silently overwrites the first with the second, so the first was
# never used. Combined into one function with smart fallback.
def generate_sql(user_query):
    schema_dict = get_schema()
    schema = format_schema(schema_dict)  # BUG FIX: was passing raw dict to prompt

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
- Return ONLY the raw SQL query, no explanation, no markdown, no backticks

Question:
{user_query}
"""

    # Try LLM first
    sql = call_llm(prompt)

    if sql and "select" in sql.lower():
        return clean_sql(sql)

    # FALLBACK: keyword-based smart SQL
    q = user_query.lower()

    if "state" in q or "region" in q:
        return """
        SELECT c.customer_state, SUM(oi.price) AS revenue
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_state
        ORDER BY revenue DESC
        LIMIT 5;
        """

    elif "category" in q or "product" in q:
        return """
        SELECT p.product_category_name, SUM(oi.price) AS revenue
        FROM products p
        JOIN order_items oi ON p.product_id = oi.product_id
        GROUP BY p.product_category_name
        ORDER BY revenue DESC
        LIMIT 10;
        """

    elif "customer" in q or "buyer" in q:
        return """
        SELECT c.customer_id, SUM(oi.price) AS total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY c.customer_id
        ORDER BY total_spent DESC
        LIMIT 10;
        """

    elif "month" in q or "trend" in q:
        return """
        SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month,
               SUM(oi.price) AS revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY month
        ORDER BY month;
        """

    elif "order" in q:
        return """
        SELECT o.order_id, SUM(oi.price) AS revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY revenue DESC
        LIMIT 5;
        """

    return "SELECT * FROM orders LIMIT 10;"


# ---------- RUN SQL ----------
def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ---------- GENERATE SUMMARY ----------
# BUG FIX: This function was called in process_query() but never defined,
# causing the NameError crash on Streamlit Cloud.
def generate_summary(df):
    if df is None or df.empty:
        return "No data returned for this query."

    rows, cols = df.shape
    col_names = ", ".join(df.columns.tolist())
    summary_lines = [
        f"The query returned **{rows} rows** across **{cols} columns** ({col_names})."
    ]

    # Try LLM-based summary
    try:
        preview = df.head(5).to_string(index=False)
        prompt = f"""
You are a business analyst. Given the following data preview, write a 2-3 sentence
plain English summary of the key insight. Be concise and specific.

Data:
{preview}
"""
        llm_summary = call_llm(prompt)
        if llm_summary:
            return llm_summary.strip()
    except Exception:
        pass

    # Fallback: basic stats summary
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        col = numeric_cols[0]
        total = df[col].sum()
        avg = df[col].mean()
        summary_lines.append(
            f"Column `{col}`: total = **{total:,.2f}**, average = **{avg:,.2f}**."
        )

    return " ".join(summary_lines)


# ---------- MAIN PIPELINE ----------
def process_query(user_query):
    sql = generate_sql(user_query)

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, f"⚠️ SQL Error: {str(e)}"

    summary = generate_summary(df)  # Now defined above — no more NameError

    return sql, df, summary
