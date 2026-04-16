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


# ---------- LLM CALL ----------
def call_llm_messages(messages: list, max_tokens: int = 800):
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
                "messages": messages,
                "max_tokens": max_tokens,
            }
        )
        data = response.json()
        if "choices" not in data:
            return None
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


# ---------- INTENT CLASSIFICATION ----------
def classify_intent(user_query: str) -> str:
    """
    Classifies the question into one of four BI intent types:
    - descriptive  : What happened? (top sales, total orders, etc.)
    - diagnostic   : Why did it happen? (what caused low ratings, why did sales drop)
    - prescriptive : What should we do? (recommend actions, best strategy)
    - predictive   : What will happen? (forecast, predict, next month)
    """
    q = user_query.lower()

    # Rule-based fast classification
    predictive_keywords = ["forecast", "predict", "next month", "next quarter", "next year",
                           "future", "projection", "trend forecast", "will be", "expected"]
    prescriptive_keywords = ["should", "recommend", "what to do", "improve", "strategy",
                              "how to increase", "best way", "suggest", "optimize", "action"]
    diagnostic_keywords = ["why", "reason", "cause", "because", "explain", "factor",
                            "impact", "affect", "drove", "correlation"]

    if any(k in q for k in predictive_keywords):
        return "predictive"
    if any(k in q for k in prescriptive_keywords):
        return "prescriptive"
    if any(k in q for k in diagnostic_keywords):
        return "diagnostic"
    return "descriptive"


# ---------- CLEAN SQL ----------
def clean_sql(sql):
    if not sql:
        return None
    return sql.replace("```sql", "").replace("```", "").strip()


# ---------- GENERATE SQL ----------
def generate_sql(user_query, chat_history=None, intent=None):
    schema = format_schema(get_schema())

    # Enrich prompt based on intent
    intent_hint = ""
    if intent == "diagnostic":
        intent_hint = "\nThe user wants to understand WHY something happened. Include relevant breakdowns, comparisons, or correlated columns that explain the pattern."
    elif intent == "prescriptive":
        intent_hint = "\nThe user wants actionable data. Focus on metrics that show performance gaps, rankings, or opportunity areas."
    elif intent == "predictive":
        intent_hint = "\nThe user wants to forecast trends. Return time-series data ordered by date so a forecasting model can extrapolate it."

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
- If the user asks about "revenue", use SUM(oi.price) from order_items as oi
- If the user asks about "monthly trend", group by strftime('%Y-%m', o.order_purchase_timestamp)
- If the user asks about "category", join products table on product_id
- If a previous question gives context (e.g. "now filter by Maharashtra"), refine accordingly
- Always use aliases to make column names readable
- Never use columns that don't exist in the schema
{intent_hint}
"""
    }

    messages = [system_msg]

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

    if "payment" in q:
        return (
            "SELECT p.payment_type, COUNT(*) AS usage_count, SUM(p.payment_value) AS total_value "
            "FROM payments p GROUP BY p.payment_type ORDER BY usage_count DESC;"
        )
    elif "review" in q or "rating" in q:
        return (
            "SELECT p.product_category_name, ROUND(AVG(r.review_score), 2) AS avg_rating, COUNT(*) AS review_count "
            "FROM order_reviews r "
            "JOIN orders o ON r.order_id = o.order_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "JOIN products p ON oi.product_id = p.product_id "
            "WHERE p.product_category_name IS NOT NULL "
            "GROUP BY p.product_category_name ORDER BY avg_rating DESC LIMIT 10;"
        )
    elif "state" in q or "region" in q:
        return (
            "SELECT c.customer_state, SUM(oi.price) AS revenue, COUNT(DISTINCT o.order_id) AS orders "
            "FROM customers c "
            "JOIN orders o ON c.customer_id = o.customer_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY c.customer_state ORDER BY revenue DESC LIMIT 10;"
        )
    elif "category" in q or "product" in q:
        return (
            "SELECT p.product_category_name, SUM(oi.price) AS revenue, COUNT(*) AS items_sold "
            "FROM products p "
            "JOIN order_items oi ON p.product_id = oi.product_id "
            "WHERE p.product_category_name IS NOT NULL "
            "GROUP BY p.product_category_name ORDER BY revenue DESC LIMIT 10;"
        )
    elif "customer" in q or "buyer" in q:
        return (
            "SELECT c.customer_id, c.customer_city, SUM(oi.price) AS total_spent, COUNT(o.order_id) AS orders "
            "FROM customers c "
            "JOIN orders o ON c.customer_id = o.customer_id "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY c.customer_id ORDER BY total_spent DESC LIMIT 10;"
        )
    elif "month" in q or "trend" in q or "time" in q:
        return (
            "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
            "SUM(oi.price) AS revenue, COUNT(DISTINCT o.order_id) AS orders "
            "FROM orders o "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "GROUP BY month ORDER BY month;"
        )
    elif "order" in q:
        return (
            "SELECT o.order_status, COUNT(*) AS count "
            "FROM orders o GROUP BY o.order_status ORDER BY count DESC;"
        )

    return (
        "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
        "SUM(oi.price) AS revenue FROM orders o "
        "JOIN order_items oi ON o.order_id = oi.order_id "
        "GROUP BY month ORDER BY month;"
    )


# ---------- RUN SQL ----------
def run_sql(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ---------- EXPLAIN SQL ----------
def explain_sql(sql: str) -> str:
    schema = get_schema()
    tables_used = [t for t in schema.keys() if t.lower() in sql.lower()]
    parts = []
    if tables_used:
        parts.append(f"Queries {', '.join(tables_used)}.")
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
def generate_summary(df, user_query=None, chat_history=None, intent=None):
    if df is None or df.empty:
        return "No data returned for this query."

    rows = df.shape[0]
    preview = df.head(5).to_string(index=False)

    intent_instruction = {
        "descriptive":  "Describe WHAT the data shows. Mention top values, totals, and distributions.",
        "diagnostic":   "Explain WHY these patterns exist. What factors or breakdowns stand out as causes?",
        "prescriptive": "Focus on actionable insight. What does the data tell the business to do?",
        "predictive":   "Describe the trend. Is it growing, declining, or stable?",
    }.get(intent or "descriptive", "Describe what the data shows.")

    context_note = ""
    if chat_history and len(chat_history) > 1:
        context_note = f'\nPrevious question: "{chat_history[-2]["question"]}"'

    prompt = f"""You are a senior business analyst. Write a 2-3 sentence insight from the data below.
