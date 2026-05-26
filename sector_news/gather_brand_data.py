import sys
import os
import json
from datetime import datetime
from search_engine import search_brand_source
from news_client import get_news
from llm_synthesizer import synthesize_report

def gather_all_sources(brand, category, region="TR", sector=None):
    """
    Scrapes and gathers data from all requested channels for the target brand.
    """
    raw_data = []
    
    # 1. News API / Scraped News
    print(file=sys.stderr, f"[{brand}] Fetching news updates...")
    news_key = os.environ.get("NEWS_API_KEY")
    news_items = get_news(brand, api_key=news_key, region=region, max_results=8)
    for n in news_items:
        raw_data.append({
            "source": "newsapi" if n.get("source") == "NewsAPI" else "news",
            "source_type": "api" if n.get("source") == "NewsAPI" else "news",
            "title": n.get("title", ""),
            "url": n.get("url", ""),
            "text": n.get("snippet", "")
        })
        
    # 2. PwC Turkey publications
    print(file=sys.stderr, f"[{brand}] Searching PwC Türkiye publications...")
    pwc_query_extra = sector if sector else category
    pwc_items = search_brand_source(brand, "pwc.com.tr", query_extra=pwc_query_extra, max_results=5)
    for item in pwc_items:
        raw_data.append({
            "source": "pwc",
            "source_type": "report",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("snippet", "")
        })
        
    # 3. Deloitte Turkey reports (as a complementary sector report source)
    print(file=sys.stderr, f"[{brand}] Searching Deloitte Türkiye reports...")
    deloitte_items = search_brand_source(brand, "deloitte.com/tr", query_extra=pwc_query_extra, max_results=3)
    for item in deloitte_items:
        raw_data.append({
            "source": "deloitte",
            "source_type": "report",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("snippet", "")
        })
        
    # 4. Ekşi Sözlük (Forum/Consumer perception)
    print(file=sys.stderr, f"[{brand}] Fetching Ekşi Sözlük sentiment...")
    eksi_items = search_brand_source(brand, "eksisozluk.com", query_extra="yorum", max_results=5)
    for item in eksi_items:
        raw_data.append({
            "source": "eksisozluk",
            "source_type": "forum",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("snippet", "")
        })
        
    # 5. Şikayetvar (Complaints and satisfaction issues)
    print(file=sys.stderr, f"[{brand}] Fetching Şikayetvar consumer complaints...")
    sikayet_items = search_brand_source(brand, "sikayetvar.com", query_extra="", max_results=5)
    for item in sikayet_items:
        raw_data.append({
            "source": "sikayetvar",
            "source_type": "complaint",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("snippet", "")
        })
        
    # 6. Reddit (Social media discussions)
    print(file=sys.stderr, f"[{brand}] Fetching Reddit discussions...")
    reddit_items = search_brand_source(brand, "reddit.com", query_extra="turkey", max_results=3)
    for item in reddit_items:
        raw_data.append({
            "source": "reddit",
            "source_type": "forum",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "text": item.get("snippet", "")
        })
        
    return raw_data

def generate_report_pipeline(brand, category, region="TR", sector=None, output_path=None):
    """
    Runs the full pipeline to gather data, synthesize, and save a brand report.
    """
    raw_data = gather_all_sources(brand, category, region, sector)
    print(file=sys.stderr, f"Total raw items gathered: {len(raw_data)}")
    
    # Synthesize using LLM
    report = synthesize_report(brand, category, region, raw_data)
    
    # Save to file
    if not output_path:
        filename = f"{brand.lower().replace(' ', '_')}_report.json"
        output_path = os.path.join(os.getcwd(), filename)
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(file=sys.stderr, f"Report successfully saved to: {output_path}")
    return report, output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gather company insight data and generate LLM report JSON")
    parser.add_argument("--brand", default="Starbucks", help="Brand name to analyze")
    parser.add_argument("--category", default="coffee", help="Category of the brand")
    parser.add_argument("--region", default="TR", help="Region (e.g. TR)")
    parser.add_argument("--sector", default=None, help="Specific sector to search")
    parser.add_argument("--out", default=None, help="Output file path")
    
    args = parser.parse_args()
    
    print(file=sys.stderr, f"Starting brand context gathering for {args.brand}...")
    generate_report_pipeline(args.brand, args.category, args.region, args.sector, args.out)
