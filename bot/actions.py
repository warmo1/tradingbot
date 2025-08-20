import subprocess
import sys
from .config import cfg
from .db import get_conn, save_backtest_result
from .backtest import run_backtest

def run_backtest_for_symbol(symbol: str, timeframe: str = "1h", strategy: str = "rsi"):
    """
    Runs a backtest for a single symbol and saves the results to the database.
    This now runs in the foreground to ensure results are saved before the web request finishes.
    """
    print(f"Starting backtest for {symbol} on {timeframe} with {strategy} strategy...")
    conn = get_conn(cfg.database_url)
    
    # We need to run the backtest function directly
    # Note: This will block the web request until the backtest is done.
    # For long backtests, a background task queue (Celery) would be better.
    _, summary_df = run_backtest(
        database_url=cfg.database_url,
        timeframe=timeframe,
        strategy_name=strategy,
        quote=cfg.default_quote,
        top=1, # We only want to run it for the one symbol
        # Pass dummy values for other strategy params, they'll be ignored
        fast=20, slow=50, rsi_period=14, rsi_oversold=30, rsi_overbought=70
    )
    
    # Filter summary to only the symbol we care about
    symbol_result_df = summary_df[summary_df['symbol'] == symbol]
    
    if not symbol_result_df.empty:
        save_backtest_result(conn, symbol, strategy, symbol_result_df)
        print(f"Saved backtest result for {symbol} with {strategy} strategy.")
    else:
        print(f"Could not generate backtest result for {symbol}.")
