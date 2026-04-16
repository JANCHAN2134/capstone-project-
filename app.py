import streamlit as st
from nl_to_sql import process_query
from predictor import generate_predictive_report
from visualizer import plot_data
from db_utils import build_database
import os

# ── Build DB on first run ──────────────────────────────────────────────────
if not os.path.exists("database/olist.db"):
    build_database()

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QueryMind BI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Grotesk:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Header */
.qm-header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 0 10px 0;
    border-bottom: 2px solid #1a1a2e;
    margin-bottom: 24px;
}
.qm-logo {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 700;
    color: #0f3460;
    letter-spacing: -0.5px;
}
.qm-logo span { color: #e94560; }
.qm-tagline {
    font-size: 13px;
    color: #888;
    font-weight: 300;
}

/* Report type selector */
.report-selector {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}
.report-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 30px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s;
}
.pill-normal   { background: #e8f4fd; color: #1565c0; border-color: #1565c0; }
.pill-predict  { background: #fdf3e8; color: #e65100; border-color: #e65100; }
.pill-inactive { background: #f5f5f5; color: #aaa; border-color: #e0e0e0; }

/* Prediction badge */
.pred-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: linear-gradient(135deg, #ff6f00, #ff8f00);
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Business recommendations box */
.rec-box {
    background: linear-gradient(135deg, #f0f9ff 0%, #e8f5e9 100%);
    border-left: 4px solid #00897b;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-top: 10px;
}
.rec-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #00695c;
    margin-bottom: 8px;
}
.rec-item {
    font-size: 14px;
    color: #333;
    margin-bottom: 4px;
    display: flex;
    gap: 8px;
}

/* Prediction box */
.pred-box {
    background: linear-gradient(135deg, #fff8e1 0%, #fff3e0 100%);
    border-left: 4px solid #ff8f00;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin-top: 10px;
}
.pred-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #e65100;
    margin-bottom: 8px;
}

/* Intent tag */
.intent-tag {
    display: inline-block;
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 4px;
    font-weight: 500;
    margin-bottom: 8px;
}
.intent-descriptive  { background: #e3f2fd; color: #1565c0; }
.intent-diagnostic   { background: #fce4ec; color: #c62828; }
.intent-prescriptive { background: #e8f5e9; color: #2e7d32; }
.intent-predictive   { background: #fff3e0; color: #e65100; }

/* Sidebar enhancements */
.sidebar-section-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #888;
    margin: 16px 0 8px 0;
}

/* Chat messages */
.stChatMessage { border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="qm-header">
    <div>
        <div class="qm-logo">Query<span>Mind</span> BI</div>
        <div class="qm-tagline">Ask business questions in plain English — powered by AI + SQLite</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "report_type" not in st.session_state:
    st.session_state.report_type = "normal"

# ── Report Type Selector ───────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 6])

with col1:
    normal_style = "pill-normal" if st.session_state.report_type == "normal" else "pill-inactive"
    if st.button("📊 Normal Report", use_container_width=True,
                 type="primary" if st.session_state.report_type == "normal" else "secondary"):
        st.session_state.report_type = "normal"
        st.rerun()

with col2:
    if st.button("🔮 Predictive Report", use_container_width=True,
                 type="primary" if st.session_state.report_type == "predictive" else "secondary"):
        st.session_state.report_type = "predictive"
        st.rerun()

with col3:
    if st.session_state.report_type == "normal":
        st.markdown("""
        <div style="padding: 8px 14px; background: #e3f2fd; border-radius: 8px; font-size: 13px; color: #1565c0;">
        📊 <b>Normal Report</b> — Descriptive analysis, insights, and business recommendations based on your data.
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding: 8px 14px; background: #fff3e0; border-radius: 8px; font-size: 13px; color: #e65100;">
        🔮 <b>Predictive Report</b> — Forecasts future trends using historical data patterns + AI projections.
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section-title">💡 Normal Report Examples</div>', unsafe_allow_html=True)
    normal_examples = [
        "Top 5 states by revenue",
        "Orders by product category",
        "Top 10 customers by spending",
        "Which payment method is most used?",
        "Average review score by category",
    ]
    for ex in normal_examples:
        if st.button(ex, use_container_width=True, key=f"n_{ex}"):
            st.session_state.pending_query = ex
            st.session_state.report_type = "normal"

    st.markdown('<div class="sidebar-section-title">🔮 Predictive Report Examples</div>', unsafe_allow_html=True)
    predictive_examples = [
        "Forecast next 3 months of sales",
        "Predict revenue trend for next quarter",
        "Which categories will grow next month?",
        "Forecast order volume for next 6 months",
    ]
    for ex in predictive_examples:
        if st.button(ex, use_container_width=True, key=f"p_{ex}"):
            st.session_state.pending_query = ex
            st.session_state.report_type = "predictive"

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
        # Intent badge
        intent = entry.get("intent", "descriptive")
        intent_label = {
            "descriptive": "📋 Descriptive",
            "diagnostic": "🔍 Diagnostic",
            "prescriptive": "💡 Prescriptive",
            "predictive": "🔮 Predictive"
        }.get(intent, "📋 Descriptive")
        st.markdown(f'<span class="intent-tag intent-{intent}">{intent_label}</span>', unsafe_allow_html=True)

        # Report type badge
        if entry.get("report_type") == "predictive":
            st.markdown('<span class="pred-badge">🔮 Predictive Report</span>', unsafe_allow_html=True)

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

        # Business recommendations
        if entry.get("recommendations"):
            recs = entry["recommendations"]
            rec_items = "".join([f'<div class="rec-item">→ {r}</div>' for r in recs.split("\n") if r.strip()])
            st.markdown(f"""
            <div class="rec-box">
                <div class="rec-title">💼 Business Recommendations</div>
                {rec_items}
            </div>""", unsafe_allow_html=True)

        # Prediction output
        if entry.get("prediction"):
            st.markdown(f"""
            <div class="pred-box">
                <div class="pred-title">🔮 Predictive Forecast</div>
                {entry["prediction"]}
            </div>""", unsafe_allow_html=True)
            if entry.get("pred_df") is not None and not entry["pred_df"].empty:
                st.markdown("**Forecast Data:**")
                st.dataframe(entry["pred_df"], use_container_width=True)
                plot_data(entry["pred_df"])

# ── Input ──────────────────────────────────────────────────────────────────
pending = st.session_state.pop("pending_query", None)
report_type = st.session_state.report_type

placeholder = (
    "Ask a predictive question, e.g. 'Forecast next 3 months of revenue'..."
    if report_type == "predictive"
    else "Ask a business question, e.g. 'Top 5 states by revenue'..."
)
query = st.chat_input(placeholder) or pending

if query:
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        if report_type == "predictive":
            with st.spinner("🔮 Running predictive model..."):
                sql, df, summary, explanation, intent, recommendations, prediction, pred_df = \
                    generate_predictive_report(query, chat_history=st.session_state.chat_history)
        else:
            with st.spinner("🤔 Analysing your question..."):
                sql, df, summary, explanation, intent, recommendations = \
                    process_query(query, chat_history=st.session_state.chat_history)
                prediction = None
                pred_df = None

        # Intent badge
        intent_label = {
            "descriptive": "📋 Descriptive",
            "diagnostic": "🔍 Diagnostic",
            "prescriptive": "💡 Prescriptive",
            "predictive": "🔮 Predictive"
        }.get(intent, "📋 Descriptive")
        st.markdown(f'<span class="intent-tag intent-{intent}">{intent_label}</span>', unsafe_allow_html=True)

        if report_type == "predictive":
            st.markdown('<span class="pred-badge">🔮 Predictive Report</span>', unsafe_allow_html=True)

        # SQL
        with st.expander("🧠 Generated SQL", expanded=True):
            st.code(sql, language="sql")
            if explanation:
                st.caption(f"ℹ️ {explanation}")

        # Data
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True)
            plot_data(df)
        else:
            st.warning("No data returned. Try rephrasing your question.")

        # Summary
        st.info(summary)

        # Business recommendations
        if recommendations:
            rec_items = "".join([f'<div class="rec-item">→ {r}</div>' for r in recommendations.split("\n") if r.strip()])
            st.markdown(f"""
            <div class="rec-box">
                <div class="rec-title">💼 Business Recommendations</div>
                {rec_items}
            </div>""", unsafe_allow_html=True)

        # Prediction
        if prediction:
            st.markdown(f"""
            <div class="pred-box">
                <div class="pred-title">🔮 Predictive Forecast</div>
                {prediction}
            </div>""", unsafe_allow_html=True)
            if pred_df is not None and not pred_df.empty:
                st.markdown("**Forecast Data:**")
                st.dataframe(pred_df, use_container_width=True)
                plot_data(pred_df)

    # Save to history
    st.session_state.chat_history.append({
        "question":        query,
        "sql":             sql,
        "df":              df,
        "summary":         summary,
        "explanation":     explanation,
        "intent":          intent,
        "recommendations": recommendations,
        "report_type":     report_type,
        "prediction":      prediction,
        "pred_df":         pred_df,
    })
