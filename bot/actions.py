import subprocess
import sys
from .config import cfg

def run_backtest_for_symbol(symbol: str, timeframe: str = "1h", strategy: str = "rsi"):
    """
    Launches a backtest for a single symbol as a background process.
    """
    print(f"Starting backtest for {symbol} on {timeframe} with {strategy} strategy...")
    command = [
        sys.executable,
        "-m", "bot.run",
        "backtest",
        "--symbol", symbol,
        "--timeframe", timeframe,
        "--strategy", strategy
    ]
    # We use Popen to run this in the background.
    # In a real production app, you'd want a more robust task queue (like Celery).
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
