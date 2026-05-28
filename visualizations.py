import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

# Configure backend logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_valuation_scatter(plot_df: pd.DataFrame) -> go.Figure:
    """
    Generates a scatter plot comparing Trailing P/E to Return on Equity across sectors.
    """
    if plot_df.empty:
        logging.warning("Empty dataframe provided to create_valuation_scatter.")
        return go.Figure()

    logging.info("Generating Valuation Scatter Plot.")
    
    fig = px.scatter(
        plot_df, 
        x="trailingPE", 
        y="returnOnEquity", 
        color="sector",
        hover_name="Ticker", 
        hover_data={"longName": True, "sector": True}
    )
    
    fig.update_layout(
        title="P/E vs. ROE by Sector", 
        template="plotly_white", 
        height=550,
        xaxis_title="Trailing P/E Ratio", 
        yaxis_title="Return on Equity"
    )
    
    # Add borders to the scatter points for better visibility
    fig.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
    
    return fig

def create_roe_pb_scatter(plot_df: pd.DataFrame) -> go.Figure:
    """
    Generates a scatter plot comparing Price to Book vs Return on Equity across sectors.
    """
    if plot_df.empty:
        logging.warning("Empty dataframe provided to create_roe_pb_scatter.")
        return go.Figure()

    logging.info("Generating ROE vs P/B Scatter Plot.")
    
    fig = px.scatter(
        plot_df, 
        x="priceToBook", 
        y="returnOnEquity", 
        color="sector",
        hover_name="Ticker", 
        hover_data={"longName": True, "sector": False}
    )
    
    fig.update_layout(
        title="Price to Book vs. ROE by Sector", 
        template="plotly_white", 
        height=550,
        xaxis_title="Price to Book (P/B) Ratio", 
        yaxis_title="Return on Equity"
    )
    
    fig.update_traces(marker=dict(size=12, line=dict(width=1, color='DarkSlateGrey')))
    
    return fig

def create_performance_line_chart(df_plot: pd.DataFrame, benchmark_ticker: str, timeframe_label: str) -> go.Figure:
    """
    Generates a multi-line chart for historical cumulative returns vs a benchmark.
    """
    if df_plot.empty:
        logging.warning("Empty dataframe provided to create_performance_line_chart.")
        return go.Figure()

    logging.info(f"Generating Performance Line Chart for {timeframe_label}.")
    
    date_col = df_plot.columns[0]
    ticker_cols = [col for col in df_plot.columns if col != date_col]
    
    fig = px.line(
        df_plot, 
        x=date_col, 
        y=ticker_cols,
        labels={"value": "Cumulative Return (%)", "variable": "Ticker"}
    )
    
    fig.update_layout(
        title=f"Cumulative % Change Over {timeframe_label}", 
        template="plotly_white",
        height=550, 
        hovermode="x unified", 
        xaxis_title="Date", 
        yaxis_title="Return (%)"
    )
    
    # Visually distinguish the benchmark index by making it a thicker, dashed line
    fig.for_each_trace(
        lambda t: t.update(line=dict(width=3, dash='dash')) if t.name == benchmark_ticker else t.update(line=dict(width=1.5))
    )
    
    return fig

def create_dual_axis_deep_dive(df_shares: pd.DataFrame, df_perf_plot: pd.DataFrame, ticker: str, start_date_str: str) -> go.Figure:
    """
    Generates a dual-axis chart comparing quarterly shares held (Bar) against cumulative daily returns (Line).
    """
    if df_shares.empty or df_perf_plot.empty:
        logging.warning(f"Incomplete data provided to create_dual_axis_deep_dive for {ticker}.")
        return go.Figure()

    logging.info(f"Generating Dual-Axis Deep Dive Chart for {ticker}.")
    
    perf_date_col = df_perf_plot.columns[0]
    
    # Initialize the subplots with a secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Bar Chart: Shares Held (Secondary Axis)
    fig.add_trace(
        go.Bar(
            x=df_shares['Date'], 
            y=df_shares['Shares'], 
            name="Shares Held",
            marker_color='rgba(158, 202, 225, 0.6)', 
            marker_line_color='rgb(8, 48, 107)',
            marker_line_width=1.5, 
            opacity=0.7
        ), 
        secondary_y=True,
    )
    
    # 2. Line Chart: Cumulative Return (Primary Axis)
    fig.add_trace(
        go.Scatter(
            x=df_perf_plot[perf_date_col], 
            y=df_perf_plot[ticker],
            name=f"{ticker} Return (%)", 
            mode='lines',
            line=dict(color='rgb(31, 119, 180)', width=2.5)
        ), 
        secondary_y=False,
    )
    
    # 3. Layout updates
    fig.update_layout(
        title=f"{ticker}: Quarterly Shares vs. Daily Return (Since {start_date_str})",
        template="plotly_white", 
        height=550, 
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Cumulative Return (%)", secondary_y=False)
    fig.update_yaxes(title_text="Shares Held", secondary_y=True, showgrid=False)
    
    return fig
