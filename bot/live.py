import time
from .exchange import get_exchange
from .db import get_conn, paper_get, paper_set
from .strategy import sma_crossover
from .config import cfg

def _now_ms():
    return int(time.time() * 1000)

def _quantize_amount(ex, symbol, amount):
    m = ex.market(symbol)
    step = m.get('precision', {}).get('amount', None)
    if step is None:
        lot = m.get('lot', None)
        if lot:
            return max(0.0, (amount // lot) * lot)
        return amount
    decimals = int(step)
    return float(f"{amount:.{decimals}f}")

def live_loop(symbol: str, timeframe: str="1m", fast: int=10, slow: int=30, cash_per_trade: float=50.0, sleep_s: int=60, confirm: bool=False):
    if not confirm:
        print("Refusing to place live orders without --confirm TRADE.")
        return

    ex = get_exchange()
    markets = ex.load_markets()
    if symbol not in markets:
        raise ValueError(f"Symbol {symbol} not available on {cfg.exchange}")

    conn = get_conn(cfg.database_url)
    pos_key = f"live:pos:{symbol}"
    pos_qty = float(paper_get(conn, pos_key, default="0"))

    print(f"[live] Starting live loop on {cfg.exchange} {symbol}, pos={pos_qty}")
    while True:
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=max(slow*2, 100))
        except Exception as e:
            print(f"[live] fetch_ohlcv error: {e}")
            time.sleep(sleep_s)
            continue
        import pandas as pd
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"]).set_index("ts")
        sig = sma_crossover(df, fast=fast, slow=slow)
        sig_last = int(sig.iloc[-1]) if len(sig) else 0

        ticker = ex.fetch_ticker(symbol)
        price = float(ticker.get("last") or ticker.get("close") or df["close"].iloc[-1])

        if sig_last == 1 and pos_qty <= 0:
            quote = cash_per_trade
            amount = quote / price
            amount = _quantize_amount(ex, symbol, amount)
            if amount > 0:
                try:
                    order = ex.create_order(symbol, "market", "buy", amount)
                    pos_qty += amount
                    paper_set(conn, pos_key, str(pos_qty))
                    print(f"[live] BUY {symbol} {amount} @ ~{price} order_id={order.get('id')}")
                except Exception as e:
                    print(f"[live] BUY failed: {e}")
        elif sig_last == 0 and pos_qty > 0:
            amount = pos_qty
            amount = _quantize_amount(ex, symbol, amount)
            if amount > 0:
                try:
                    order = ex.create_order(symbol, "market", "sell", amount)
                    pos_qty = 0.0
                    paper_set(conn, pos_key, str(pos_qty))
                    print(f"[live] SELL {symbol} {amount} @ ~{price} order_id={order.get('id')}")
                except Exception as e:
                    print(f"[live] SELL failed: {e}")
        else:
            print(f"[live] HOLD {symbol} @ {price}")

        time.sleep(sleep_s)
