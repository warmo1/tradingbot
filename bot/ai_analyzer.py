from .config import cfg
import pandas as pd

# (Keep the existing AIAnalyzer, GeminiAnalyzer, and OpenAIAnalyzer classes)
class AIAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key

    def get_trade_suggestion(self, symbol: str, df: pd.DataFrame) -> str:
        raise NotImplementedError

    def get_news_sentiment(self, headlines: list[str]) -> str:
        raise NotImplementedError
    
    def get_portfolio_suggestion(self, cash: float, symbols: list, insights: list) -> str:
        raise NotImplementedError

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
            
    def get_portfolio_suggestion(self, cash: float, symbols: list, insights: list) -> str:
        insights_str = "\n".join([f"- {i['symbol']}: {i['signal']} ({i['justification']})" for i in insights])
        prompt = f"""
        You are a crypto portfolio manager. Your goal is to grow an initial pot of money.
        You have £{cash:,.2f} in cash to invest.
        
        Here are the available coins and the latest AI analysis on them:
        {insights_str}

        Based on this information, recommend a set of trades to build a small, diversified portfolio.
        Provide a list of BUY trades. For each trade, specify the symbol and the amount of cash to allocate.
        The total cash allocated should not exceed the available cash.
        
        Your response should be a brief, actionable trading plan.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating portfolio: {e}"

# (Keep the OpenAIAnalyzer and the factory function)
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
            
    def get_portfolio_suggestion(self, cash: float, symbols: list, insights: list) -> str:
        insights_str = "\n".join([f"- {i['symbol']}: {i['signal']} ({i['justification']})" for i in insights])
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a crypto portfolio manager. Your goal is to grow an initial pot of money."},
                    {"role": "user", "content": f"""
                        You have £{cash:,.2f} in cash to invest.
                        
                        Here are the available coins and the latest AI analysis on them:
                        {insights_str}

                        Based on this information, recommend a set of trades to build a small, diversified portfolio.
                        Provide a list of BUY trades. For each trade, specify the symbol and the amount of cash to allocate.
                        The total cash allocated should not exceed the available cash.
                        
                        Your response should be a brief, actionable trading plan.
                    """}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating portfolio: {e}"

def get_ai_analyzer(provider: str = "gemini") -> AIAnalyzer:
    if provider == "gemini":
        return GeminiAnalyzer(cfg.gemini_api_key)
    elif provider == "openai":
        return OpenAIAnalyzer(cfg.openai_api_key)
    else:
        raise ValueError("Unsupported AI provider")
