# -*- coding: utf-8 -*-
"""
Simulation Engine Module - Simulates agent reactions to campaigns using a multi-stage cognitive model.
Supports a hybrid approach: stochastic numerical modeling + dynamic LLM semantic quote generation.
"""

import random
import json
import time

from llm_layer import call_llm, is_placeholder

CITY_REGION_MAP = {
    "İstanbul": "Marmara",
    "Ankara": "İç Anadolu",
    "İzmir": "Ege",
    "Muğla": "Ege",
    "Aydın": "Ege",
    "Denizli": "Ege",
    "Bursa": "Marmara",
    "Adana": "Akdeniz",
    "Konya": "İç Anadolu",
    "Kayseri": "İç Anadolu",
    "Eskişehir": "İç Anadolu",
    "Gaziantep": "Güneydoğu Anadolu",
    "Samsun": "Karadeniz",
}

def calculate_multi_stage_reaction(agent, campaign):
    """
    Computes a deterministic-stochastic multi-stage cognitive response:
    Stage 1: Attention Check
    Stage 2: Resonance Analysis
    Stage 3: Economic/Objection Calculation
    Stage 4: Purchase Likelihood & Categorical Decision
    """
    
    # 1. ATTENTION CHECK (0.0 to 1.0)
    # Based on agent's ad receptivity, tech savviness, and regional target
    target_regions = campaign.get("target_regions") or []
    if isinstance(target_regions, str):
        target_regions = [target_regions]
    normalized_targets = {str(r).strip().lower() for r in target_regions if str(r).strip()}
    agent_city = agent["city"]
    agent_region = CITY_REGION_MAP.get(agent_city, agent_city)
    all_region_tokens = {"tüm bölgeler", "tum bölgeler", "all", "tr", "türkiye", "turkiye"}
    region_match = 1.0 if (
        not normalized_targets
        or normalized_targets.intersection(all_region_tokens)
        or agent_city.lower() in normalized_targets
        or agent_region.lower() in normalized_targets
    ) else 0.5
    attention_score = (agent["ad_receptivity"] * 0.6 + agent["tech_savviness"] * 0.4) / 10.0
    attention_score = min(1.0, max(0.1, attention_score * region_match))
    
    # 2. RESONANCE STAGE (1.0 to 10.0)
    # Check alignment between agent core values and campaign key points
    resonance_base = 5.0
    campaign_text = (campaign["name"] + " " + campaign["description"]).lower()
    
    # Value Alignment Checks
    if agent["core_value"] == "Sustainability & Ethics":
        if any(w in campaign_text for w in ["ekolojik", "kompost", "plastik", "sıfır atık", "adil ticaret", "doğa", "geri dönüşüm", "yeşil"]):
            resonance_base += 4.0
        else:
            resonance_base -= 2.0
            
    elif agent["core_value"] == "Status & Quality":
        if any(w in campaign_text for w in ["premium", "nitelikli", "özel", "tek köken", "prestij", "şov"]):
            resonance_base += 4.0
        else:
            resonance_base -= 1.0
            
    elif agent["core_value"] == "Economy & Utility":
        if any(w in campaign_text for w in ["ucuz", "ekonomik", "hediye", "indirim", "fiyat koruma", "promosyon", "bedava"]):
            resonance_base += 4.5
        if campaign.get("price_index", 1.0) > 1.2:
            resonance_base -= 3.0  # Big penalty for high prices
            
    elif agent["core_value"] == "Nostalgia & Tradition":
        if any(w in campaign_text for w in ["nostalji", "geleneksel", "ata", "köz", "damla sakız", "fincan"]):
            resonance_base += 4.0
        if any(w in campaign_text for w in ["otonom", "robotik", "kiosk", "qr", "espresso"]):
            resonance_base -= 3.0  # Penalty for overly digital
            
    resonance_score = min(10.0, max(1.0, resonance_base + random.uniform(-1.0, 1.0)))

    # 3. ECONOMIC OBJECTION CALCULATION (0.0 to 10.0)
    # Formula: Price_Sensitivity * Price_Index * (50000 / Agent_Income), clipped to 1-10.
    income = max(1.0, float(agent["income_try"]))
    price_objection = agent["price_sensitivity"] * campaign.get("price_index", 1.0) * (50000.0 / income)
    
    # Cap objection between 1.0 and 10.0
    objection_score = min(10.0, max(1.0, price_objection))

    # 4. PURCHASE LIKELIHOOD (0 to 100)
    # 50% Resonance, 40% Objection Mitigation, 10% Attention
    objection_mitigation = 10.0 - objection_score
    raw_likelihood = (resonance_score * 5.0) + (objection_mitigation * 4.0) + (attention_score * 10.0)
    purchase_likelihood = min(100, max(0, round(raw_likelihood)))
    
    # 5. CATEGORICAL CHOICE
    decision = map_likelihood_to_decision(purchase_likelihood)
        
    return {
        "attention_score": round(attention_score, 2),
        "resonance_score": round(resonance_score, 2),
        "objection_score": round(objection_score, 2),
        "purchase_likelihood": purchase_likelihood,
        "decision": decision
    }


def map_likelihood_to_decision(likelihood):
    if likelihood >= 75:
        return "Buy"
    if likelihood >= 50:
        return "Skeptical Buy"
    if likelihood >= 25:
        return "Ignore"
    return "Reject"


