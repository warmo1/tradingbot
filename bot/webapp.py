from flask import Flask, render_template, jsonify, request
from .config import cfg
from .db import get_conn, get_paper_trades_df, list_state_prefix, get_latest_close, paper_get, get_symbols, get_candles_df
from .strategy import SMACrossoverStrategy
from .gemini_analyzer import get_gemini_trade_suggestion

app = Flask(__name__)

def _get_non_gemini_suggestions(conn):
    """Generates a list of BUY/SELL/HOLD signals from the SMA strategy."""
    symbols = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    suggestions = []
    strategy = SMACrossoverStrategy(fast=10, slow=30) # Using paper trading defaults

    for symbol in symbols[:20]: # Limit to top 20 symbols for performance
        df = get_candles_df(conn, cfg.exchange, symbol, "1h")
        if df.empty or len(df) < 32:
            continue
        
        sig = strategy.generate_signals(df)
        last_sig = int(sig.iloc[-1]) if len(sig) else 0
        
        if last_sig == 1:
            suggestions.append({"symbol": symbol, "signal": "BUY"})
        elif last_sig == 0:
            # Optionally show sell signals if you have an open position
            # For now, we'll just show BUY or HOLD
            pass

    return suggestions

def _compute_summary():
    conn = get_conn(cfg.database_url)
    trades = get_paper_trades_df(conn)
    starting_cash = float(paper_get(conn, "cash", str(cfg.paper_starting_cash)))
    realized = {}
    positions = {}
    if not trades.empty:
        for _, row in trades.iterrows():
            sym = row["symbol"]
            qty = float(row["qty"])
            price = float(row["price"])
            side = row["side"]
            realized.setdefault(sym, 0.0)
            positions.setdefault(sym, 0.0)
            if side == "buy":
                realized[sym] -= qty * price
                positions[sym] += qty
            elif side == "sell":
                realized[sym] += qty * price
                positions[sym] -= qty

    for key, val in list_state_prefix(conn, "pos:"):
        sym = key.split("pos:")[1]
        positions[sym] = float(val)

    mtm = {}
    last_prices = {}
    for sym, qty in positions.items():
        if abs(qty) < 1e-12:
            continue
        lp = get_latest_close(conn, cfg.exchange, sym)
        if lp is None:
            continue
        last_prices[sym] = lp
        mtm[sym] = qty * lp

    cash = float(paper_get(conn, "cash", str(cfg.paper_starting_cash)) or cfg.paper_starting_cash)
    total_realized = sum(realized.values()) if realized else 0.0
    total_mtm = sum(mtm.values()) if mtm else 0.0
    equity = cash + total_mtm

    realized_rows = [
        dict(symbol=sym, realized_pnl=round(val, 2))
        for sym, val in sorted(realized.items(), key=lambda kv: kv[1], reverse=True)
    ] if realized else
