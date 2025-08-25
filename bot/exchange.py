from uphold import Uphold
from .config import cfg

def get_exchange(sandbox_mode: bool = False) -> Uphold:
    """
    Initializes and returns an authenticated Uphold API client.
    """
    # The Uphold SDK uses environment variables for keys, but we can pass them directly
    # Note: The official SDK is simple and doesn't have a formal sandbox mode toggle.
    # You must use separate sandbox keys in your .env file to test.
    
    api_key = cfg.sandbox_api_key if sandbox_mode else cfg.api_key
    api_secret = cfg.sandbox_api_secret if sandbox_mode else cfg.api_secret
    
    # This is a simplified way to use the SDK. In production, you'd use OAuth.
    # For this bot, we'll assume Personal Access Tokens are being used.
    # The SDK is not fully featured, so we'll have to make some direct requests.
    
    return Uphold(api_key, api_secret)


def get_uphold_assets(ex: Uphold):
    """
    Gets a list of all available assets on Uphold.
    """
    # The SDK doesn't have a direct method for this, so we make a request.
    return ex.get_assets()


def get_uphold_ohlcv(symbol: str, timeframe: str = 'day'):
    """
    Gets OHLCV data. Uphold's API is limited and doesn't provide this directly.
    This is a placeholder for where you would connect to a third-party data provider
    or use a different method if Uphold's API supported it.
    
    For now, we will return an empty list to prevent crashes.
    """
    print(f"WARNING: Uphold's API does not provide historical OHLCV data. Ingest will not work.")
    return []
