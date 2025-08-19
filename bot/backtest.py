from dataclasses import dataclass
import pandas as pd
from typing import Tuple, List
from .db import get_conn, get_candles_df, get_symbols
from .config import cfg
from .strategy import sma_crossover, position_changes

@dataclass
class BTResult:
    symbol: str
    trades: int
    return_pct: float
    max_dd_pct: float
    equity_curve: pd.Series

def run_backtest(database_url: str, timeframe: str="1h", fast: int=20, slow: int=50, quote: str | None = None, top: int | None = 20) -> Tuple[List[BTResult], pd.DataFrame]:
    conn = get_conn(database_url)
    symbols = get_symbols(conn, cfg.exchange, quote=quote)
    results: List[BTResult] = []

    for symbol in symbols[: (top or len(symbols)) ]:
        df = get_candles_df(conn, cfg.exchange, symbol, timeframe)
        if df.empty or len(df) < max(fast, slow) + 2:
            continue
        sig = sma_crossover(df, fast=fast, slow=slow)
        changes = position_changes(sig)
        df["ret"] = df["close"].pct_change().fillna(0)
        pos = sig.shift(1).fillna(0)  # hold prior bar's signal
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
    summary = pd.DataFrame(rows).sort_values("return_pct", ascending=False).reset_index(drop=True)
    return results, summary
