"""PriceScout Operator Console — Streamlit dashboard for monitoring listings, valuations, and ingestion health."""

import os

import mysql.connector
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

@st.cache_resource
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "capstone"),
    )


def run_query(query):
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    except Exception:
        # Reconnect on stale connection
        st.cache_resource.clear()
        conn = get_connection()
        return pd.read_sql(query, conn)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PriceScout Operator Console", page_icon="📊", layout="wide")
st.title("PriceScout Operator Console")

tab_listings, tab_valuations, tab_ingestion = st.tabs(["Listing Explorer", "Valuations", "Ingestion Health"])

# ---------------------------------------------------------------------------
# Tab 1 — Listing Explorer
# ---------------------------------------------------------------------------

with tab_listings:
    st.header("Listing Explorer")

    category = st.selectbox("Category", ["vehicle", "mobiles", "laptops"])

    if category == "vehicle":
        df = run_query("SELECT * FROM vehicle")
        brand_col = "brand"
    elif category == "mobiles":
        df = run_query("SELECT * FROM mobiles")
        brand_col = "brand"
    else:
        df = run_query("SELECT * FROM laptops")
        brand_col = "brandlap"

    if not df.empty:
        brands = ["All"] + sorted(df[brand_col].dropna().unique().tolist())
        selected_brand = st.selectbox("Filter by brand", brands)

        if selected_brand != "All":
            df = df[df[brand_col] == selected_brand]

        st.metric("Total Listings", len(df))
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No listings found for this category.")

# ---------------------------------------------------------------------------
# Tab 2 — Valuations
# ---------------------------------------------------------------------------

with tab_valuations:
    st.header("Valuations")

    price_df = run_query("SELECT post_type, brand, model, price FROM price WHERE price IS NOT NULL")

    if not price_df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Average Price", f"₹{price_df['price'].mean():,.0f}")
        col2.metric("Total Valued", len(price_df))
        col3.metric("Brand Count", price_df["brand"].nunique())

        st.subheader("Average Price by Brand")
        avg_by_brand = price_df.groupby("brand")["price"].mean().sort_values(ascending=False)
        st.bar_chart(avg_by_brand)

        st.subheader("Price Distribution")
        st.bar_chart(price_df["price"].value_counts(bins=20).sort_index())
    else:
        st.info("No valuations available yet.")

# ---------------------------------------------------------------------------
# Tab 3 — Ingestion Health
# ---------------------------------------------------------------------------

with tab_ingestion:
    st.header("Ingestion Health")

    log_df = run_query("SELECT * FROM ingestion_log ORDER BY started_at DESC")

    if not log_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Runs", len(log_df))
        col2.metric("Avg Duration (s)", f"{log_df['duration_seconds'].mean():.1f}")
        col3.metric("Total Ingested", int(log_df["listings_inserted"].sum()))
        total_processed = log_df["listings_processed"].sum()
        total_errors = log_df["errors"].sum()
        error_rate = (total_errors / total_processed * 100) if total_processed > 0 else 0
        col4.metric("Error Rate", f"{error_rate:.1f}%")

        st.subheader("Listings Processed vs Errors Over Time")
        chart_df = log_df[["started_at", "listings_processed", "errors"]].copy()
        chart_df = chart_df.sort_values("started_at")
        chart_df = chart_df.set_index("started_at")
        st.line_chart(chart_df)

        st.subheader("Recent Ingestion Logs")
        st.dataframe(log_df.head(20), use_container_width=True)
    else:
        st.info("No ingestion logs yet.")