Be specific: mention actual top values, trends, or notable findings.
{intent_instruction}{context_note}

Current question: "{user_query or ''}"

Data ({rows} rows):
{preview}

Only write the insight. No preamble, no formatting."""

    summary = call_llm_messages([{"role": "user", "content": prompt}])
    if summary:
        return summary.strip()

    # Fallback
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    lines = [f"Returned {rows} rows."]
    if numeric_cols:
        col = numeric_cols[0]
        lines.append(f"{col}: total = {df[col].sum():,.2f}, avg = {df[col].mean():,.2f}.")
    return " ".join(lines)


# ---------- GENERATE BUSINESS RECOMMENDATIONS ----------
def generate_recommendations(df, user_query=None, intent=None, summary=None):
    """
    Returns 3 actionable business recommendations based on the data and intent.
    Always generated for prescriptive/diagnostic/descriptive queries.
    """
    if df is None or df.empty:
        return None

    preview = df.head(8).to_string(index=False)

    prompt = f"""You are a senior business strategist analyzing e-commerce data.
Based on the data below and the user's question, provide exactly 3 concise, actionable business recommendations.

User question: "{user_query or ''}"
Data insight: "{summary or ''}"

Data:
{preview}

Rules:
- Each recommendation must start on a new line
- Each must be 1-2 sentences, specific and actionable
- Focus on revenue growth, customer retention, or operational efficiency
- Do NOT number them, just list them one per line
- No headers, no preamble

3 recommendations:"""

    recs = call_llm_messages([{"role": "user", "content": prompt}])
    if recs:
        lines = [l.strip() for l in recs.strip().split("\n") if l.strip()]
        return "\n".join(lines[:3])

    # Fallback static recs
    fallback = {
        "descriptive":  "Focus marketing spend on your top-performing segment.\nInvestigate underperforming areas for quick wins.\nSet KPI benchmarks based on current top performers.",
        "diagnostic":   "Address the root cause of the identified underperformance.\nRun A/B tests to validate improvement hypotheses.\nMonitor the flagged segment weekly after any changes.",
        "prescriptive": "Prioritise the highest-ROI action from this analysis.\nAllocate resources to the top-performing segment first.\nSet a 30-day review milestone to measure impact.",
    }
    return fallback.get(intent or "descriptive", fallback["descriptive"])


# ---------- MAIN PIPELINE ----------
def process_query(user_query, chat_history=None):
    """
    Returns: sql, df, summary, explanation, intent, recommendations
    """
    intent = classify_intent(user_query)
    sql    = generate_sql(user_query, chat_history, intent=intent)

    try:
        df = run_sql(sql)
    except Exception as e:
        return sql, None, f"SQL Error: {str(e)}", explain_sql(sql), intent, None

    summary         = generate_summary(df, user_query, chat_history, intent=intent)
    explanation     = explain_sql(sql)
    recommendations = generate_recommendations(df, user_query, intent=intent, summary=summary)

    return sql, df, summary, explanation, intent, recommendations
