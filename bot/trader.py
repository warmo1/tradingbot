import time
from .db import get_conn
from .strategy import RSIStrategy
from .config import cfg
from .exchange import get_exchange

def trading_loop(symbol: str, timeframe: str="1h", strategy=RSIStrategy(), trade_amount: float=50.0, sleep_s: int=300, sandbox_mode: bool=True):
    conn = get_conn(cfg.database_url)
    ex = get_exchange(sandbox_mode=sandbox_mode)
    mode = "Sandbox" if sandbox_mode else "LIVE"
    
    print(f"[{mode}] Starting trading loop for {symbol} on {timeframe} timeframe.")

    while True:
        try:
            # 1. Get latest data
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = __import__("pandas").DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")

            # 2. Generate signal
            sig = strategy.generate_signals(df)
            last_sig = int(sig.iloc[-1]) if len(sig) else 0

            # 3. Get current balance and position
            balance = ex.fetch_balance()
            quote_currency = symbol.split('/')[1]
            base_currency = symbol.split('/')[0]
            
            quote_balance = balance['free'].get(quote_currency, 0)
            base_balance = balance['free'].get(base_currency, 0)
            
            print(f"[{mode}][{symbol}] Signal: {last_sig} | {quote_currency} Balance: {quote_balance} | {base_currency} Balance: {base_balance}")

            # 4. Execute trade
            if last_sig == 1 and quote_balance >= trade_amount: # Buy signal and enough cash
                print(f"[{mode}][{symbol}] BUY signal received. Placing market order.")
                ex.create_market_buy_order(symbol, trade_amount)
            
            elif last_sig == -1 and base_balance > 0: # Sell signal and we have the coin
                print(f"[{mode}][{symbol}] SELL signal received. Placing market order.")
                ex.create_market_sell_order(symbol, base_balance)

        except Exception as e:
            print(f"[{mode}][{symbol}] An error occurred: {e}")

        time.sleep(sleep_s)
