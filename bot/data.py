import time
from typing import Iterable, List, Optional
from .exchange import get_uphold_ohlcv
from .db import get_conn, init_schema, bulk_insert_candles
from .config import cfg

def ingest_candles(
    database_url: str,
    timeframe: str="1h",
    limit: int=500,
    symbol_override: Optional[str]=None
) -> None:
    conn = get_conn(database_url)
    init_schema(conn)
    
    print("--- Uphold Data Ingestion Notice ---")
    print("Uphold's official API does not provide historical OHLCV (candle) data.")
    print("As a result, the 'ingest' command cannot function.")
    print("For analysis and backtesting, you would need to integrate a third-party data source like CoinGecko or another exchange's public API.")
    print("------------------------------------")
    
    # The following code will not run effectively, as get_uphold_ohlcv returns nothing.
    # It is left here as a placeholder.
    if symbol_override:
        ohlcv = get_uphold_ohlcv(symbol_override, timeframe)
        # ... logic to save the data would go here ...
