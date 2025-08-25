import ccxt
from uphold import Uphold
from .config import cfg

def get_data_exchange() -> ccxt.Exchange:
    """Returns a ccxt instance for the public data source (e.g., Binance)."""
    klass = getattr(ccxt, cfg.data_source_exchange)
    exchange = klass()
    exchange.enableRateLimit = True
    return exchange

def get_trading_exchange(sandbox: bool = True) -> Uphold:
    """Returns an authenticated Uphold SDK client."""
    if not cfg.uphold_api_key or not cfg.uphold_api_secret:
        raise ValueError("UPHOLD_API_KEY and UPHOLD_API_SECRET must be set in your .env file.")
    
    # The SDK takes a fourth argument for sandbox mode.
    return Uphold(cfg.uphold_api_key, cfg.uphold_api_secret, sandbox)
