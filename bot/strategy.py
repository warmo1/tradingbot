import pandas as pd
from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        pass

class SMACrossoverStrategy(Strategy):
    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Returns signal series: 1 for long, 0 for flat. No shorting."""
        if df.empty:
            return pd.Series(dtype=float)
        fast_ma = df['close'].rolling(self.fast, min_periods=self.fast).mean()
        slow_ma = df['close'].rolling(self.slow, min_periods=self.slow).mean()
        signal = (fast_ma > slow_ma).astype(int)
        return signal

class RSIStrategy(Strategy):
    def __init__(self, rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Returns signal series: 1 for long, -1 for short, 0 for flat."""
        if df.empty:
            return pd.Series(dtype=float)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        signal = pd.Series(0, index=df.index)
        signal[rsi < self.rsi_oversold] = 1
        signal[rsi > self.rsi_overbought] = -1
        return signal

def position_changes(signal: pd.Series) -> pd.Series:
    if signal.empty:
        return signal
    return signal.diff().fillna(0)
