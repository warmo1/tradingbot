from flask import Flask, render_template, jsonify, request
import subprocess
import sys
import pandas as pd
import plotly.graph_objects as go
from .config import cfg
from .db import get_conn, get_symbols, get_candles_df

app = Flask(__name__)

@app.route("/")
def dashboard():
    conn = get_conn(cfg.database_url)
    symbols = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    return render_template("dashboard.html", symbols=symbols)

@app.route("/coins")
def coins_page():
    conn = get_conn(cfg.database_url)
    symbols = get_symbols(conn, cfg.exchange, quote=cfg.default_quote)
    return render_template("coins.html", symbols=symbols)
    
@app.route("/chart/<symbol>")
def chart_page(symbol):
    symbol = symbol.replace('-', '/')
    conn = get_conn(cfg.database_url)
    df = get_candles_df(conn, cfg.exchange, symbol, "1h")
    
    chart_html = "<div>No data available to plot chart.</div>"
    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'])])
        fig.update_layout(xaxis_rangeslider_visible=False, title=f"{symbol} 1h Chart")
        chart_html = fig.to_html(full_html=False)
        
    return render_template("chart.html", symbol=symbol, chart_html=chart_html)

# --- This endpoint now starts the new trader.py script ---
@app.route("/api/start-trader", methods=["POST"])
def start_trader():
    symbol = request.form['symbol']
    mode = request.form['mode'] # 'sandbox' or 'live'
    if not symbol or not mode:
        return jsonify({"status": "error", "message": "Symbol and mode are required."}), 400

    try:
        command = [sys.executable, "-m", "bot.run", "trader", "--symbol", symbol]
        if mode == "sandbox":
            command.append("--sandbox")
            
        subprocess.Popen(command)
        return jsonify({"status": "success", "message": f"Started {mode} trader for {symbol}."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def create_app():
    return app
