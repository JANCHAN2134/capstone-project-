import pandas as pd
import requests
import streamlit as st

from db_utils import get_connection, get_schema
from schema_glossary import GLOSSARY

OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", None)


# ---------- FORMAT SCHEMA ----------
def format_schema(schema: dict) -> str:
    lines = []
    for table, columns in schema.items():
        lines.append(f"Table: {table}  |  Columns: {', '.join(columns)}")
    return "\n".join(lines)


# ---------- LLM CALL (raw, with message list) ----------
def call_llm_messages(messages: list):
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
                "messages": messages
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


# ---------- GENERATE SQL (with conversational memory) ----------
def generate_sql(user_query, chat_history=None):
    """
    chat_history: list of dicts {question, sql, summary}
    Passes the last 4 turns as context so the LLM can handle
    follow-up queries like "now filter by Maharashtra".
    """
    schema = format_schema(get_schema())

    system_msg = {
        "role": "system",
        "content": f"""You are an expert SQLite SQL generator for a business intelligence tool.

Database Schema:
{schema}

Glossary (user terms -> SQL meaning):
{GLOSSARY}

Rules:
- Use ONLY the tables and columns listed above
- Use proper JOINs when combining tables
- Return ONLY the raw SQL — no markdown, no backticks, no explanation
- If a previous question gives relevant context (e.g. "now show only SP state"), use it to refine the query
"""
    }

    messages = [system_msg]

    # Inject last 4 turns of chat history as context
    if chat_history:
        for entry in chat_history[-4:]:
            messages.append({"role": "user",      "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["sql"]})

    messages.append({"role": "user", "content": user_query})

    sql_raw = call_llm_messages(messages)
    if sql_raw:
        sql = clean_sql(sql_raw)
        if sql and "select" in sql.lower():
            return sql

    # ---------- KEYWORD FALLBACK ----------
    q = user_query.lower()

    if "state" in q or "region" in q:
        return (
            "SELECT c.customer_state, SUM(oi.price) AS revenue "
            "FROM customers c "
            "JOIN orders o ON c.customer_id = o.customer_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY c.customer_state ORDER BY revenue DESC LIMIT 5;"
        )
    elif "category" in q or "product" in q:
        return (
            "SELECT p.product_category_name, SUM(oi.price) AS revenue "
            "FROM products p "
            "JOIN order_items oi ON p.product_id = oi.product_id "
            "GROUP BY p.product_category_name ORDER BY revenue DESC LIMIT 10;"
        )
    elif "customer" in q or "buyer" in q:
        return (
            "SELECT c.customer_id, SUM(oi.price) AS total_spent "
            "FROM customers c "
            "JOIN orders o ON c.customer_id = o.customer_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY c.customer_id ORDER BY total_spent DESC LIMIT 10;"
        )
    elif "month" in q or "trend" in q:
        return (
            "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
            "SUM(oi.price) AS revenue "
            "FROM orders o "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY month ORDER BY month;"
        )
    elif "order" in q:
        return (
            "SELECT o.order_id, SUM(oi.price) AS revenue "
            "FROM orders o "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY o.order_id ORDER BY revenue DESC LIMIT 5;"
        )

    return "SELECT * FROM orders LIMIT 10;"


# ---------- RUN SQL ----------
def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ---------- EXPLAIN SQL ----------
def explain_sql(sql: str) -> str:
    """
    Returns a plain-English one-liner explaining what the SQL does.
    Shown in the UI so users understand the query logic.
    """
    schema = get_schema()
    tables_used = [t for t in schema.keys() if t.lower() in sql.lower()]
    parts = []
    if tables_used:
        parts.append(f"Queries **{', '.join(tables_used)}**.")
    if "JOIN" in sql.upper():
        parts.append("Joins related tables together.")
    if "GROUP BY" in sql.upper():
        parts.append("Groups rows to compute totals or counts.")
    if "ORDER BY" in sql.upper():
        parts.append("Ranks results.")
    if "LIMIT" in sql.upper():
        parts.append("Returns only the top N rows.")
    return " ".join(parts) if parts else "Fetches raw rows from the database."


# ---------- GENERATE SUMMARY ----------
def generate_summary(df, user_query=None, chat_history=None):
    if df is None or df.empty:
        return "No data returned for this query."

    rows = df.shape[0]
    preview = df.head(5).to_string(index=False)

    context_note = ""
    if chat_history and len(chat_history) > 1:
        context_note = f'\nPrevious question: "{chat_history[-2]["question"]}"'

    prompt = f"""You are a business analyst. Write a 2-3 sentence plain English insight from the data below.
Be specific: mention actual top values, trends, or notable findings.{context_note}

Current question: "{user_query or ''}"

Data ({rows} rows):
{preview}

Only write the insight. No preamble, no formatting."""

    summary = call_llm_messages([{"role": "user", "content": prompt}])
    if summary:
        return summary.strip()

    # Fallback stats summary
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    lines = [f"Returned {rows} rows."]
    if numeric_cols:
        col = numeric_cols[0]
        lines.append(
            f"{col}: total = {df[col].sum():,.2f}, avg = {df[col].mean():,.2f}."
        )
    return " ".join(lines)


# ---------- MAIN PIPELINE ----------
def process_query(user_query, chat_history=None):
    """
    Parameters
    ----------
    user_query   : str  — the user's natural language question
    chat_history : list — previous turns: [{question, sql, summary}, ...]

    Returns
    -------
    sql, df, summary, explanation
    """
    sql = generate_sql(user_query, chat_history)

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, f"SQL Error: {str(e)}", explain_sql(sql)

    summary     = generate_summary(df, user_query, chat_history)
    explanation = explain_sql(sql)

    return sql, df, summary, explanation
