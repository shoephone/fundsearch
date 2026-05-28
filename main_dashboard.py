import streamlit as st
import pandas as pd
import re

# Import your modular backend
from data_ingestion import (
    fetch_13f_data, 
    fetch_yf_data, 
    fetch_historical_performance, 
    fetch_ticker_news
)
from analysis_engine import (
    process_ticker_share_history, 
    clean_valuation_metrics
)
from visualizations import (
    create_valuation_scatter,
    create_roe_pb_scatter, # <-- New Import
    create_performance_line_chart, 
    create_dual_axis_deep_dive
)

# ==========================================
# 0. Page Config & Caching Wrappers
# ==========================================
st.set_page_config(page_title="13F Portfolio Analytics", layout="wide")

# Wrap pure Python ingestion functions in Streamlit's cache
@st.cache_data(show_spinner=False)
def cached_13f_data(identifier):
    return fetch_13f_data(identifier)

@st.cache_data(show_spinner=False)
def cached_yf_data(perf_symbols):
    return fetch_yf_data(perf_symbols)

@st.cache_data(show_spinner=False)
def cached_historical_performance(symbols, benchmark, period="1y", start_date=None):
    return fetch_historical_performance(symbols, benchmark, period, start_date)

@st.cache_data(show_spinner=False, ttl=3600) # Cache news for 1 hour to stay fresh
def cached_ticker_news(symbol):
    return fetch_ticker_news(symbol)

# ==========================================
# 1. Sidebar Configuration
# ==========================================
st.sidebar.header("Portfolio Configuration")
target_cik = st.sidebar.text_input("Enter Fund CIK", value="1656456")
benchmark_ticker = st.sidebar.selectbox("Market Benchmark", options=["SPY", "QQQ", "DIA", "IWM"], index=0)

st.sidebar.markdown("""
**Common CIKs:**
* Appaloosa: `1656456`
* Pershing Square: `1336528`
* Baupost Group: `1054420`
* Causeway Cap: `1165797`
* Icahn Capital: `1412093`
* Tiger Global: `1167483`
* Coatue: `1135730`
""")

