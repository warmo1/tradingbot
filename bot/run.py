import argparse
from .config import cfg
from .db import get_conn, init_schema, get_candles_df
from .discover import discover_markets
from .data import ingest_candles
from .backtest import run_backtest
from .paper import paper_loop
from .exchange import get_exchange
from .strategy import SMACrossoverStrategy, RSIStrategy
from .gemini_analyzer import get_gemini_sentiment, get_gemini_trade_suggestion

import os
import json
import time
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

# (Keep all the existing cmd_ functions like cmd_discover, cmd_ingest, etc.)

# -----------------
# Helpers & storage
# -----------------
WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "watchlist.json")
NEWS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "news_cache.json")

DEFAULT_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "https://cointelegraph.com/rss",
    "https://www.theblock.co/rss",
]


def _load_watchlist():
    if not os.path.exists(WATCHLIST_PATH):
        return []
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_watchlist(symbols):
    try:
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(list(set(symbols))), f, indent=2)
    except Exception as e:
        print(f"[watchlist] failed to save: {e}")


def _fetch_rss(url, timeout=10):
    # Very small RSS fetcher using stdlib only
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            xml_data = resp.read()
    except (URLError, HTTPError) as e:
        print(f"[news] fetch error for {url}: {e}")
        return []
    try:
        root = ET.fromstring(xml_data)
        # Try common RSS layout
        items = []
        for item in root.findall('.//item'):
            title = (item.findtext('title') or '').strip()
            link = (item.findtext('link') or '').strip()
            pub = item.findtext('pubDate') or ''
            items.append({"title": title, "url": link, "published": pub})
        if items:
            return items
        # Some Atom feeds
        for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
            title = (entry.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
            link_el = entry.find('{http://www.w3.org/2005/Atom}link')
            link = link_el.get('href') if link_el is not None else ''
            pub = entry.findtext('{http://www.w3.org/2005/Atom}updated') or ''
            items.append({"title": title, "url": link, "published": pub})
        return items
    except ET.ParseError as e:
        print(f"[news] parse error for {url}: {e}")
        return []


def _load_news_cache():
    if not os.path.exists(NEWS_CACHE_PATH):
        return []
    try:
        with open(NEWS_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_news_cache(items):
    try:
        with open(NEWS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        print(f"[news] failed to save cache: {e}")

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
            key=lambda s: (tickers[s].get("quoteVolume") or tickers[s].get("baseVolume") or 0),
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

def cmd_gemini_trade(args):
    conn = get_conn(cfg.database_url)
    df = get_candles_df(conn, cfg.exchange, args.symbol, args.timeframe)
    if df.empty:
        print(f"No data found for {args.symbol} on {args.timeframe} timeframe. Ingest data first.")
        return
    print(f"Analyzing {args.symbol} on the {args.timeframe} timeframe...")
    suggestion = get_gemini_trade_suggestion(args.symbol, df)
    print("\n--- Gemini Trade Suggestion ---")
    print(suggestion)

def cmd_watch(args):
    symbols = _load_watchlist()
    if args.add:
        for s in args.add.split(','):
            s = s.strip()
            if s:
                symbols.append(s)
        _save_watchlist(symbols)
        symbols = _load_watchlist()
        print("Added. Current watchlist:", ", ".join(symbols) or "(empty)")
        return
    if args.clear:
        _save_watchlist([])
        print("Watchlist cleared.")
        return
    print("Current watchlist:", ", ".join(symbols) or "(empty)")


def cmd_news(args):
    feeds = DEFAULT_FEEDS if not args.feed else [args.feed]
    all_items = []
    for u in feeds:
        items = _fetch_rss(u)
        if items:
            all_items.extend(items)
    # De-dup by URL
    seen = set()
    uniq = []
    for it in all_items:
        url = it.get("url")
        if url and url not in seen:
            uniq.append(it)
            seen.add(url)
    _save_news_cache(uniq)
    print(f"Fetched {len(uniq)} news items.")


def cmd_insights(args):
    # Build headlines list and pass to Gemini sentiment/suggestion functions we already have
    items = _load_news_cache()
    if not items:
        print("No news cached. Run: python -m bot.run news")
        return
    headlines = [i.get('title') for i in items if i.get('title')] [:30]
    print("Summarising ~", len(headlines), "headlines with Gemini...")
    try:
        summary = get_gemini_sentiment(headlines)
    except Exception as e:
        print("Gemini error:", e)
        return
    print("\n--- Insight (Gemini) ---\n")
    print(summary)
    # Optionally save a lightweight insight JSON for the dashboard to read later
    insight_rec = {
        "created": datetime.now(timezone.utc).isoformat(),
        "headline": "News digest",
        "summary": summary,
        "count": len(headlines)
    }
    insight_path = os.path.join(os.path.dirname(__file__), "insights_latest.json")
    try:
        with open(insight_path, "w", encoding="utf-8") as f:
            json.dump(insight_rec, f, indent=2)
        print(f"Saved: {insight_path}")
    except Exception as e:
        print("Failed to save insight:", e)


def cmd_scheduler(args):
    """Minimal scheduler loop using stdlib only (no APScheduler dependency)."""
    interval_ingest = args.ingest_every
    interval_news = args.news_every
    last_ingest = 0
    last_news = 0
    quote = args.quote or "USDT"
    tf = args.timeframe
    limit = args.limit
    top = args.top
    feeds_info = "default feeds"
    print(f"[scheduler] running… ingest every {interval_ingest}s, news every {interval_news}s, timeframe={tf}, top={top}, quote={quote}")
    try:
        while True:
            now = time.time()
            if now - last_ingest >= interval_ingest:
                try:
                    # keep markets fresh and ingest candles for most liquid
                    discover_markets(cfg.database_url, quote=quote)
                    ingest_candles(cfg.database_url, timeframe=tf, limit=limit, quote=quote, top_by_volume=top)
                    print("[scheduler] ingest tick done")
                except Exception as e:
                    print("[scheduler] ingest error:", e)
                last_ingest = now
            if now - last_news >= interval_news:
                try:
                    cmd_news(argparse.Namespace(feed=None))
                    print("[scheduler] news tick done")
                except Exception as e:
                    print("[scheduler] news error:", e)
                last_news = now
            time.sleep(1)
    except KeyboardInterrupt:
        print("[scheduler] stopped")

def main(argv=None):
    p = argparse.ArgumentParser(description="Crypto Bot (Starter)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # (Keep all the existing parsers: discover, ingest, backtest, paper, live, gemini)
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
    sp.add_argument("--symbol", type=str, required=True, help="Symbol like BTC/USDT")
    sp.add_argument("--timeframe", type=str, default="1m")
    sp.add_argument("--fast", type=int, default=10)
    sp.add_argument("--slow", type=int, default=30)
    sp.add_argument("--cash", type=float, default=50.0, help="Approx quote to deploy per trade")
    sp.add_argument("--sleep", type=int, default=60)
    sp.add_argument("--confirm", type=str, default="", help="Must equal 'TRADE' to run")
    sp.set_defaults(func=cmd_live)

    # Gemini command
    sp = sub.add_parser("gemini", help="Run Gemini sentiment analysis")
    sp.set_defaults(func=cmd_gemini)

    # NEW Gemini Trade command
    sp = sub.add_parser("gemini-trade", help="Get a trade suggestion from Gemini based on market data")
    sp.add_argument("--symbol", type=str, required=True, help="Symbol to analyze, e.g., BTC/USDT")
    sp.add_argument("--timeframe", type=str, default="1h", help="Timeframe to analyze, e.g., 1h, 15m, 1d")
    sp.set_defaults(func=cmd_gemini_trade)

    # Watchlist
    sp = sub.add_parser("watch", help="Manage the watchlist (stored locally as JSON)")
    sp.add_argument("--add", type=str, help="Comma-separated symbols to add, e.g. BTC/USDT,ETH/USDT")
    sp.add_argument("--clear", action="store_true", help="Clear the entire watchlist")
    sp.set_defaults(func=cmd_watch)

    # News fetch
    sp = sub.add_parser("news", help="Fetch crypto news into local cache (std RSS)")
    sp.add_argument("--feed", type=str, default=None, help="Single feed URL to fetch (otherwise defaults)")
    sp.set_defaults(func=cmd_news)

    # Insights via Gemini/OpenAI
    sp = sub.add_parser("insights", help="Summarise recent news into a dashboard-ready insight")
    sp.set_defaults(func=cmd_insights)

    # Minimal scheduler
    sp = sub.add_parser("scheduler", help="Run periodic ingest + news (simple loop)")
    sp.add_argument("--timeframe", type=str, default="1m")
    sp.add_argument("--limit", type=int, default=200)
    sp.add_argument("--quote", type=str, default="USDT")
    sp.add_argument("--top", type=int, default=20)
    sp.add_argument("--news-every", type=int, default=900, dest="news_every")
    sp.add_argument("--ingest-every", type=int, default=300, dest="ingest_every")
    sp.set_defaults(func=cmd_scheduler)

    args = p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    main()
