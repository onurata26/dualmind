import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

def search_duckduckgo(query, max_results=10):
    """
    Searches DuckDuckGo HTML interface and returns structured results.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept-Language": "tr,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # In DDG HTML version, result elements are usually in div.result or table/tr
        result_elements = soup.find_all('div', class_='result')
        if not result_elements:
            # Fallback to result__body
            result_elements = soup.find_all('div', class_='result__body')
            
        for elem in result_elements:
            title_elem = elem.find('a', class_='result__a')
            snippet_elem = elem.find('a', class_='result__snippet')
            url_elem = elem.find('a', class_='result__url')
            
            if not title_elem:
                continue
                
            title = title_elem.get_text(strip=True)
            raw_href = title_elem.get('href', '')
            
            # Extract actual URL from DuckDuckGo redirect link
            actual_url = raw_href
            if "uddg=" in raw_href:
                try:
                    parsed = urllib.parse.urlparse(raw_href)
                    queries = urllib.parse.parse_qs(parsed.query)
                    if 'uddg' in queries:
                        actual_url = queries['uddg'][0]
                except Exception:
                    pass
            
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            results.append({
                "title": title,
                "url": actual_url,
                "snippet": snippet
            })
            
            if len(results) >= max_results:
                break
                
        return results
    except Exception as e:
        print(file=sys.stderr, f"Error searching DuckDuckGo for query '{query}': {str(e)}")
        return []

def search_brand_source(brand, source_domain, query_extra="", max_results=5):
    """
    Searches a specific domain for brand-related context.
    """
    query = f"site:{source_domain} {brand} {query_extra}".strip()
    # Add a slight delay to respect search engine rate limits
    time.sleep(random.uniform(0.5, 1.2))
    return search_duckduckgo(query, max_results=max_results)

if __name__ == "__main__":
    # Quick self test
    print(file=sys.stderr, "Testing search_duckduckgo...")
    results = search_duckduckgo("site:pwc.com.tr perakende", max_results=2)
    print(file=sys.stderr, f"Found {len(results)} results:")
    for r in results:
        print(file=sys.stderr, f"- {r['title']}: {r['url']}")
