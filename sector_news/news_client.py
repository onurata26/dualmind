import sys
import os
import requests
from search_engine import search_duckduckgo

def fetch_news_api(brand, api_key, region="tr", max_results=10):
    """
    Fetches news from NewsAPI.
    """
    url = "https://newsapi.org/v2/everything"
    
    # Customize search terms for Turkey region if specified
    q = f"{brand}"
    if region.lower() == "tr":
        q = f"{brand} OR {brand} Türkiye"
        
    params = {
        "q": q,
        "sortBy": "publishedAt",
        "pageSize": max_results,
        "apiKey": api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            results = []
            for art in articles:
                results.append({
                    "title": art.get("title", ""),
                    "url": art.get("url", ""),
                    "snippet": art.get("description", "") or art.get("content", "") or "",
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                    "published_at": art.get("publishedAt", "")
                })
            return results
        else:
            print(file=sys.stderr, f"NewsAPI error (Status {response.status_code}): {response.text}")
            return []
    except Exception as e:
        print(file=sys.stderr, f"Error fetching from NewsAPI: {str(e)}")
        return []

def fetch_news_fallback(brand, region="tr", max_results=10):
    """
    Fallback news gathering using search engines on popular Turkish/global news and tech blogs.
    """
    results = []
    
    # Domains we want to target for news
    domains = [
        "webrazzi.com",
        "bigumigu.com",
        "bloomberght.com",
        "patronlardunyasi.com",
        "hurriyet.com.tr",
        "haberturk.com",
        "sabah.com.tr",
        "dunya.com"
    ]
    
    # We construct a query: (site:webrazzi.com OR site:bloomberght.com OR ...) brand
    # DuckDuckGo handles OR queries well. Let's group them.
    domain_query = " OR ".join([f"site:{d}" for d in domains[:4]]) # keep it short for DDG query length limit
    query1 = f"({domain_query}) {brand}"
    
    news_items = search_duckduckgo(query1, max_results=max_results // 2)
    for item in news_items:
        item["source"] = "news_scraped"
        results.append(item)
        
    if len(results) < max_results:
        domain_query2 = " OR ".join([f"site:{d}" for d in domains[4:]])
        query2 = f"({domain_query2}) {brand}"
        news_items2 = search_duckduckgo(query2, max_results=(max_results - len(results)))
        for item in news_items2:
            item["source"] = "news_scraped"
            results.append(item)
            
    return results

def get_news(brand, api_key=None, region="tr", max_results=10):
    """
    Fetches news using NewsAPI if key is provided, otherwise falls back to scraping.
    """
    if api_key:
        api_results = fetch_news_api(brand, api_key, region, max_results)
        if api_results:
            return api_results
            
    # Try fallback
    return fetch_news_fallback(brand, region, max_results)

if __name__ == "__main__":
    print(file=sys.stderr, "Testing get_news...")
    news = get_news("Starbucks", max_results=3)
    print(file=sys.stderr, f"Found {len(news)} news items:")
    for n in news:
        print(file=sys.stderr, f"- [{n.get('source')}] {n['title']} -> {n['url']}")
