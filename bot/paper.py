import time
from .db import get_conn, get_candles_df, paper_get, paper_set, paper_trade
from .config import cfg
from .strategy import SMACrossoverStrategy

def _now_ms() -> int:
    return int(time.time() * 1000)

def paper_loop(database_url: str, symbol: str, timeframe: str="1m", strategy: SMACrossoverStrategy = SMACrossoverStrategy(), cash_per_trade: float=100.0, stop_loss_pct: float=0.05, take_profit_pct: float=0.1, sleep_s: int=60):
    conn = get_conn(database_url)
    pos_key = f"pos:{symbol}"
    cash_key = "cash"
    cash = float(paper_get(conn, cash_key, default=str(cfg.paper_starting_cash)))
    pos_qty = float(paper_get(conn, pos_key, default="0"))
    entry_price = float(paper_get(conn, f"entry_price:{symbol}", default="0"))
    
    print(f"[paper] starting cash £{cash:.2f}, position {symbol} qty={pos_qty}")

    last_ts = None
    while True:
        df = get_candles_df(conn, cfg.exchange, symbol, timeframe)
        if df.empty:
            print(f"[paper] no candles for {symbol} {timeframe}. Waiting...")
            time.sleep(sleep_s)
            continue
        ts = int(df.index[-1].timestamp() * 1000)
        if ts == last_ts:
            time.sleep(sleep_s)
            continue
        last_ts = ts
        
        sig = strategy.generate_signals(df)
        sig_last = int(sig.iloc[-1]) if len(sig) else 0
        price = float(df['close'].iloc[-1])
        
        # Risk management
        if pos_qty > 0:
            if price <= entry_price * (1 - stop_loss_pct):
                print(f"[paper] STOP-LOSS triggered for {symbol}")
                sig_last = 0
            elif price >= entry_price * (1 + take_profit_pct):
                print(f"[paper] TAKE-PROFIT triggered for {symbol}")
                sig_last = 0

        if sig_last == 1 and cash > 0:
            qty = max(0.0, (cash_per_trade / price))
            if qty > 0:
                cash -= qty * price
                pos_qty += qty
                entry_price = price
                paper_set(conn, cash_key, str(cash))
                paper_set(conn, pos_key, str(pos_qty))
                paper_set(conn, f"entry_price:{symbol}", str(entry_price))
                paper_trade(conn, ts=_now_ms(), symbol=symbol, side="buy", qty=qty, price=price, note="Strategy BUY")
                print(f"[paper] BUY {symbol} qty={qty:.6f} @ {price:.4f} | cash £{cash:.2f}")
        elif sig_last == 0 and pos_qty > 0:
            qty = pos_qty
            cash += qty * price
            pos_qty = 0.0
            entry_price = 0.0
            paper_set(conn, cash_key, str(cash))
            paper_set(conn, pos_key, str(pos_qty))
            paper_set(conn, f"entry_price:{symbol}", str(entry_price))
            paper_trade(conn, ts=_now_ms(), symbol=symbol, side="sell", qty=qty, price=price, note="Strategy SELL")
            print(f"[paper] SELL {symbol} qty={qty:.6f} @ {price:.4f} | cash £{cash:.2f}")
        else:
            print(f"[paper] HOLD {symbol} @ {price:.4f} | cash £{cash:.2f}, pos {pos_qty:.6f}")

        time.sleep(sleep_s)
