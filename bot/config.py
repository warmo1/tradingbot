import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    exchange: str = os.getenv("EXCHANGE", "uphold")
    api_key: str = os.getenv("API_KEY", "")
    api_secret: str = os.getenv("API_SECRET", "")
    # --- New Uphold Sandbox Keys ---
    sandbox_api_key: str = os.getenv("SANDBOX_API_KEY", "")
    sandbox_api_secret: str = os.getenv("SANDBOX_API_SECRET", "")
    
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")
    default_quote: str = os.getenv("DEFAULT_QUOTE", "USD") # Uphold uses USD, not USDT
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

cfg = Config()
