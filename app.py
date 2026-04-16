import streamlit as st
from nl_to_sql import process_query
from visualizer import plot_data
from db_utils import build_database
import os

# ── Build DB on first run ──────────────────────────────────────────────────
if not os.path.exists("database/olist.db"):
    build_database()

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="QueryMind BI", layout="wide")
st.title("📊 QueryMind BI")
st.caption("Ask business questions in plain English — powered by AI + SQLite")

# ── Session state: persistent chat history ────────────────────────────────
# Each entry: {question, sql, df, summary, explanation}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💡 Try asking...")
    examples = [
        "Top 5 states by revenue",
        "Monthly sales trend",
        "Orders by product category",
        "Top 10 customers by spending",
        "Which payment method is most used?",
        "Average review score by category",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending_query = ex

    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.caption("Powered by OpenRouter (Llama 3) + SQLite + Chart.js")

# ── Render existing chat history ──────────────────────────────────────────
for i, entry in enumerate(st.session_state.chat_history):
    with st.chat_message("user"):
        st.write(entry["question"])

    with st.chat_message("assistant"):
        # SQL + explanation
        with st.expander("🧠 Generated SQL", expanded=False):
            st.code(entry["sql"], language="sql")
            if entry.get("explanation"):
                st.caption(f"ℹ️ {entry['explanation']}")

        # Data table
        if entry["df"] is not None and not entry["df"].empty:
            st.dataframe(entry["df"], use_container_width=True)
            plot_data(entry["df"])
        else:
            st.warning("No data returned.")

        # Summary
        st.info(entry["summary"])

# ── Input: text box OR sidebar button ─────────────────────────────────────
pending = st.session_state.pop("pending_query", None)
query   = st.chat_input("Ask a question about your data...") or pending

if query:
    # Show the user message immediately
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Pass history so LLM has multi-turn context
            sql, df, summary, explanation = process_query(
                query,
                chat_history=st.session_state.chat_history
            )

        # SQL + explanation
        with st.expander("🧠 Generated SQL", expanded=True):
            st.code(sql, language="sql")
            if explanation:
                st.caption(f"ℹ️ {explanation}")

        # Data table
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            plot_data(df)
        else:
            st.warning("No data returned. Try rephrasing your question.")

        # AI summary
        st.info(summary)

    # Save to history
    st.session_state.chat_history.append({
        "question":    query,
        "sql":         sql,
        "df":          df,
        "summary":     summary,
        "explanation": explanation,
    })