def generate_semantic_quote(agent, campaign, simulation_metrics, api_key=None, provider="openai", strict=True):
    """
    Generates a natural, highly contextual Turkish quote expressing the agent's opinion.
    Each call injects randomized diversity seeds so 100 agents never sound alike.
    """
    decision = simulation_metrics["decision"]
    brand_name = campaign.get("brand", "Marka")
    selling_points = campaign.get("key_selling_points") or ["Kalite"]
    selling_point = selling_points[0] if isinstance(selling_points, list) else str(selling_points)
    
    if is_placeholder(api_key or "") and strict:
        raise RuntimeError("Live LLM API key is required to generate agent quotes.")

    # --- DIVERSITY INJECTION: randomize angle, mood, and focus per agent ---
    angles = [
        "price comparison with competitors",
        "personal taste and sensory experience",
        "family or household impact",
        "social status and what friends would think",
        "health and ingredient concerns",
        "convenience and accessibility",
        "brand trust and past experience",
        "environmental or ethical considerations",
        "value for money calculation",
        "emotional impulse vs rational decision",
        "seasonal or occasion relevance",
        "curiosity about trying something new",
        "skepticism based on advertising claims",
        "comparison with existing habits",
        "gift potential or shareability",
    ]
    moods = [
        "enthusiastic", "cautious", "indifferent", "suspicious",
        "curious", "disappointed", "excited", "practical",
        "nostalgic", "frustrated", "hopeful", "dismissive",
        "analytical", "impulsive", "worried",
    ]
    focuses = [
        "how it fits their daily routine",
        "whether the quality justifies the cost",
        "what their spouse/partner would say",
        "whether they've seen it on social media",
        "a specific personal anecdote or memory",
        "comparing it to a cheaper alternative",
        "their first impression of the packaging/ad",
        "whether they'd recommend it to a friend",
        "their monthly budget constraints",
        "how often they'd actually use/consume it",
    ]
    
    chosen_angle = random.choice(angles)
    chosen_mood = random.choice(moods)
    chosen_focus = random.choice(focuses)

    prompt = f"""
CRITICAL PRODUCT CONTEXT:
- Product category: {campaign.get('category')}
- You MUST understand what type of product this is (food, electronics, fashion, service, etc.)
- Your response MUST be contextually appropriate for this product type
- For FOOD/BEVERAGE: talk about taste, freshness, snacking, ingredients, price per unit — NEVER mention 'long-term usage', 'durability', or 'subscription'
- For TECH: talk about features, specs, ecosystem, updates
- For FASHION/COSMETICS: talk about style, brand image, occasions, trends
- For SERVICES: talk about convenience, reliability, customer experience

CONSUMER PROFILE (you are this person):
- Name: {agent['name']}
- Age: {agent['age']}
- Occupation: {agent['occupation']}
- Monthly Income: {agent['income_try']} TL
- City: {agent.get('city', 'Belirtilmedi')}
- Household Size: {agent.get('household_size', 1)}
- Segment: {agent['segment_name']}
- MBTI: {agent['mbti']}
- Core Value: {agent['core_value']}
- Lifestyle: {agent['lifestyle_habit']}

CAMPAIGN:
- Brand: "{brand_name}"
- Title: {campaign['name']}
- Description: {campaign['description']}

YOUR CALCULATED REACTION:
- Resonance: {simulation_metrics['resonance_score']}/10
- Economic Objection: {simulation_metrics['objection_score']}/10
- Purchase Likelihood: {simulation_metrics['purchase_likelihood']}%
- Decision: {simulation_metrics['decision']}

MANDATORY DIVERSITY INSTRUCTIONS:
- Your speaking ANGLE must be: {chosen_angle}
- Your MOOD is: {chosen_mood}
- Your specific FOCUS is: {chosen_focus}
- You MUST incorporate ALL THREE above into your quote
- Do NOT write a generic opinion — be SPECIFIC to your age, job, city, and income
- Reference a concrete detail from your life (e.g., your commute, your kids, your salary day, a specific store)

Write exactly ONE Turkish sentence (max 200 chars), first person ("Ben..." or direct speech).
The sentence must feel like a REAL person talking — messy, opinionated, specific.
Output ONLY the Turkish quote, nothing else.
"""

    try:
        return call_llm(
            prompt,
            max_tokens=100,
            temperature=1.1,
            provider=provider,
            api_key=api_key,
            allow_fallback=not strict,
        ).strip().replace('"', '')
    except Exception as exc:
        raise RuntimeError(f"Could not generate API-driven agent quote: {exc}") from exc


def run_full_focus_group_simulation(agents, campaign, api_key=None, provider="openai", progress_callback=None):
    """
    Simulates the reaction of all agents to a given campaign.
    """
    results = []
    
    for i, agent in enumerate(agents):
        # 1. Calculate cognitive metrics
        metrics = calculate_multi_stage_reaction(agent, campaign)
        
        # 2. Generate natural response quote
        quote = generate_semantic_quote(agent, campaign, metrics, api_key, provider)
        
        # Assemble complete result payload
        result = {
            "agent": agent,
            "metrics": metrics,
            "quote": quote
        }
        
        results.append(result)
        
        # Invoke progress callback if provided (useful for Streamlit rolling tickers)
        if progress_callback:
            progress_callback(i + 1, len(agents), agent, metrics)
            
    return results
