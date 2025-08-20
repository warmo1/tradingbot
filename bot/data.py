import time
from typing import Iterable, List, Optional
from .exchange import get_exchange, fetch_ohlcv
from .db import get_conn, init_schema, get_symbols, bulk_insert_candles, get_latest_ts
from .config import cfg

def _chunk(seq: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def ingest_candles(
    database_url: str,
    timeframe: str="1h",
    limit: int=500,
    quote: Optional[str]=None,
    top_by_volume: Optional[int]=None,
    symbol_override: Optional[str]=None
) -> None:
    ex = get_exchange()
    conn = get_conn(database_url)
    init_schema(conn)
    
    # If a single symbol is provided, use it. Otherwise, get a list.
    if symbol_override:
        symbols = [symbol_override]
    else:
        symbols = get_symbols(conn, cfg.exchange, quote=quote)
        if top_by_volume:
            tickers = ex.fetch_tickers()
            tickers = {s: t for s, t in tickers.items() if s in symbols}
            def vol_key(t):
                return t.get("quoteVolume") or t.get("baseVolume") or 0
            top_syms = sorted(tickers.keys(), key=lambda s: vol_key(tickers[s]) or 0, reverse=True)[:top_by_volume]
            symbols = top_syms

    for batch in _chunk(symbols, 5):
        for symbol in batch:
            since = get_latest_ts(conn, cfg.exchange, symbol, timeframe)
            if since is not None:
                since = since + 1
            try:
                ohlcv = fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit, ex=ex)
            except Exception as e:
                print(f"[ingest] {symbol} failed: {e}")
                continue
            rows = []
            for ts, o, h, l, c, v in ohlcv:
                rows.append((cfg.exchange, symbol, timeframe, int(ts), float(o), float(h), float(l), float(c), float(v)))
            if rows:
                bulk_insert_candles(conn, rows)
                print(f"[ingest] {symbol}: +{len(rows)} rows")
        time.sleep(getattr(ex, "rateLimit", 1000) / 1000.0)
