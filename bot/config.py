import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    exchange: str = os.getenv("EXCHANGE", "binance")
    api_key: str = os.getenv("API_KEY", "")
    api_secret: str = os.getenv("API_SECRET", "")
    api_password: str = os.getenv("API_PASSWORD", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")
    paper_starting_cash: float = float(os.getenv("PAPER_STARTING_CASH", "10000"))
    default_quote: str = os.getenv("DEFAULT_QUOTE", "USDT")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

cfg = Config()
