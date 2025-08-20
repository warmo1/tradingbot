import requests

def get_latest_crypto_news(limit: int = 5):
    """Fetches the latest crypto news headlines from CryptoCompare."""
    url = f"https://min-api.cryptocompare.com/data/v2/news/?lang=EN&limit={limit}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        articles = response.json().get("Data", [])
        return [article['title'] for article in articles]
    except requests.RequestException as e:
        print(f"Error fetching news: {e}")
        return []
