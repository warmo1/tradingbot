from dataclasses import dataclass
import pandas as pd
from typing import Tuple, List
from .db import get_conn, get_candles_df, get_symbols
from .config import cfg
from .strategy import SMACrossoverStrategy, RSIStrategy, position_changes

@dataclass
class BTResult:
    symbol: str
    trades: int
    return_pct: float
    max_dd_pct: float
    equity_curve: pd.Series

def run_backtest(
    database_url: str,
    timeframe: str="1h",
    strategy_name: str="sma_crossover",
    fast: int=20,
    slow: int=50,
    rsi_period: int=14,
    rsi_oversold: int=30,
    rsi_overbought: int=70,
    quote: str | None = None,
    top: int | None = 20,
    symbol_override: str | None = None
) -> Tuple[List[BTResult], pd.DataFrame]:
    conn = get_conn(database_url)
    
    # If a single symbol is provided, use it. Otherwise, get a list of symbols.
    if symbol_override:
        symbols = [symbol_override]
    else:
        symbols = get_symbols(conn, cfg.exchange, quote=quote)
    
    results: List[BTResult] = []

    if strategy_name == "sma_crossover":
        strategy = SMACrossoverStrategy(fast=fast, slow=slow)
    elif strategy_name == "rsi":
        strategy = RSIStrategy(rsi_period=rsi_period, rsi_oversold=rsi_oversold, rsi_overbought=rsi_overbought)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    # Use the 'top' parameter only when fetching a list of symbols
    symbols_to_run = symbols[: (top if not symbol_override else None) or len(symbols)]

    for symbol in symbols_to_run:
        df = get_candles_df(conn, cfg.exchange, symbol, timeframe)
        if df.empty or len(df) < max(fast, slow, rsi_period) + 2:
            continue

        sig = strategy.generate_signals(df)
        changes = position_changes(sig)
        df["ret"] = df["close"].pct_change().fillna(0)
        
        pos = sig.shift(1).fillna(0) 
        strat_ret = pos * df["ret"]
        
        equity = (1 + strat_ret).cumprod()
        ret_pct = (equity.iloc[-1] - 1) * 100.0
        
        roll_max = equity.cummax()
        dd = equity / roll_max - 1.0
        max_dd_pct = dd.min() * 100.0
        
        trades = int((changes != 0).sum())
        results.append(BTResult(symbol=symbol, trades=trades, return_pct=float(ret_pct), max_dd_pct=float(max_dd_pct), equity_curve=equity))

    rows = []
    for r in results:
        rows.append(dict(symbol=r.symbol, trades=r.trades, return_pct=round(r.return_pct, 2), max_dd_pct=round(r.max_dd_pct, 2)))
    
    if not rows:
        return results, pd.DataFrame()

    summary = pd.DataFrame(rows).sort_values("return_pct", ascending=False).reset_index(drop=True)
    return results, summary
