import streamlit as st
from nl_to_sql import process_query
from visualizer import plot_data
from db_utils import build_database
import os

# Build DB if not exists
if not os.path.exists("database/olist.db"):
    build_database()

st.set_page_config(page_title="QueryMind BI", layout="wide")

st.title("📊 QueryMind BI")
st.subheader("Ask questions in natural language")

# Sidebar examples
st.sidebar.header("Example Questions")
st.sidebar.write("• Top 5 states by revenue")
st.sidebar.write("• Monthly sales trend")
st.sidebar.write("• Orders by category")
st.sidebar.write("• Top customers by spending")

# Input box
query = st.text_input("Enter your question:")

if query:
    with st.spinner("Processing..."):
        sql, df, summary = process_query(query)

    st.subheader("🧠 Generated SQL")
    st.code(sql, language="sql")

    st.subheader("📋 Result")
    st.dataframe(df)

    st.subheader("📊 Visualization")
    fig = plot_data(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No suitable chart for this data")

    st.subheader("💡 Summary")
    st.write(summary)