from flask import Flask, render_template, jsonify, request, redirect, url_for
import subprocess
import sys
from .config import cfg
from .db import get_conn, get_paper_trades_df, list_state_prefix, get_latest_close, paper_get, get_all_insights, paper_trade, paper_set, get_symbols, get_backtest_results
from .ai_analyzer import get_ai_analyzer
from .actions import run_backtest_for_symbol

app = Flask(__name__)

# (_compute_summary remains largely the same)
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
    
    insights = get_all_insights(conn)

    return dict(
        cash=round(cash, 2),
        equity=round(equity, 2),
        total_realized=round(total_realized, 2),
        total_mtm=round(total_mtm, 2),
        realized_rows=realized_rows,
        position_rows=position_rows,
        recent_trades=recent_trades,
        insights=insights
    )

@app.route("/")
def dashboard():
    data = _compute_summary()
    return render_template("dashboard.html", **data)
    
# --- New Portfolio Page ---
@app.route("/portfolio")
def portfolio_page():
    conn = get_conn(cfg.database_url)
    cash = float(paper_get(conn, "cash", str(cfg.paper_starting_cash)))
    symbols = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    insights = get_all_insights(conn)
    
    ai = get_ai_analyzer()
    portfolio_suggestion = ai.get_portfolio_suggestion(cash, symbols, insights)
    
    return render_template("portfolio.html", suggestion=portfolio_suggestion)

# --- New Coins and Backtesting Page ---
@app.route("/coins")
def coins_page():
    conn = get_conn(cfg.database_url)
    symbols = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    return render_template("coins.html", symbols=symbols)

# --- New Backtest Results Page ---
@app.route("/backtest-results/<symbol>")
def backtest_results_page(symbol):
    conn = get_conn(cfg.database_url)
    results = get_backtest_results(conn, symbol)
    return render_template("backtest_results.html", symbol=symbol, results=results)

# --- Fixed Trades Page ---
@app.route("/trades")
def trades():
    data = _compute_summary()
    return render_template("trades.html", **data)

# --- API Endpoints ---
@app.route("/api/run-backtest", methods=["POST"])
def api_run_backtest():
    symbol = request.form.get("symbol")
    strategy = request.form.get("strategy")
    if not symbol or not strategy:
        return jsonify({"status": "error", "message": "Symbol and strategy are required"}), 400
    
    run_backtest_for_symbol(symbol, strategy=strategy)
    return jsonify({"status": "success", "message": f"Backtest for {symbol} with {strategy} strategy is complete. Refresh to see results."})

@app.route("/api/start-bot", methods=["POST"])
def start_bot():
    symbol = request.form['symbol']
    if not symbol:
        return jsonify({"status": "error", "message": "Symbol is required."}), 400

    try:
        command = [sys.executable, "-m", "bot.run", "paper", "--symbol", symbol]
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return jsonify({"status": "success", "message": f"Started paper trading bot for {symbol}."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def create_app():
    return app