# ==========================================
# 2. Main Execution Flow
# ==========================================
try:
    with st.spinner(f"Querying SEC EDGAR for CIK {target_cik}..."):
        # 1. Ingest Data
        df_13f, tickers, fund_name, history_df, new_buys, exits, increases = cached_13f_data(target_cik)
        df_perf = cached_yf_data(tickers)
        
    st.title(f"{fund_name} Portfolio")
    
    # ------------------------------------------
    # 13F Data Tabs
    # ------------------------------------------
    st.subheader("13F Activity & Trend Analysis")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Full Portfolio", "New Buys", "Increased", "Closed (Exits)", "10-Period History"
    ])
    
    with tab1:
        st.dataframe(df_13f, use_container_width=True)
        
    with tab2:
        if not new_buys.empty:
            st.dataframe(new_buys, use_container_width=True)
        else:
            st.info("No new buys reported.")
            
    with tab3:
        if not increases.empty:
            st.dataframe(increases, use_container_width=True)
        else:
            st.info("No increased positions.")
            
    with tab4:
        if not exits.empty:
            st.dataframe(exits, use_container_width=True)
        else:
            st.info("No exited positions.")
    
    # ------------------------------------------
    # Add this updated block for tab5
    # ------------------------------------------
    with tab5:
        if not history_df.empty:
            # 1. Dynamically find all the date columns (these hold the share counts)
            date_cols = [c for c in history_df.columns if re.match(r'\d{4}-\d{2}-\d{2}', str(c))]
            
            # 2. Apply Pandas Styling: Commas, Terminal Font, and a Green Color Scale
            styled_history = (
                history_df.style
                .format("{:,.0f}", subset=date_cols)  # Drops the commas in for readability
                .set_properties(**{
                    'font-family': 'Roboto',       # Forces that Bloomberg terminal font
                    'background-color': '#0a0a0a',    # Pitch black cell background
                    'color': '#4CAF50',               # Terminal green text
                    'border-color': '#333333'         # Dark grid lines
                })
                .background_gradient(subset=date_cols, cmap='YlOrRd_r') # Applies heatmap scale
            )
            
            st.dataframe(styled_history, use_container_width=True)
        else:
            st.info("No historical holding data available.")
            
    
    # ------------------------------------------
    # Performance Indicators
    # ------------------------------------------
    st.subheader("Performance Indicators")
    st.dataframe(
        df_perf, use_container_width=True, hide_index=True,
        column_config={
            "Ticker": st.column_config.TextColumn("Symbol", width="small"),
            "longName": st.column_config.TextColumn("Company Name", width="medium"),
            "sector": st.column_config.TextColumn("Sector"),
            "trailingPE": st.column_config.NumberColumn("Trailing P/E", format="%.2f"),
            "returnOnEquity": st.column_config.NumberColumn("ROE", format="%.2f"),
        }
    )
    
    # ------------------------------------------
    # Visualizations
    # ------------------------------------------
    st.subheader("Valuation & Efficiency Maps")
    plot_df = clean_valuation_metrics(df_perf)
    
    if not plot_df.empty:
        # Create columns for side-by-side scatter plots
        scat_col1, scat_col2 = st.columns(2)
        
        with scat_col1:
            fig_pe_roe = create_valuation_scatter(plot_df)
            st.plotly_chart(fig_pe_roe, use_container_width=True)
            
        with scat_col2:
            fig_pb_roe = create_roe_pb_scatter(plot_df)
            st.plotly_chart(fig_pb_roe, use_container_width=True)
    else:
        st.warning("Insufficient fundamental data to generate valuation maps.")
    
    # ------------------------------------------
    # Position Deep Dive
    # ------------------------------------------
    st.subheader("Position Deep Dive: Shares vs. Returns")
    deep_dive_ticker = st.selectbox("Select Holding for Deep Dive", options=tickers, index=0)
    
    if deep_dive_ticker:
        with st.spinner(f"Generating deep dive for {deep_dive_ticker}..."):
            # Use analysis engine to isolate share history
            df_shares = process_ticker_share_history(history_df, deep_dive_ticker)
            
            if not df_shares.empty:
                start_date_dt = df_shares['Date'].min()
                start_date_str = start_date_dt.strftime('%Y-%m-%d')
                
                df_deep_dive_perf = cached_historical_performance(
                    [deep_dive_ticker], benchmark_ticker, start_date=start_date_str
                )
                
                if not df_deep_dive_perf.empty:
                    df_perf_plot = df_deep_dive_perf.reset_index()
                    fig_dual = create_dual_axis_deep_dive(df_shares, df_perf_plot, deep_dive_ticker, start_date_str, fund_name)
                    st.plotly_chart(fig_dual, use_container_width=True)
                else:
                    st.warning(f"Insufficient historical price data for {deep_dive_ticker}.")
            else:
                st.warning(f"No historical shares found for {deep_dive_ticker}.")

            # ------------------------------------------
            # News Feed
            # ------------------------------------------
            st.divider()
            st.subheader(f"🗞️ Latest News: {deep_dive_ticker}")
            
            news_data = cached_ticker_news(deep_dive_ticker)
            
            if news_data:
                for article in news_data[:5]:
                    content = article.get("content", {})
                    title = content.get("title", "No Title Available")
                    publisher = content.get("provider", {}).get("displayName", "Unknown Publisher")
                    link = content.get("clickThroughUrl", {}).get("url", "#")
                    pub_date_str = content.get("pubDate")
                    
                    try:
                        date_str = pd.to_datetime(pub_date_str).strftime('%Y-%m-%d %H:%M') if pub_date_str else "Unknown Date"
                    except Exception:
                        date_str = pub_date_str
                    
                    st.markdown(f"**[{title}]({link})**")
                    st.caption(f"Published by **{publisher}** on {date_str}")
                    st.write("") 
            else:
                st.info("No recent news articles found for this ticker.")

except Exception as e:
    st.error(f"Failed to load dashboard for CIK '{target_cik}'. Check backend logs.")
    st.exception(e)
