import streamlit as st
from nl_to_sql import process_query
from visualizer import plot_data
from db_utils import build_database
import os

if not os.path.exists("database/olist.db"):
    build_database()

st.set_page_config(page_title="QueryMind BI", layout="wide")
st.title("📊 QueryMind BI")
st.subheader("Ask questions in natural language")

st.sidebar.header("Example Questions")
st.sidebar.write("• Top 5 states by revenue")
st.sidebar.write("• Monthly sales trend")
st.sidebar.write("• Orders by category")
st.sidebar.write("• Top customers by spending")

query = st.text_input("Enter your question:")

if query:
    with st.spinner("Processing..."):
        sql, df, summary = process_query(query)

    st.subheader("🧠 Generated SQL")
    st.code(sql, language="sql")

    st.subheader("📋 Result")
    if df is not None and not df.empty:
        st.dataframe(df, use_container_width=True)

        st.subheader("📊 Visualization")
        # plot_data now renders its own interactive Chart.js widget inline
        # — no return value needed, no st.pyplot() call
        plot_data(df)
    else:
        st.warning("No data returned. The query may have failed or returned empty results.")

    st.subheader("💡 Summary")
    st.write(summary)
