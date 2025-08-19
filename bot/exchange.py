import ccxt
from typing import Any, Optional
from .config import cfg

def get_exchange() -> Any:
    klass = getattr(ccxt, cfg.exchange)
    params = {}
    if cfg.api_key and cfg.api_secret:
        params["apiKey"] = cfg.api_key
        params["secret"] = cfg.api_secret
    if cfg.api_password:
        params["password"] = cfg.api_password
    ex = klass(params)
    ex.enableRateLimit = True
    return ex

def load_markets(ex=None):
    ex = ex or get_exchange()
    return ex.load_markets()

def fetch_ohlcv(symbol: str, timeframe: str = "1h", since: Optional[int]=None, limit: int=500, ex=None):
    ex = ex or get_exchange()
    return ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

def fetch_tickers(ex=None):
    ex = ex or get_exchange()
    return ex.fetch_tickers()

def create_order(symbol: str, side: str, amount: float, order_type: str="market", price: Optional[float]=None, ex=None):
    ex = ex or get_exchange()
    if order_type == "market":
        return ex.create_order(symbol, "market", side, amount)
    else:
        assert price is not None, "Price required for limit orders"
        return ex.create_order(symbol, "limit", side, amount, price)
