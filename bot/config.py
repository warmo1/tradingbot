import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///crypto_bot.db")
    paper_starting_cash: float = float(os.getenv("PAPER_STARTING_CASH", "10000"))
    admin_token: str = os.getenv("ADMIN_TOKEN", "") # Optional: for securing the trade form
    
    # --- New Provider Configuration ---
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    uphold_api: str = os.getenv("UPHOLD_API", "https://api-sandbox.uphold.com")
    uphold_pat: str = os.getenv("UPHOLD_PAT", "")
    sandbox: bool = os.getenv("SANDBOX", "true").lower() == "true"

cfg = Config()
