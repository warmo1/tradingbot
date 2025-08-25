import ccxt
from typing import Any, Optional
from .config import cfg

def get_exchange(sandbox_mode: bool = False) -> Any:
    klass = getattr(ccxt, cfg.exchange)
    
    params = {
        'apiKey': cfg.sandbox_api_key if sandbox_mode else cfg.api_key,
        'secret': cfg.sandbox_api_secret if sandbox_mode else cfg.api_secret,
    }
    
    ex = klass(params)
    ex.enableRateLimit = True
    
    if sandbox_mode:
        if hasattr(ex, 'set_sandbox_mode'):
            ex.set_sandbox_mode(True)
        else:
            # Handle exchanges that don't have a formal sandbox mode in ccxt
            # This might involve changing API URLs, which can be added here if needed
            print(f"Warning: {cfg.exchange} does not have a formal sandbox mode in this library.")

    return ex

def load_markets(ex=None):
    ex = ex or get_exchange()
    return ex.load_markets()

# --- This function is now re-added ---
def fetch_ohlcv(symbol: str, timeframe: str = "1h", since: Optional[int]=None, limit: int=500, ex=None):
    ex = ex or get_exchange()
    return ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
