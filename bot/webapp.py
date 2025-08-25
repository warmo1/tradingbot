from flask import Flask, render_template, jsonify, request, abort
import sqlite3
import json
import time
from .config import cfg
from .symbols import uphold_pair
from .providers.uphold_exec import create_market_exchange

app = Flask(__name__)

def _get_conn():
    from .db import get_conn
    c = get_conn(cfg.database_url)
    c.row_factory = sqlite3.Row
    return c

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/ohlcv")
def api_ohlcv():
    symbol = request.args.get("symbol", "BTC/USDT")
    tf = request.args.get("timeframe", "1h")
    limit = int(request.args.get("limit", "500"))
    conn = _get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS candles(
      exchange TEXT, symbol TEXT, timeframe TEXT, ts INTEGER,
      open REAL, high REAL, low REAL, close REAL, volume REAL,
      PRIMARY KEY(exchange,symbol,timeframe,ts)
    )""")
    rows = conn.execute("""SELECT ts, open, high, low, close
                           FROM candles
                           WHERE exchange=? AND symbol=? AND timeframe=?
                           ORDER BY ts DESC LIMIT ?""",
                        ("binance", symbol, tf, limit)).fetchall()
    rows = rows[::-1]
    data = [{"time": r['ts'] / 1000, "open": r['open'], "high": r['high'], "low": r['low'], "close": r['close']} for r in rows]
    return jsonify({"symbol": symbol, "timeframe": tf, "rows": data})

@app.route("/uphold_trade", methods=["POST"])
def uphold_trade():
    token = request.form.get("token", "")
    if cfg.admin_token and token != cfg.admin_token:
        return abort(403)
    if not cfg.sandbox:
        return abort(400, "Sandbox disabled.")
    
    symbol = request.form.get("symbol", "BTC/USDT")
    side = request.form.get("side", "buy")
    amount = float(request.form.get("amount", "10"))
    
    from_cur, to_cur = uphold_pair(symbol)
    
    try:
        resp = create_market_exchange(from_cur, to_cur, amount=str(amount))
        note = f"uphold-sandbox ok: {resp.get('status','ok')}"
    except Exception as e:
        note = f"uphold-sandbox error: {e}"
    
    conn = _get_conn()
    conn.execute("""CREATE TABLE IF NOT EXISTS paper_trades(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
      qty REAL, price REAL, note TEXT
    )""")
    conn.execute("INSERT INTO paper_trades(ts,symbol,side,qty,price,note) VALUES (?,?,?,?,?,?)",
                 (int(time.time()*1000), symbol, side, amount, None, note))
    conn.commit()
    return ("", 204)

def create_app():
    return app
