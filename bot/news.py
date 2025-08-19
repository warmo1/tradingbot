import requests
from .config import cfg

def get_latest_crypto_news(limit: int = 5):
    """Fetches the latest crypto news headlines."""
    if not cfg.news_api_key:
        return []
    
    url = f"https://newsapi.org/v2/everything?q=crypto&sortBy=publishedAt&apiKey={cfg.news_api_key}&pageSize={limit}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [article['title'] for article in articles]
    except requests.RequestException as e:
        print(f"Error fetching news: {e}")
        return []
