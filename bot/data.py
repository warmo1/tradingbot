import time
from typing import List, Optional
from .exchange import get_data_exchange
from .db import get_conn, init_schema, get_symbols, bulk_insert_candles, get_latest_ts
from .config import cfg

def ingest_candles(
    database_url: str,
    timeframe: str="1h",
    limit: int=500,
    quote: Optional[str]=None,
    top_by_volume: Optional[int]=None,
    symbol_override: Optional[str]=None
) -> None:
    ex = get_data_exchange()
    conn = get_conn(database_url)
    init_schema(conn)
    
    if symbol_override:
        symbols = [symbol_override]
    else:
        symbols = get_symbols(conn, cfg.data_source_exchange, quote=quote)
        if top_by_volume:
            # Logic to filter by volume remains the same
            all_tickers = ex.fetch_tickers()
            symbols = sorted(
                [s for s in symbols if s in all_tickers],
                key=lambda s: (all_tickers.get(s, {}).get("quoteVolume") or 0),
                reverse=True
            )[:top_by_volume]

    for symbol in symbols:
        since = get_latest_ts(conn, cfg.data_source_exchange, symbol, timeframe)
        if since is not None: since += 1

        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
            rows = []
            for ts, o, h, l, c, v in ohlcv:
                rows.append((cfg.data_source_exchange, symbol, timeframe, int(ts), float(o), float(h), float(l), float(c), float(v)))
            if rows:
                bulk_insert_candles(conn, rows)
                print(f"[ingest][{cfg.data_source_exchange}] {symbol}: +{len(rows)} rows")
        except Exception as e:
            print(f"[ingest][{cfg.data_source_exchange}] {symbol} failed: {e}")
        
        time.sleep(ex.rateLimit / 1000)
