import ccxt
from uphold import Uphold
from .config import cfg

def get_data_exchange() -> ccxt.Exchange:
    """Returns a ccxt instance for the public data source (e.g., Binance)."""
    klass = getattr(ccxt, cfg.data_source_exchange)
    exchange = klass()
    exchange.enableRateLimit = True
    return exchange

def get_trading_exchange() -> Uphold:
    """Returns an authenticated Uphold SDK client."""
    # The Uphold SDK uses Personal Access Tokens as the username/password for basic auth.
    if not cfg.api_key or not cfg.api_secret:
        raise ValueError("UPHOLD_API_KEY and UPHOLD_API_SECRET must be set in your .env file.")
    
    # The SDK is basic, we may need to handle sandbox logic manually if required.
    # For now, we assume keys directly control live vs sandbox.
    return Uphold(cfg.api_key, cfg.api_secret)
