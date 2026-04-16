"""
predictor.py
------------
Handles the "Predictive Report" mode of QueryMind BI.

Pipeline:
1. Fetch historical time-series data from the DB (monthly revenue / orders)
2. Apply linear regression to extrapolate future values
3. Call LLM to narrate the forecast in business language
4. Return everything: sql, df (historical), summary, explanation, intent,
   recommendations, prediction (HTML narrative), pred_df (forecast table)
"""

import pandas as pd
import numpy as np
import requests
import streamlit as st

from db_utils import get_connection
from nl_to_sql import (
    call_llm_messages,
    generate_sql,
    run_sql,
    explain_sql,
    generate_summary,
    generate_recommendations,
    classify_intent,
)

OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", None)


# ---------- DETECT FORECAST HORIZON ----------
def parse_horizon(user_query: str) -> int:
    """
    Extracts number of months to forecast from the query.
    Defaults to 3 months.
    """
    q = user_query.lower()
    mapping = {
        "1 month": 1, "one month": 1,
        "2 month": 2, "two month": 2,
        "3 month": 3, "three month": 3, "quarter": 3,
        "4 month": 4, "four month": 4,
        "5 month": 5, "five month": 5,
        "6 month": 6, "six month": 6, "half year": 6,
        "year": 12, "12 month": 12, "twelve month": 12,
    }
    for phrase, n in mapping.items():
        if phrase in q:
            return n
    # Look for digit patterns like "next 4 months"
    import re
    m = re.search(r"next\s+(\d+)\s+month", q)
    if m:
        return int(m.group(1))
    return 3


# ---------- FETCH HISTORICAL TIME SERIES ----------
def get_time_series(metric: str = "revenue") -> tuple[str, pd.DataFrame]:
    """
    Returns (sql, df) with monthly historical data.
    metric: "revenue" | "orders"
    """
    if metric == "orders":
        sql = (
            "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
            "COUNT(DISTINCT o.order_id) AS orders "
            "FROM orders o "
            "WHERE o.order_purchase_timestamp IS NOT NULL "
            "GROUP BY month ORDER BY month;"
        )
    else:
        sql = (
            "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
            "ROUND(SUM(oi.price), 2) AS revenue "
            "FROM orders o "
            "JOIN order_items oi ON o.order_id = oi.order_id "
            "WHERE o.order_purchase_timestamp IS NOT NULL "
            "GROUP BY month ORDER BY month;"
        )
    try:
        df = run_sql(sql)
        # Drop null/empty months
        df = df[df["month"].notna() & (df["month"] != "")]
        return sql, df
    except Exception as e:
        return sql, pd.DataFrame()


# ---------- DETECT METRIC FROM QUERY ----------
def detect_metric(user_query: str) -> str:
    q = user_query.lower()
    if "order" in q or "volume" in q:
        return "orders"
    return "revenue"


# ---------- LINEAR REGRESSION FORECAST ----------
def linear_forecast(df: pd.DataFrame, metric_col: str, n_months: int) -> pd.DataFrame:
    """
    Takes a df with columns [month, metric_col].
    Returns a df with [month, metric_col, type] where type = "historical" or "forecast".
    Uses numpy polyfit (degree 1) for linear extrapolation.
    """
    if df.empty or len(df) < 3:
        return pd.DataFrame()

    df = df.copy().reset_index(drop=True)
    df["t"] = range(len(df))

    y = df[metric_col].values.astype(float)
    x = df["t"].values

    # Fit linear model
    coeffs = np.polyfit(x, y, deg=1)
    slope, intercept = coeffs

    # Generate future months
    last_month = df["month"].iloc[-1]
    try:
        last_date = pd.to_datetime(last_month + "-01")
    except Exception:
        return pd.DataFrame()

    future_months = [
        (last_date + pd.DateOffset(months=i+1)).strftime("%Y-%m")
        for i in range(n_months)
    ]
    future_t = [len(df) + i for i in range(n_months)]
    future_vals = [max(0, slope * t + intercept) for t in future_t]

    hist_df = df[["month", metric_col]].copy()
    hist_df["type"] = "historical"

    fore_df = pd.DataFrame({
        "month": future_months,
        metric_col: [round(v, 2) for v in future_vals],
        "type": "forecast"
    })

    combined = pd.concat([hist_df, fore_df], ignore_index=True)
    return combined, slope, intercept


