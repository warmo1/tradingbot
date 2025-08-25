import ccxt
from typing import Any
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
        ex.set_sandbox_mode(True)
        
    return ex

# (Other functions like fetch_ohlcv, etc., can be removed if not used elsewhere,
# but it's safe to leave them for now.)
