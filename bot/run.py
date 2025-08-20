import argparse
from .config import cfg
from .db import get_conn, init_schema, get_candles_df
from .discover import discover_markets
from .data import ingest_candles
from .backtest import run_backtest
from .paper import paper_loop
from .exchange import get_exchange
from .strategy import SMACrossoverStrategy, RSIStrategy
from .ai_analyzer import get_ai_analyzer
from .news import get_latest_crypto_news

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
    # Pass the strategy arguments to the backtest function
    results, summary = run_backtest(
        database_url=cfg.database_url,
        timeframe=args.timeframe,
        strategy_name=args.strategy,
        fast=args.fast,
        slow=args.slow,
        rsi_period=args.rsi_period,
        rsi_oversold=args.rsi_oversold,
        rsi_overbought=args.rsi_overbought,
        quote=args.quote,
        top=args.top
    )
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
