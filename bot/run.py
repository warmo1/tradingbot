import argparse
import sqlite3
import time
import json
from .config import cfg
from .providers.binance_data import BinanceData
from .providers.uphold_exec import create_market_exchange
from .symbols import binance_symbol, uphold_pair

def _ensure_candles_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS candles(
      exchange TEXT NOT NULL,
      symbol TEXT NOT NULL,
      timeframe TEXT NOT NULL,
      ts INTEGER NOT NULL,
      open REAL, high REAL, low REAL, close REAL, volume REAL,
      PRIMARY KEY(exchange, symbol, timeframe, ts)
    )""")
    conn.commit()

def _insert_klines(conn: sqlite3.Connection, exchange: str, symbol_ui: str, tf: str, klines: list[list]):
    _ensure_candles_table(conn)
    rows = [
        (exchange, symbol_ui, tf, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        for k in klines
    ]
    conn.executemany("""INSERT OR REPLACE INTO candles
        (exchange,symbol,timeframe,ts,open,high,low,close,volume)
        VALUES (?,?,?,?,?,?,?,?,?)""", rows)
    conn.commit()

def cmd_datapull(args):
    from .db import get_conn
    conn = get_conn(cfg.database_url)
    bd = BinanceData()
    symbols = [s.strip() for s in args.symbols.split(",")]
    for ui_sym in symbols:
        b_sym = binance_symbol(ui_sym)
        start_ms = args.since_ms
        got_total = 0
        while True:
            # Binance's API can fetch in batches of 1000
            batch = bd.klines(b_sym, interval=args.timeframe, start_ms=start_ms, limit=1000)
            if not batch:
                break
            _insert_klines(conn, "binance", ui_sym, args.timeframe, batch)
            got_total += len(batch)
            start_ms = int(batch[-1][0]) + 1 # Use the timestamp of the last candle to get the next batch
            if len(batch) < 1000:
                break
            time.sleep(0.2)
        print(f"[datapull] {ui_sym} {args.timeframe}: {got_total} rows")

def cmd_uphold_trade(args):
    if not cfg.sandbox:
        print("Sandbox is off. Refusing to trade. Set SANDBOX=true in your .env file.")
        return
    if args.confirm != "TRADE":
        print("You must pass --confirm TRADE to proceed (Sandbox).")
        return
    
    from_cur, to_cur = uphold_pair(args.symbol)
    try:
        r = create_market_exchange(from_cur, to_cur, amount=str(args.amount))
        print("Uphold trade successful:")
        print(json.dumps(r, indent=2))
    except Exception as e:
        print(f"Uphold trade error: {e}")
        return # Stop if the trade failed
    
    # Log the successful trade to the local database
    try:
        from .db import get_conn
        conn = get_conn(cfg.database_url)
        conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts INTEGER NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
          qty REAL, price REAL, note TEXT
        )""")
        conn.execute("INSERT INTO paper_trades(ts,symbol,side,qty,price,note) VALUES (?,?,?,?,?,?)",
                     (int(time.time()*1000), args.symbol, args.side, args.amount, None, "uphold-sandbox"))
        conn.commit()
    except Exception as db_e:
        print(f"Failed to log trade to local DB: {db_e}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Trading Bot CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("datapull", help="Backfill OHLCV from Binance public API")
    sp.add_argument("--symbols", type=str, required=True, help="Comma-separated, e.g. BTC/USDT,ETH/USDT")
    sp.add_argument("--timeframe", type=str, default="1h", help="1m,5m,15m,1h,4h,1d...")
    sp.add_argument("--since-ms", type=int, default=None, dest="since_ms")
    sp.set_defaults(func=cmd_datapull)

    sp = sub.add_parser("uphold-trade", help="Sandbox market exchange via Uphold")
    sp.add_argument("--symbol", type=str, required=True, help="UI symbol, e.g. BTC/USDT")
    sp.add_argument("--side", type=str, default="buy")
    sp.add_argument("--amount", type=float, required=True, help="Amount in FROM currency (usually USDT)")
    sp.add_argument("--confirm", type=str, default="")
    sp.set_defaults(func=cmd_uphold_trade)
    
    args = p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    main()
