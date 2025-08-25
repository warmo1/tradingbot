from .config import cfg
from .db import get_conn, save_backtest_result
from .backtest import run_backtest
import pandas as pd

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
        symbol_override=symbol, # This is the key change
        # Provide default values for other strategy params
        fast=20, slow=50, rsi_period=14, rsi_oversold=30, rsi_overbought=70
    )
    
    if summary_df.empty:
        print(f"INFO: Could not generate a backtest result for {symbol}. It may not have enough data.")
        error_df = pd.DataFrame([{"symbol": symbol, "trades": 0, "return_pct": 0, "max_dd_pct": 0, "error": "No result. Ingest more data for this symbol and timeframe."}])
        save_backtest_result(conn, symbol, strategy, error_df)
    else:
        save_backtest_result(conn, symbol, strategy, summary_df)
        print(f"SUCCESS: Saved backtest result for {symbol} with {strategy} strategy.")
