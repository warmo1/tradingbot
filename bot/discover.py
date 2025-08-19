from typing import List, Set
from .exchange import get_exchange, load_markets
from .db import upsert_market, get_conn, init_schema
from .config import cfg

def _existing_symbols(conn, exchange: str) -> Set[str]:
    cur = conn.execute("SELECT symbol FROM markets WHERE exchange=?", (exchange,))
    return {r[0] for r in cur.fetchall()}

def discover_markets(database_url: str, quote: str | None = None) -> List[str]:
    ex = get_exchange()
    markets = load_markets(ex)
    conn = get_conn(database_url)
    init_schema(conn)

    before = _existing_symbols(conn, cfg.exchange)
    discovered: List[str] = []

    for mkt in markets.values():
        symbol = mkt.get("symbol")
        base = mkt.get("base")
        q = mkt.get("quote")
        active = 1 if mkt.get("active", True) else 0
        if quote and q != quote:
            continue
        upsert_market(conn, (cfg.exchange, symbol, base, q, active))
        if symbol not in before:
            discovered.append(symbol)
    return sorted(discovered)
