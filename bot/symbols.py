SYMBOL_MAP = {
    "BTC/USDT": {"binance": "BTCUSDT", "uphold_from": "USDT", "uphold_to": "BTC"},
    "ETH/USDT": {"binance": "ETHUSDT", "uphold_from": "USDT", "uphold_to": "ETH"},
    # Add more mappings here as needed
}

def binance_symbol(ui_symbol: str) -> str:
    return SYMBOL_MAP.get(ui_symbol, {}).get("binance") or ui_symbol.replace("/", "")

def uphold_pair(ui_symbol: str) -> tuple[str, str]:
    m = SYMBOL_MAP.get(ui_symbol)
    if not m:
        base, quote = ui_symbol.split("/")
        return quote, base # e.g., for BTC/USDT, from=USDT, to=BTC
    return m["uphold_from"], m["uphold_to"]
