import sys
import os
import json
import time

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def log(msg):
    sys.stderr.write(f"[SCRAPER LOG] {msg}\n")
    sys.stderr.flush()

class TuikScraper:
    """
    A high-fidelity dynamic scraper that bypasses TÜİK's SPA/WAF protection
    using a real headless browser.
    """
    
    @classmethod
    def is_configured(cls):
        return PLAYWRIGHT_AVAILABLE

    @classmethod
    def scrape_search_results(cls, query, limit=5):
        """
        Launches headless browser, searches TÜİK, and returns the result cards.
        """
        if not PLAYWRIGHT_AVAILABLE:
            log("Playwright is not installed. Please run: pip install playwright && playwright install chromium")
            return {"error": "Playwright is not installed in the environment."}
            
        log(f"Searching TÜİK for: '{query}'...")
        search_url = f"https://data.tuik.gov.tr/tr/search?q={query}"
        
        results = []
        
        with sync_playwright() as p:
            # Launch headless chromium with standard desktop user agent
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                # Navigate to search URL
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for React SPA cards to render (wait for lists containing results)
                page.wait_for_selector("a[href*='/Bulten/Index']", timeout=10000)
                
                # Extract search result elements
                elements = page.query_selector_all("a[href*='/Bulten/Index']")
                log(f"Found {len(elements)} raw matching elements.")
                
                for el in elements[:limit]:
                    try:
                        title = el.inner_text().strip()
                        href = el.get_attribute("href")
                        
                        if title and href:
                            full_url = href if href.startswith("http") else f"https://data.tuik.gov.tr{href}"
                            # Extract potential date/subtitle from sibling elements if present
                            results.append({
                                "title": title,
                                "url": full_url
                            })
                    except Exception as e:
                        log(f"Error parsing search element: {str(e)}")
                        
            except Exception as e:
                log(f"Playwright navigation/wait failed: {str(e)}")
            finally:
                browser.close()
                
        return results

    @classmethod
    def scrape_bulletin(cls, url):
        """
        Navigates to a specific TÜİK bulletin page and extracts raw numerical tables and text.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return {"error": "Playwright is not installed in the environment."}
            
        log(f"Scraping bulletin page: {url}...")
        
        bulletin_data = {
            "title": "",
            "release_date": "",
            "paragraphs": [],
            "tables": []
        }
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for any text block or table to render
                page.wait_for_selector("div#root", timeout=15000)
                
                # Short sleep to allow complete JS rendering
                time.sleep(2)
                
                # Get page title
                title_el = page.query_selector("h1, h2, .bulletin-title, .title")
                if title_el:
                    bulletin_data["title"] = title_el.inner_text().strip()
                
                # Extract all paragraph texts
                p_elements = page.query_selector_all("p, .bulletin-text, .text")
                for p_el in p_elements:
                    txt = p_el.inner_text().strip()
                    if len(txt) > 20: # Filter out empty/short labels
                        bulletin_data["paragraphs"].append(txt)
                        
                # Extract all tables
                tables = page.query_selector_all("table")
                log(f"Found {len(tables)} tables on bulletin page.")
                
                for idx, t in enumerate(tables):
                    table_rows = []
                    rows = t.query_selector_all("tr")
                    for r in rows:
                        cols = r.query_selector_all("td, th")
                        row_data = [col.inner_text().strip() for col in cols]
                        if any(row_data): # Skip completely empty rows
                            table_rows.append(row_data)
                            
                    if table_rows:
                        bulletin_data["tables"].append({
                            "table_index": idx + 1,
                            "data": table_rows
                        })
                        
            except Exception as e:
                log(f"Failed to scrape bulletin: {str(e)}")
            finally:
                browser.close()
                
        return bulletin_data

if __name__ == "__main__":
    # Standard CLI test run if executed directly
    if not PLAYWRIGHT_AVAILABLE:
        print("Playwright is NOT installed. Run: pip install playwright && playwright install chromium")
    else:
        print("Playwright detected! Testing TUIK live search for 'enflasyon'...")
        res = TuikScraper.scrape_search_results("enflasyon", limit=3)
        print("Search Results:\n", json.dumps(res, indent=2, ensure_ascii=False))
        if res and "url" in res[0]:
            print(f"\nTesting scraping on first result: {res[0]['url']}...")
            data = TuikScraper.scrape_bulletin(res[0]['url'])
            print("Bulletin Data:\n", json.dumps(data, indent=2, ensure_ascii=False)[:1000] + "...")
