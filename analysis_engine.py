import pandas as pd
import re
import logging
from typing import Dict, List, Tuple

# Configure backend logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# 1. 13F Holdings Analysis
# ==========================================

def categorize_holdings(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Parses a 13F comparison dataframe and categorizes positions by their status.
    """
    if df is None or df.empty:
        logging.warning("Empty dataframe passed to categorize_holdings.")
        return {"new": pd.DataFrame(), "increases": pd.DataFrame(), "exits": pd.DataFrame()}

    logging.info("Categorizing quarter-over-quarter holdings changes.")
    
    # Isolate specific changes based on the 'Status' column from edgartools
    categorized = {
        "new": df[df['Status'] == 'NEW'].copy(),
        "increases": df[df['Status'] == 'INCREASED'].copy(),
        "exits": df[df['Status'] == 'CLOSED'].copy()
    }
    
    return categorized

def extract_active_tickers(df: pd.DataFrame) -> List[str]:
    """
    Extracts a list of currently held tickers (excludes closed positions) for downstream API pipelines.
    """
    if df is None or 'Status' not in df.columns or 'Ticker' not in df.columns:
        return []
        
    active_tickers = df[df['Status'] != 'CLOSED']['Ticker'].dropna().unique().tolist()
    logging.info(f"Extracted {len(active_tickers)} active tickers for market data processing.")
    
    return active_tickers

def tag_asset_classes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optional expansion: Segregates or tags specific asset types within the holdings.
    Useful for separating standard equities from targeted ETF holdings or isolating specific 
    structured credit targets (e.g., Generate CLO) before sending to the database/UI.
    """
    # Example implementation for future expansion
    if 'Name' in df.columns:
        df['Is_ETF'] = df['Name'].str.contains('ETF|FUND|TRUST', case=False, na=False)
        df['Is_CLO'] = df['Name'].str.contains('CLO|COLLATERALIZED', case=False, na=False)
    return df

# ==========================================
# 2. Time-Series & Deep Dive Processing
# ==========================================

def process_ticker_share_history(history_df: pd.DataFrame, target_ticker: str) -> pd.DataFrame:
    """
    Isolates and formats the multi-quarter share count history for a specific ticker.
    """
    logging.info(f"Processing historical share counts for {target_ticker}.")
    
    # 1. Locate the Ticker column robustly
    ticker_col = next((c for c in history_df.columns if str(c).lower() == 'ticker'), 'Ticker')
    
    # 2. Identify all date columns containing the share counts using regex
    date_cols = [c for c in history_df.columns if re.match(r'\d{4}-\d{2}-\d{2}', str(c))]
    
    if not date_cols:
        logging.error("Could not identify date columns in the history dataframe.")
        return pd.DataFrame()
        
    # 3. Filter for the selected ticker
    df_ticker_rows = history_df[history_df[ticker_col] == target_ticker][date_cols]
    
    if df_ticker_rows.empty:
        logging.warning(f"No historical shares found for {target_ticker}.")
        return pd.DataFrame()
        
    # 4. Clean data, convert to numeric, and sum shares across duplicate entries (if any)
    df_ticker_rows = df_ticker_rows.apply(pd.to_numeric, errors='coerce').fillna(0)
    shares_series = df_ticker_rows.sum(axis=0)
    
    # 5. Format for Plotly/UI
    df_shares = pd.DataFrame({
        'Date': pd.to_datetime(shares_series.index),
        'Shares': shares_series.values
    }).sort_values(by='Date')
    
    return df_shares

# ==========================================
# 3. Valuation & Performance Cleaning
# ==========================================

def clean_valuation_metrics(df_perf: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares the fundamental data for scatter plot visualizations by removing incomplete rows.
    """
    if df_perf is None or df_perf.empty:
        return pd.DataFrame()
        
    required_cols = ['trailingPE', 'returnOnEquity', 'sector']
    missing_cols = [col for col in required_cols if col not in df_perf.columns]
    
    if missing_cols:
        logging.warning(f"Missing columns for valuation cleaning: {missing_cols}")
        return df_perf
        
    plot_df = df_perf.dropna(subset=required_cols).copy()
    
    # Ensure numeric columns are strictly numeric for graphing
    plot_df['trailingPE'] = pd.to_numeric(plot_df['trailingPE'], errors='coerce')
    plot_df['returnOnEquity'] = pd.to_numeric(plot_df['returnOnEquity'], errors='coerce')
    
    return plot_df