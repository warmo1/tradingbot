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

# ... (rest of the cmd_ functions)

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

    # ... (discover, ingest, backtest commands)

    sp = sub.add_parser("paper", help="Run paper-trading loop")
    sp.add_argument("--symbol", type=str, default=None, help="Symbol like BTC/USDT (auto-picked if omitted + --quote)")
    sp.add_argument("--quote", type=str, default="USDT")
    sp.add_argument("--timeframe", type=str, default="1m")
    sp.add_argument("--strategy", type=str, default="sma_crossover", choices=["sma_crossover", "rsi"], help="Trading strategy to use")
    # SMA Crossover args
    sp.add_argument("--fast", type=int, default=10)
    sp.add_argument("--slow", type=int, default=30)
    # RSI args
    sp.add_argument("--rsi-period", type=int, default=14)
    sp.add_argument("--rsi-oversold", type=int, default=30)
    sp.add_argument("--rsi-overbought", type=int, default=70)

    sp.add_argument("--cash", type=float, default=100.0, help="Cash to deploy per trade")
    sp.add_argument("--stop-loss", type=float, default=0.05, help="Stop-loss percentage (e.g., 0.05 for 5%)")
    sp.add_argument("--take-profit", type=float, default=0.1, help="Take-profit percentage (e.g., 0.1 for 10%)")
    sp.add_argument("--sleep", type=int, default=60, help="Seconds between loops")
    sp.set_defaults(func=cmd_paper)
    
    sp = sub.add_parser("gemini", help="Run Gemini sentiment analysis")
    sp.set_defaults(func=cmd_gemini)


    # ... (live command)

    args = p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    main()
