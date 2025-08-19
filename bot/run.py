import argparse
from .config import cfg
from .db import get_conn, init_schema
from .discover import discover_markets
from .data import ingest_candles
from .backtest import run_backtest
from .paper import paper_loop
from .exchange import get_exchange
from .strategy import SMACrossoverStrategy, RSIStrategy
from .gemini_analyzer import get_gemini_sentiment

def cmd_discover(args):
    conn = get_conn(cfg.database_url)
    init_schema(conn)
    syms = discover_markets(cfg.database_url, quote=args.quote)
    print(f"New symbols found: {len(syms)} on {cfg.exchange}" + (f" with quote {args.quote}" if args.quote else ""))
    for s in syms[:50]:
        print(" ", s)
    if len(syms) > 50:
        print(" ...")

def cmd_ingest(args):
    ingest_candles(cfg.database_url, timeframe=args.timeframe, limit=args.limit, quote=args.quote, top_by_volume=args.top)
    print("Done ingest.")

def cmd_backtest(args):
    results, summary = run_backtest(cfg.database_url, timeframe=args.timeframe, fast=args.fast, slow=args.slow, quote=args.quote, top=args.top)
    if summary.empty:
        print("No data to backtest. Ingest candles first.")
        return
    print(summary.to_string(index=False))

def cmd_paper(args):
    symbol = args.symbol
    if not symbol:
        ex = get_exchange()
        tickers = ex.fetch_tickers()
        liquid = sorted(
            [s for s, t in tickers.items() if s.endswith(f"/{args.quote}")],
            key=lambda s: (tickers[s].get("quoteVolume") or 0),
            reverse=True
        )
        if not liquid:
            print("Could not pick a symbol automatically. Specify --symbol.")
            return
        symbol = liquid[0]
        print(f"[paper] Auto-selected symbol: {symbol}")

    strategy_map = {
        "sma_crossover": SMACrossoverStrategy(fast=args.fast, slow=args.slow),
        "rsi": RSIStrategy(rsi_period=args.rsi_period, rsi_oversold=args.rsi_oversold, rsi_overbought=args.rsi_overbought),
    }
    strategy = strategy_map.get(args.strategy)
    if not strategy:
        print(f"Invalid strategy: {args.strategy}")
        return

    paper_loop(
        cfg.database_url,
        symbol,
        timeframe=args.timeframe,
        strategy=strategy,
        cash_per_trade=args.cash,
        stop_loss_pct=args.stop_loss,
        take_profit_pct=args.take_profit,
        sleep_s=args.sleep
    )

def cmd_live(args):
    if args.confirm != "TRADE":
        print("You must pass --confirm TRADE to enable live orders.")
        return
    symbol = args.symbol
    if not symbol:
        print("Specify --symbol like BTC/USDT for live mode.")
        return
    from .live import live_loop
    live_loop(symbol=symbol, timeframe=args.timeframe, fast=args.fast, slow=args.slow, cash_per_trade=args.cash, sleep_s=args.sleep, confirm=True)

def cmd_gemini(args):
    headlines = [
        "Bitcoin surges past $70,000, setting new all-time high.",
        "Ethereum developers announce major upgrade to the network.",
        "SEC delays decision on another spot Bitcoin ETF application.",
    ]
    sentiment = get_gemini_sentiment(headlines)
    print("--- Gemini Sentiment Analysis ---")
    print(sentiment)

def main(argv=None):
    p = argparse.ArgumentParser(description="Crypto Bot (Starter)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # Discover command
    sp = sub.add_parser("discover", help="Discover and store markets (symbols)")
    sp.add_argument("--quote", type=str, default=None, help="Filter by quote currency (e.g., USDT)")
    sp.set_defaults(func=cmd_discover)

    # Ingest command
    sp = sub.add_parser("ingest", help="Fetch and store historical candles")
    sp.add_argument("--timeframe", type=str, default="1h")
    sp.add_argument("--limit", type=int, default=500)
    sp.add_argument("--quote", type=str, default=None, help="Filter to symbols with this quote")
    sp.add_argument("--top", type=int, default=None, help="Limit to top N symbols by volume (uses exchange tickers)")
    sp.set_defaults(func=cmd_ingest)

    # Backtest command
    sp = sub.add_parser("backtest", help="Run SMA-crossover backtest")
    sp.add_argument("--timeframe", type=str, default="1h")
    sp.add_argument("--fast", type=int, default=20)
    sp.add_argument("--slow", type=int, default=50)
    sp.add_argument("--quote", type=str, default=None)
    sp.add_argument("--top", type=int, default=20)
    sp.set_defaults(func=cmd_backtest)

    # Paper command
    sp = sub.add_parser("paper", help="Run paper-trading loop")
    sp.add_argument("--symbol", type=str, default=None, help="Symbol like BTC/USDT (auto-picked if omitted + --quote)")
    sp.add_argument("--quote", type=str, default="USDT")
    sp.add_argument("--timeframe", type=str, default="1m")
    sp.add_argument("--strategy", type=str, default="sma_crossover", choices=["sma_crossover", "rsi"], help="Trading strategy to use")
    sp.add_argument("--fast", type=int, default=10, help="Fast SMA period")
    sp.add_argument("--slow", type=int, default=30, help="Slow SMA period")
    sp.add_argument("--rsi-period", type=int, default=14)
    sp.add_argument("--rsi-oversold", type=int, default=30)
    sp.add_argument("--rsi-overbought", type=int, default=70)
    sp.add_argument("--cash", type=float, default=100.0, help="Cash to deploy per trade")
    sp.add_argument("--stop-loss", type=float, default=0.05, help="Stop-loss percentage (e.g., 0.05 for 5%)")
    sp.add_argument("--take-profit", type=float, default=0.1, help="Take-profit percentage (e.g., 0.1 for 10%)")
    sp.add_argument("--sleep", type=int, default=60, help="Seconds between loops")
    sp.set_defaults(func=cmd_paper)

    # Live command
    sp = sub.add_parser("live", help="(DANGER) Live trading loop (market orders). Use at your own risk.")
    sp.add_argument("--symbol", type=str, required=
