import time
from .strategy import RSIStrategy
from .config import cfg
from .exchange import get_trading_exchange, get_data_exchange

def trading_loop(symbol: str, timeframe: str="1h", strategy=RSIStrategy(), trade_amount: float=50.0, sleep_s: int=300, sandbox_mode: bool=True):
    
    mode = "Sandbox" if sandbox_mode else "LIVE"
    print(f"[{mode}] Starting Uphold trading loop for {symbol} on {timeframe}.")
    
    uphold_ex = get_trading_exchange(sandbox=sandbox_mode)
    data_ex = get_data_exchange()

    while True:
        try:
            # 1. Get price data from Binance
            ohlcv = data_ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            df = __import__("pandas").DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")

            # 2. Generate signal
            sig = strategy.generate_signals(df)
            last_sig = int(sig.iloc[-1]) if len(sig) else 0

            # 3. Get Uphold balance
            cards = uphold_ex.get_cards()
            quote_currency = symbol.split('/')[1]
            base_currency = symbol.split('/')[0]
            
            quote_card = next((c for c in cards if c['currency'] == quote_currency), None)
            base_card = next((c for c in cards if c['currency'] == base_currency), None)
            
            quote_balance = float(quote_card['available']) if quote_card else 0
            base_balance = float(base_card['available']) if base_card else 0

            print(f"[{mode}][{symbol}] Signal: {last_sig} | Uphold {quote_currency} Balance: {quote_balance} | Uphold {base_currency} Balance: {base_balance}")

            # 4. Execute trade on Uphold
            if last_sig == 1 and quote_card and quote_balance >= trade_amount:
                print(f"[{mode}][{symbol}] BUY signal received. Placing order on Uphold.")
                txn = uphold_ex.create_transaction(quote_card['id'], base_currency, trade_amount, quote_currency)
                print(f"[{mode}][{symbol}] Transaction created: {txn['id']}")

            elif last_sig == -1 and base_card and base_balance > 0:
                print(f"[{mode}][{symbol}] SELL signal received. Placing order on Uphold.")
                txn = uphold_ex.create_transaction(base_card['id'], quote_currency, base_balance, base_currency)
                print(f"[{mode}][{symbol}] Transaction created: {txn['id']}")

        except Exception as e:
            print(f"[{mode}][{symbol}] An error occurred: {e}")

        time.sleep(sleep_s)
