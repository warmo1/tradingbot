from typing import List, Set
from .exchange import get_data_exchange
from .db import upsert_market, get_conn, init_schema
from .config import cfg

def discover_markets(database_url: str, quote: str | None = None) -> List[str]:
    ex = get_data_exchange()
    markets = ex.load_markets()
    conn = get_conn(database_url)
    init_schema(conn)

    discovered: List[str] = []
    
    for symbol, market in markets.items():
        if quote and market.get('quote') == quote and market.get('active'):
            upsert_market(conn, (cfg.data_source_exchange, symbol, market.get('base'), market.get('quote'), 1))
            discovered.append(symbol)
            
    return sorted(discovered)
