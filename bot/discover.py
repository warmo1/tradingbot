from typing import List, Set
from .exchange import get_exchange, get_uphold_assets
from .db import upsert_market, get_conn, init_schema
from .config import cfg

def discover_markets(database_url: str, quote: str | None = None) -> List[str]:
    ex = get_exchange()
    assets = get_uphold_assets(ex)
    conn = get_conn(database_url)
    init_schema(conn)

    discovered: List[str] = []

    for asset in assets:
        # Uphold provides assets, not pairs. We'll create pairs against our default quote currency.
        base = asset.get('code')
        q = quote or cfg.default_quote
        symbol = f"{base}/{q}"
        
        # We don't have all the market data, so we'll make some assumptions
        upsert_market(conn, (cfg.exchange, symbol, base, q, 1))
        discovered.append(symbol)
        
    return sorted(discovered)
