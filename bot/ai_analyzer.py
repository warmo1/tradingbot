from .config import cfg
import pandas as pd

# Abstract base class for different AI models
class AIAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_trade_suggestion(self, symbol: str, df: pd.DataFrame) -> str:
        raise NotImplementedError

    def get_news_sentiment(self, headlines: list[str]) -> str:
        raise NotImplementedError

# Gemini implementation
class GeminiAnalyzer(AIAnalyzer):
    def __init__(self, api_key):
        super().__init__(api_key)
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    def get_trade_suggestion(self, symbol: str, df: pd.DataFrame) -> str:
        df_recent = df.tail(50)
        data_str = df_recent[['open', 'high', 'low', 'close', 'volume']].to_string()
        prompt = f"You are a crypto trading analyst. Based on the following recent market data for {symbol}, should I BUY, SELL, or HOLD?\n\nProvide a clear, one-word answer first, followed by a brief justification.\n\nRecent Market Data:\n{data_str}"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def get_news_sentiment(self, headlines: list[str]) -> str:
        prompt = f"Analyze the sentiment of the following crypto news headlines and classify it as 'bullish', 'bearish', or 'neutral'.\n\nHeadlines:\n- {'\n- '.join(headlines)}"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"


# OpenAI implementation
class OpenAIAnalyzer(AIAnalyzer):
    def __init__(self, api_key):
        super().__init__(api_key)
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)

    def get_trade_suggestion(self, symbol: str, df: pd.DataFrame) -> str:
        df_recent = df.tail(50)
        data_str = df_recent[['open', 'high', 'low', 'close', 'volume']].to_string()
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a crypto trading analyst."},
                    {"role": "user", "content": f"Based on the following recent market data for {symbol}, should I BUY, SELL, or HOLD?\n\nProvide a clear, one-word answer first, followed by a brief justification.\n\nRecent Market Data:\n{data_str}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    def get_news_sentiment(self, headlines: list[str]) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial news analyst."},
                    {"role": "user", "content": f"Analyze the sentiment of the following crypto news headlines and classify it as 'bullish', 'bearish', or 'neutral'.\n\nHeadlines:\n- {'\n- '.join(headlines)}"}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

# Factory function to get the desired AI analyzer
def get_ai_analyzer(provider: str = "gemini") -> AIAnalyzer:
    if provider == "gemini":
        return GeminiAnalyzer(cfg.gemini_api_key)
    elif provider == "openai":
        return OpenAIAnalyzer(cfg.openai_api_key)
    else:
        raise ValueError("Unsupported AI provider")
