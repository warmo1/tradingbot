from flask import Flask, render_template, jsonify, request, redirect, url_for
from .config import cfg
from .db import get_conn, get_paper_trades_df, list_state_prefix, get_latest_close, paper_get, get_symbols, get_candles_df, paper_trade, paper_set
from .strategy import SMACrossoverStrategy
from .ai_analyzer import get_ai_analyzer
from .news import get_latest_crypto_news
import time

app = Flask(__name__)

# (Keep the existing _get_non_gemini_suggestions and _compute_summary functions)
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
    ] if realized else []

    position_rows = []
    for sym, qty in positions.items():
        if abs(qty) < 1e-12:
            continue
        lp = last_prices.get(sym)
        position_rows.append(dict(symbol=sym, qty=qty, last_price=lp, value=round(qty * (lp or 0), 2)))
    position_rows = sorted(position_rows, key=lambda r: r["value"], reverse=True)

    recent_trades = []
    if not trades.empty:
        t = trades.copy().sort_values("ts", ascending=False).head(50)
        for _, r in t.iterrows():
            recent_trades.append(dict(
                ts=str(r["ts"]),
                symbol=r["symbol"],
                side=r["side"],
                qty=float(r["qty"]),
                price=float(r["price"]),
                note=str(r.get("note") or ""),
            ))
    
    suggestions = _get_non_gemini_suggestions(conn)
    
    # --- New News and Insights ---
    headlines = get_latest_crypto_news()
    ai_analyzer = get_ai_analyzer() # Defaults to Gemini
    news_sentiment = ai_analyzer.get_news_sentiment(headlines) if headlines else "Could not fetch news."

    return dict(
        cash=round(cash, 2),
        equity=round(equity, 2),
        total_realized=round(total_realized, 2),
        total_mtm=round(total_mtm, 2),
        realized_rows=realized_rows,
        position_rows=position_rows,
        recent_trades=recent_trades,
        suggestions=suggestions,
        headlines=headlines,
        news_sentiment=news_sentiment
    )


@app.route("/")
def dashboard():
    data = _compute_summary()
    return render_template("dashboard.html", **data)

# (Keep the existing /trades and /api/gemini-suggestion routes)
@app.route("/trades")
def trades():
    data = _compute_summary()
    return render_template("trades.html", **data)

@app.route("/api/gemini-suggestion")
def gemini_suggestion():
    symbol = request.args.get('symbol', type=str)
    timeframe = request.args.get('timeframe', '1h', type=str)
    if not symbol:
        return jsonify({"error": "Symbol parameter is required."}), 400
    
    conn = get_conn(cfg.database_url)
    df = get_candles_df(conn, cfg.exchange, symbol, timeframe)
    if df.empty:
        return jsonify({"error": f"No data found for {symbol} on {timeframe} timeframe."}), 404
    
    ai_analyzer = get_ai_analyzer() # Defaults to Gemini
    suggestion = ai_analyzer.get_trade_suggestion(symbol, df)
    return jsonify({"suggestion": suggestion})


# --- New Route for Dashboard Trading ---
@app.route("/trade/buy", methods=["POST"])
def buy_from_dashboard():
    symbol = request.form['symbol']
    cash_per_trade = 100.0 # You can make this configurable
    
    conn = get_conn(cfg.database_url)
    price = get_latest_close(conn, cfg.exchange, symbol)
    if not price:
        return "Could not get latest price.", 400

    cash = float(paper_get(conn, "cash", "0"))
    if cash < cash_per_trade:
        return "Not enough cash.", 400

    qty = cash_per_trade / price
    new_cash = cash - cash_per_trade
    
    pos_key = f"pos:{symbol}"
    current_qty = float(paper_get(conn, pos_key, "0"))
    new_qty = current_qty + qty

    paper_set(conn, "cash", str(new_cash))
    paper_set(conn, pos_key, str(new_qty))
    paper_trade(conn, int(time.time() * 1000), symbol, "buy", qty, price, note="Dashboard BUY")

    return redirect(url_for("dashboard"))


def create_app():
    return app
