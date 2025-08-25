import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # --- Trading Exchange Configuration ---
    trading_exchange: str = "uphold"
    uphold_api_key: str = os.getenv("UPHOLD_API_KEY", "")
    uphold_api_secret: str = os.getenv("UPHOLD_API_SECRET", "")
    
    # --- Data Source Configuration ---
    data_source_exchange: str = "binance"
    
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")
    default_quote: str = os.getenv("DEFAULT_QUOTE", "USDT") # For data fetching
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

cfg = Config()
