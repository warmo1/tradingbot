import argparse
from .config import cfg
from .db import get_conn, init_schema
from .discover import discover_markets
from .data import ingest_candles
from .trader import trading_loop # Import the new trading loop

def cmd_discover(args):
    conn = get_conn(cfg.database_url)
    init_schema(conn)
    syms = discover_markets(cfg.database_url, quote=args.quote)
    print(f"New symbols found: {len(syms)} on {cfg.exchange}")

def cmd_ingest(args):
    ingest_candles(cfg.database_url, timeframe=args.timeframe, limit=args.limit, quote=args.quote, top_by_volume=args.top)
    print("Done ingest.")

def cmd_trader(args):
    trading_loop(symbol=args.symbol, sandbox_mode=args.sandbox)

def main(argv=None):
    p = argparse.ArgumentParser(description="Uphold Trading Bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("discover", help="Discover and store markets from Uphold")
    sp.add_argument("--quote", type=str, default="USD")
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("ingest", help="Fetch and store historical candles")
    sp.add_argument("--timeframe", type=str, default="1h")
    sp.add_argument("--limit", type=int, default=500)
    sp.add_argument("--quote", type=str, default="USD")
    sp.add_argument("--top", type=int, default=50)
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("trader", help="Run the trading loop for a single symbol")
    sp.add_argument("--symbol", type=str, required=True, help="Symbol to trade, e.g., BTC/USD")
    sp.add_argument("--sandbox", action="store_true", help="Run in sandbox mode")
    sp.set_defaults(func=cmd_trader)

    args = p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    main()
