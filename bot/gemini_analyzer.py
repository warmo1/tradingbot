import google.generativeai as genai
from .config import cfg

def get_gemini_sentiment(headlines: list[str]) -> str:
    """
    Analyzes the sentiment of a list of news headlines using the Gemini API.
    """
    if not cfg.gemini_api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    genai.configure(api_key=cfg.gemini_api_key)
    model = genai.GenerativeModel('gemini-pro')

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
