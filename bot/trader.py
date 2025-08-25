import time
from .db import get_conn
from .strategy import RSIStrategy
from .config import cfg
from .exchange import get_trading_exchange, get_data_exchange

def trading_loop(symbol: str, timeframe: str="1h", strategy=RSIStrategy(), trade_amount: float=50.0, sleep_s: int=300, sandbox_mode: bool=True):
    
    mode = "Sandbox" if sandbox_mode else "LIVE"
    print(f"[{mode}] Starting Uphold trading loop for {symbol} on {timeframe} timeframe.")
    
    # Initialize both exchange connections
    uphold_ex = get_trading_exchange()
    data_ex = get_data_exchange()

    while True:
        try:
            # 1. Get price data from the data source (Binance)
            ohlcv = data_ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = __import__("pandas").DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")

            # 2. Generate signal
            sig = strategy.generate_signals(df)
            last_sig = int(sig.iloc[-1]) if len(sig) else 0

            # 3. Get Uphold balance
            # The Uphold SDK uses 'cards' to represent balances
            cards = uphold_ex.get_cards()
            quote_currency = symbol.split('/')[1]
            base_currency = symbol.split('/')[0]
            
            quote_card = next((c for c in cards if c['currency'] == quote_currency), None)
            base_card = next((c for c in cards if c['currency'] == base_currency), None)
            
            quote_balance = float(quote_card['balance']) if quote_card else 0
            base_balance = float(base_card['balance']) if base_card else 0

            print(f"[{mode}][{symbol}] Signal: {last_sig} | Uphold {quote_currency} Balance: {quote_balance} | Uphold {base_currency} Balance: {base_balance}")

            # 4. Execute trade on Uphold
            if last_sig == 1 and quote_card and quote_balance >= trade_amount: # Buy signal
                print(f"[{mode}][{symbol}] BUY signal received. Placing order on Uphold.")
                uphold_ex.prepare_txn(quote_card['id'], base_currency, trade_amount, quote_currency)

            elif last_sig == -1 and base_card and base_balance > 0: # Sell signal
                print(f"[{mode}][{symbol}] SELL signal received. Placing order on Uphold.")
                uphold_ex.prepare_txn(base_card['id'], quote_currency, base_balance, base_currency)

        except Exception as e:
            print(f"[{mode}][{symbol}] An error occurred: {e}")

        time.sleep(sleep_s)
