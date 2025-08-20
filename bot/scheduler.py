import schedule
import time
from .data import ingest_candles
from .news import get_latest_crypto_news
from .ai_analyzer import get_ai_analyzer
from .db import get_conn, add_insight
from .config import cfg

def ingest_data_job():
    print("[Scheduler] Running hourly data ingestion job...")
    ingest_candles(cfg.database_url, timeframe="1h", top_by_volume=20, limit=100)
    print("[Scheduler] Data ingestion job finished.")

def generate_insights_job():
    print("[Scheduler] Running 15-minute insights generation job...")
    conn = get_conn(cfg.database_url)
    headlines = get_latest_crypto_news()
    
    if headlines:
        ai = get_ai_analyzer()
        sentiment = ai.get_news_sentiment(headlines)
        add_insight(conn, "news_sentiment", sentiment)
        print(f"[Scheduler] Saved new sentiment insight: {sentiment[:60]}...")
    
    print("[Scheduler] Insights generation job finished.")


def run_scheduler():
    print("--- Starting Automated Scheduler ---")
    
    # Schedule the jobs
    schedule.every().hour.do(ingest_data_job)
    schedule.every(15).minutes.do(generate_insights_job)

    # Run the jobs once at the start
    ingest_data_job()
    generate_insights_job()

    while True:
        schedule.run_pending()
        time.sleep(1)
