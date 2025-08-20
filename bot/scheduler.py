import schedule
import time
import re
from .data import ingest_candles
from .ai_analyzer import get_ai_analyzer
# Correct way to import from other files in the 'bot' package
from .db import get_conn, upsert_insight, get_symbols, get_candles_df
from .config import cfg
from .exchange import get_exchange

def ingest_data_job():
    print("[Scheduler] Running hourly data ingestion job...")
    ingest_candles(cfg.database_url, timeframe="1h", top_by_volume=20, limit=100)
    print("[Scheduler] Data ingestion job finished.")

def generate_insights_job():
    print("[Scheduler] Running insights generation job...")
    conn = get_conn(cfg.database_url)
    ai = get_ai_analyzer()
    
    # --- Get top 5 symbols by volume ---
    ex = get_exchange()
    tickers = ex.fetch_tickers()
    all_symbols_in_db = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    
    liquid_symbols = sorted(
        [s for s in all_symbols_in_db if s in tickers],
        key=lambda s: (tickers.get(s, {}).get("quoteVolume") or 0),
        reverse=True
    )
    symbols_to_analyze = liquid_symbols[:5]

    for symbol in symbols_to_analyze:
        print(f"[Scheduler] Analyzing {symbol}...")
        # This line is now fixed
        df = get_candles_df(conn, cfg.exchange, symbol, "1h")
        if df.empty:
            continue
            
        suggestion = ai.get_trade_suggestion(symbol, df)
        
        # Extract the first word (BUY, SELL, or HOLD)
        match = re.match(r"^\s*(\w+)", suggestion)
        signal = match.group(1).upper() if match else "HOLD"
        
        upsert_insight(conn, symbol, signal, suggestion)
        print(f"[Scheduler] Saved new insight for {symbol}: {signal}")

    print("[Scheduler] Insights generation job finished.")

def run_scheduler():
    print("--- Starting Automated Scheduler ---")
    schedule.every().hour.do(ingest_data_job)
    schedule.every(30).minutes.do(generate_insights_job)

    # Run jobs once at the start
    ingest_data_job()
    generate_insights_job()

    while True:
        schedule.run_pending()
        time.sleep(1)