# ---------- CATEGORY-LEVEL FORECAST ----------
def get_category_forecast(n_months: int = 3) -> tuple[str, pd.DataFrame]:
    """
    Returns revenue forecast per top category using linear trend.
    """
    sql = (
        "SELECT strftime('%Y-%m', o.order_purchase_timestamp) AS month, "
        "p.product_category_name AS category, ROUND(SUM(oi.price), 2) AS revenue "
        "FROM orders o "
        "JOIN order_items oi ON o.order_id = oi.order_id "
        "JOIN products p ON oi.product_id = p.product_id "
        "WHERE o.order_purchase_timestamp IS NOT NULL AND p.product_category_name IS NOT NULL "
        "GROUP BY month, category ORDER BY month, category;"
    )
    try:
        df = run_sql(sql)
    except Exception:
        return sql, pd.DataFrame()

    # Get top 5 categories by total revenue
    top_cats = (
        df.groupby("category")["revenue"].sum()
        .sort_values(ascending=False)
        .head(5).index.tolist()
    )
    df = df[df["category"].isin(top_cats)]

    forecasts = []
    for cat in top_cats:
        cat_df = df[df["category"] == cat][["month", "revenue"]].copy().reset_index(drop=True)
        if len(cat_df) < 3:
            continue
        cat_df["t"] = range(len(cat_df))
        y = cat_df["revenue"].values.astype(float)
        x = cat_df["t"].values
        coeffs = np.polyfit(x, y, deg=1)
        slope, intercept = coeffs
        last_month = cat_df["month"].iloc[-1]
        try:
            last_date = pd.to_datetime(last_month + "-01")
        except Exception:
            continue
        for i in range(1, n_months + 1):
            future_month = (last_date + pd.DateOffset(months=i)).strftime("%Y-%m")
            val = max(0, slope * (len(cat_df) + i - 1) + intercept)
            forecasts.append({
                "category": cat,
                "month": future_month,
                "forecast_revenue": round(val, 2)
            })

    return sql, pd.DataFrame(forecasts)


# ---------- LLM FORECAST NARRATIVE ----------
def generate_forecast_narrative(
    user_query: str,
    metric: str,
    slope: float,
    intercept: float,
    pred_df: pd.DataFrame,
    n_months: int
) -> str:
    """
    Asks the LLM to write a business-friendly forecast narrative.
    """
    direction = "upward (growing)" if slope > 0 else "downward (declining)"
    forecast_rows = pred_df[pred_df["type"] == "forecast"] if "type" in pred_df.columns else pred_df
    preview = forecast_rows.to_string(index=False) if not forecast_rows.empty else "N/A"

    prompt = f"""You are a senior business analyst presenting a {n_months}-month {metric} forecast.

The trend is {direction} with a monthly change of approximately {abs(slope):,.0f} units.

Forecast data for next {n_months} months:
{preview}

User's question: "{user_query}"

Write a 3-4 sentence executive forecast narrative that:
1. States the trend direction clearly
2. Quotes the key forecast numbers
3. Gives a strategic implication for the business

Be specific, confident, and business-focused. No preamble."""

    result = call_llm_messages([{"role": "user", "content": prompt}])
    if result:
        return result.strip()

    # Fallback narrative
    direction_word = "growing" if slope > 0 else "declining"
    return (
        f"The {metric} trend is {direction_word}, with an estimated monthly change "
        f"of {abs(slope):,.0f} units. Based on historical patterns, the next {n_months} months "
        f"are projected accordingly. Businesses should plan inventory, staffing, and "
        f"marketing budgets to align with this trajectory."
    )


# ---------- MAIN PREDICTIVE PIPELINE ----------
def generate_predictive_report(user_query: str, chat_history=None):
    """
    Returns:
        sql, df (historical), summary, explanation, intent,
        recommendations, prediction (HTML string), pred_df (forecast df)
    """
    intent   = "predictive"
    metric   = detect_metric(user_query)
    n_months = parse_horizon(user_query)

    # ── Detect if asking about categories ─────────────────────────────────
    q = user_query.lower()
    is_category_query = "categor" in q or "product" in q

    if is_category_query:
        sql, pred_df = get_category_forecast(n_months)
        df_historical = pd.DataFrame()
        slope = 0
        intercept = 0
        combined_df = pred_df
    else:
        # ── Time-series forecast ───────────────────────────────────────────
        sql, df_historical = get_time_series(metric)

        if df_historical.empty or len(df_historical) < 3:
            return (
                sql, df_historical,
                "Not enough historical data to generate a forecast.",
                explain_sql(sql), intent, None, None, pd.DataFrame()
            )

        metric_col = "revenue" if metric == "revenue" else "orders"
        result = linear_forecast(df_historical, metric_col, n_months)

        if isinstance(result, tuple):
            combined_df, slope, intercept = result
        else:
            return (
                sql, df_historical,
                "Could not compute forecast from available data.",
                explain_sql(sql), intent, None, None, pd.DataFrame()
            )

        pred_df = combined_df  # full combined historical + forecast

    # ── Summary (on historical data) ──────────────────────────────────────
    summary = generate_summary(
        df_historical if not df_historical.empty else pred_df,
        user_query, chat_history, intent="predictive"
    )

    # ── Forecast narrative ─────────────────────────────────────────────────
    if is_category_query:
        prediction = generate_forecast_narrative(
            user_query, "category revenue", slope=0, intercept=0,
            pred_df=pred_df, n_months=n_months
        )
    else:
        prediction = generate_forecast_narrative(
            user_query, metric, slope, intercept, pred_df, n_months
        )

    # ── Business recommendations ───────────────────────────────────────────
    recommendations = generate_recommendations(
        pred_df, user_query, intent="predictive", summary=prediction
    )

    explanation = explain_sql(sql)

    return sql, df_historical, summary, explanation, intent, recommendations, prediction, pred_df
