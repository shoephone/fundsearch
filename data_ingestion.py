import pandas as pd
import yfinance as yf
from edgar import Company, set_identity
import logging
from typing import Tuple, List, Dict, Any

# ==========================================
# 0. Configuration & Compliance
# ==========================================

# Configure backend logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SEC EDGAR Compliance (Required by edgartools)
set_identity("collin.mccoll@gmail.com")

# ==========================================
# 1. SEC Data Extraction (13F-HR)
# ==========================================

def fetch_13f_data(identifier: str) -> Tuple[pd.DataFrame, List[str], str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Fetches the latest 13F-HR filing for a given CIK/Ticker and extracts holdings.
    """
    logging.info(f"Querying SEC EDGAR for identifier: {identifier}")
    try:
        company = Company(identifier)
        entity_name = company.name
        
        # Fetch the most recent 13F-HR
        thirteenf = company.get_filings(form="13F-HR")[0].obj()
        
        # Multi-quarter trend analysis (20 periods)
        history_obj = thirteenf.holding_history(periods=20)
        history_df = history_obj.data if hasattr(history_obj, 'data') else history_obj
        
        # Quarter-over-quarter comparison
        comparison = thirteenf.compare_holdings()
        df = comparison.data
        
        # Isolate specific changes
        new_buys = df[df['Status'] == 'NEW']
        exits = df[df['Status'] == 'CLOSED']
        increases = df[df['Status'] == 'INCREASED']
        
        # Extract currently held tickers for the Yahoo Finance pipeline
        perf_symbols = df[df['Status'] != 'CLOSED']['Ticker'].dropna().unique().tolist()
        
        logging.info(f"Successfully extracted {len(perf_symbols)} active holdings for {entity_name}")
        return df, perf_symbols, entity_name, history_df, new_buys, exits, increases
        
    except Exception as e:
        logging.error(f"Failed to fetch 13F data for {identifier}: {e}")
        raise

# ==========================================
# 2. Market Data Extraction (Yahoo Finance)
# ==========================================

def fetch_yf_data(perf_symbols: List[str]) -> pd.DataFrame:
    """
    Fetches fundamental metrics for a list of ticker symbols.
    """
    if not perf_symbols:
        return pd.DataFrame()
        
    logging.info(f"Fetching fundamental data for {len(perf_symbols)} tickers...")
    
    metrics = [
        'longName', 'sector', 'epsCurrentYear', 'trailingPE', 'forwardPE', 
        'returnOnEquity', 'freeCashflow', 'debtToEquity', 'priceToBook', 
        'ebitda', 'ebitdaMargins', 'grossMargins', 'twoHundredDayAverage'
    ]
    
    perf_data = {}
    for symb in perf_symbols:
        try:
            info = yf.Ticker(symb).info
            if info:
                perf_data[symb] = [info.get(metric, pd.NA) for metric in metrics]
        except Exception as e:
            logging.warning(f"Could not fetch info for {symb}: {e}")
            pass 
            
    df_performance = pd.DataFrame(perf_data, index=metrics).T.reset_index()
    df_performance = df_performance.rename(columns={'index': 'Ticker'})
    return df_performance

def fetch_historical_performance(symbols: List[str], benchmark: str, period: str = "1y", start_date: str = None) -> pd.DataFrame:
    """
    Downloads historical price data and calculates cumulative percentage returns.
    """
    query_symbols = list(set(symbols + [benchmark]))
    if not query_symbols:
        return pd.DataFrame()
        
    logging.info(f"Fetching historical performance for {len(query_symbols)} tickers. Period: {period}, Start: {start_date}")
    
    try:
        if start_date:
            data = yf.download(query_symbols, start=start_date, progress=False)
        else:
            data = yf.download(query_symbols, period=period, progress=False)
            
        if 'Close' not in data:
            return pd.DataFrame()
            
        closes = data['Close']
        if isinstance(closes, pd.Series):
            closes = closes.to_frame(name=query_symbols[0])
            
        closes = closes.dropna(axis=1, how='all').ffill()
        
        if closes.empty:
            return pd.DataFrame()
            
        baseline = closes.bfill().iloc[0]
        pct_change = ((closes / baseline) - 1) * 100
        
        return pct_change
        
    except Exception as e:
        logging.error(f"Error fetching historical prices: {e}")
        return pd.DataFrame()

def fetch_ticker_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Retrieves recent news articles for a specific ticker symbol.
    """
    logging.info(f"Fetching news for {symbol}")
    try:
        ticker = yf.Ticker(symbol)
        return ticker.news 
    except Exception as e:
        logging.warning(f"Could not fetch news for {symbol}: {e}")
        return []