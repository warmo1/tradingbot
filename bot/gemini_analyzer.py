import google.generativeai as genai
from .config import cfg
import pandas as pd

def get_gemini_sentiment(headlines: list[str]) -> str:
    """
    Analyzes the sentiment of a list of news headlines using the Gemini API.
    """
    if not cfg.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    genai.configure(api_key=cfg.gemini_api_key)
    # Use the official 2.5 Pro model name
    model = genai.GenerativeModel('gemini-2.5-pro')

    prompt = f"""
    Analyze the sentiment of the following cryptocurrency news headlines and classify it as 'bullish', 'bearish', or 'neutral'.
    Provide a brief justification for your classification.

    Headlines:
    - {'\n- '.join(headlines)}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error analyzing sentiment: {e}"

def get_gemini_trade_suggestion(symbol: str, df: pd.DataFrame) -> str:
    """
    Analyzes historical price data and provides a trade suggestion using the Gemini API.
    """
    if not cfg.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    genai.configure(api_key=cfg.gemini_api_key)
    # Use the official 2.5 Pro model name
    model = genai.GenerativeModel('gemini-2.5-pro')

    # Prepare the data for the prompt
    df_recent = df.tail(50) # Use the last 50 candles
    data_str = df_recent[['open', 'high', 'low', 'close', 'volume']].to_string()

    prompt = f"""
    You are a crypto trading analyst. Based on the following recent market data for {symbol},
    should I BUY, SELL, or HOLD?

    Provide a clear, one-word answer first (BUY, SELL, or HOLD), followed by a brief, data-driven justification for your choice.

    Recent Market Data:
    {data_str}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error getting trade suggestion: {e}"
