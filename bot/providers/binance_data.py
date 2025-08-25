from binance.spot import Spot as Binance
from ..config import cfg

class BinanceData:
    def __init__(self, base_url: str | None = None):
        self.client = Binance(base_url=(base_url or cfg.binance_base_url))

    def klines(self, symbol: str, interval: str="1h", start_ms: int | None=None, limit: int=1000):
        return self.client.klines(symbol=symbol, interval=interval, startTime=start_ms, limit=limit)

    def exchange_info(self):
        return self.client.exchange_info()
