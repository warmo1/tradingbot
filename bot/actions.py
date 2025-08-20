import subprocess
import sys
from .config import cfg
from .db import get_conn, save_backtest_result
from .backtest import run_backtest

def run_backtest_for_symbol(symbol: str, timeframe: str = "1h", strategy: str = "rsi"):
    """
    Runs a backtest for a single symbol and saves the results to the database.
    """
    print(f"Starting backtest for {symbol} on {timeframe} with {strategy} strategy...")
    conn = get_conn(cfg.database_url)
    
    # Correctly call the backtest function for a single symbol
    _, summary_df = run_backtest(
        database_url=cfg.database_url,
        timeframe=timeframe,
        strategy_name=strategy,
        symbol_override=symbol # This is the key change
    )
    
    if not summary_df.empty:
        save_backtest_result(conn, symbol, strategy, summary_df)
        print(f"Saved backtest result for {symbol} with {strategy} strategy.")
    else:
        print(f"Could not generate backtest result for {symbol}.")
