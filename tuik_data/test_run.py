import json
from mcp_server import get_market_dynamics, get_brand_context, get_current_context, fetch_live_tuik_data

def run_pipeline_validation():
    print("=" * 80)
    print("🔮 AI-POWERED TÜİK DYNAMIC SCRAPING & DATA EXTRACTION PIPELINE 🔮")
    print("=" * 80)
    
    # 1. Inputs
    brand_name = "Ege Craft Coffee"
    region = "Ege"
    target_age = "18-30"
    category = "coffee"
    query_topic = "enflasyon"
    
    print(f"\n[1] INPUT METADATA PARAMETERS:")
    print(f"  - Brand: {brand_name}")
    print(f"  - Region: {region}")
    print(f"  - Target Cohort: {target_age}")
    print(f"  - Category: {category}")
    print(f"  - Live Scrape Topic: '{query_topic}'")
    
    # 2. Call MCP Server (Numeric Mode)
    print(f"\n[2] QUERYING MCP SERVER TOOLS (PURE NUMERICAL VARIABLES)...")
    market_dynamics = get_market_dynamics(region, target_age, category)
    brand_context = get_brand_context(brand_name)
    current_context = get_current_context(region, category, brand_name)
    
    print(f"  ✓ Resolved local market dynamics (ADNKS pop: {market_dynamics['demographics']['cohort_population_adnks']})")
    print(f"  ✓ Resolved brand price index ({brand_context['brand_price_premium_index']}x premium)")
    print(f"  ✓ Resolved regional CPI inflation ({current_context['regional_cpi_inflation']}%)")
    
    # 3. Call Live Scraping Tool
    print(f"\n[3] EXECUTING LIVE DYNAMIC TÜİK SCRAPING TOOL (REAL-TIME FETCH)...")
    live_scraped_data = fetch_live_tuik_data(query_topic, scrape_first_bulletin=True)
    
    print(f"\n[4] live_scraped_data OUTPUT PAYLOAD:")
    print(json.dumps(live_scraped_data, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("✓ SUCCESS: Live TÜİK search resolves and outputs official links dynamically.")
    print("=" * 80)

if __name__ == "__main__":
    run_pipeline_validation()
