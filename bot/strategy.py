import pandas as pd

def sma_crossover(df: pd.DataFrame, fast: int=20, slow: int=50) -> pd.Series:
    """Returns signal series: 1 for long, 0 for flat. No shorting."""
    if df.empty:
        return pd.Series(dtype=float)
    fast_ma = df['close'].rolling(fast, min_periods=fast).mean()
    slow_ma = df['close'].rolling(slow, min_periods=slow).mean()
    signal = (fast_ma > slow_ma).astype(int)
    return signal

def position_changes(signal: pd.Series) -> pd.Series:
    if signal.empty:
        return signal
    return signal.diff().fillna(0)
