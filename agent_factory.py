# -*- coding: utf-8 -*-
"""
MCP-calibrated profile factory.

Profiles are created inside the app at run time from MCP-backed market
segments. There are no fixed local segment tables or canned persona pools.
"""

import json
import random
import re
from typing import Any, Dict, Iterable, List

from llm_layer import call_llm, is_placeholder


REQUIRED_SEGMENT_KEYS = [
    "name",
    "weight_pct",
    "age_range",
    "avg_income",
    "price_sensitivity",
    "sustainability_focus",
    "brand_loyalty",
    "ad_receptivity",
    "tech_savviness",
    "core_value",
]


def _extract_json_array(text: str) -> List[Dict[str, Any]]:
    if not text:
        raise ValueError("LLM response is empty.")
    
    # Strip markdown formatting if present
    clean_text = text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    
    match = re.search(r"\[.*\]", clean_text, re.DOTALL)
    if not match:
        raise ValueError(f"LLM response did not contain a JSON array. Raw output: {text[:500]}")
    
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM JSON Decode Error: {e}. Raw output: {text[:500]}")


def _as_list(value: Any, fallback: Iterable[str]) -> List[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or list(fallback)
    if isinstance(value, str) and value.strip():
        cleaned = [part.strip() for part in value.split(",") if part.strip()]
        return cleaned or list(fallback)
    return list(fallback)


def _float_1_10(value: Any, field_name: str) -> float:
    try:
        return min(10.0, max(1.0, float(value)))
    except Exception as exc:
        raise ValueError(f"{field_name} must be a numeric 1-10 score.") from exc


def _coerce_segment(segment: Dict[str, Any], index: int) -> Dict[str, Any]:
    missing = [key for key in REQUIRED_SEGMENT_KEYS if segment.get(key) in (None, "", [])]
    if missing:
        raise ValueError(f"Segment {index + 1} is missing required fields: {', '.join(missing)}")

    age_range = segment.get("age_range")
    if not isinstance(age_range, list) or len(age_range) != 2:
        raise ValueError(f"Segment {index + 1} has invalid age_range.")

    coerced = dict(segment)
    coerced["id"] = str(coerced.get("id") or f"segment_{index + 1}")
    coerced["name"] = str(coerced["name"])
    coerced["weight_pct"] = float(coerced["weight_pct"])
    coerced["age_range"] = [int(age_range[0]), int(age_range[1])]
    coerced["avg_income"] = int(float(coerced["avg_income"]))
    coerced["core_value"] = str(coerced["core_value"])
    coerced["allowed_cities"] = _as_list(coerced.get("allowed_cities"), [])
    coerced["allowed_occupations"] = _as_list(coerced.get("allowed_occupations"), [])
    coerced["habits"] = _as_list(coerced.get("habits"), [])
    for key in ["price_sensitivity", "sustainability_focus", "brand_loyalty", "ad_receptivity", "tech_savviness"]:
        coerced[key] = _float_1_10(coerced[key], key)
    return coerced


def segment_report_mathematically(report_text: str, api_key=None, provider="openai", strict=True) -> List[Dict[str, Any]]:
    """
    Parses the external MCP-backed market report into proportional consumer
    segments. Segment data is generated from live LLM interpretation of MCP
    context, not from local templates.
    """
    if strict and (provider not in {"openai", "gemini"} or is_placeholder(api_key or "")):
        raise RuntimeError("Live OpenAI/Gemini API key is required to generate market segments.")

    prompt = f"""
Analyze the following Turkish MCP-backed market research report and produce a JSON array of consumer segments.

Rules:
- CRITICAL: First identify the product type from the report (e.g., chocolate → food/snack, phone → electronics). All segment attributes (habits, core_value, occupations) MUST be contextually appropriate for this product category.
- For food/snack products: habits should involve taste preferences, snacking occasions, ingredient awareness, family consumption patterns — NOT tech adoption or long-term investment behavior.
- For tech products: habits should involve device usage, app preferences, upgrade cycles.
- For fashion/cosmetics: habits should involve style preferences, shopping frequency, brand following.
- The segment weights must sum to exactly 100.
- Create as many segments as the data justifies, usually 3 to 6.
- Do not use generic canned profile segments.
- For every segment return:
  id, name, weight_pct, age_range, avg_income, price_sensitivity,
  sustainability_focus, brand_loyalty, ad_receptivity, tech_savviness,
  core_value, allowed_cities, allowed_occupations, habits.
- Scores are 1-10. avg_income is representative monthly TRY.
- allowed_cities, allowed_occupations and habits must come from the report's region/category logic.

Market report:
{report_text}

Return ONLY valid JSON. No markdown.
"""
    response = call_llm(
        prompt,
        system_prompt="You are a market segmentation analyst. You MUST first identify the exact product type (food, tech, fashion, service, etc.) from the report before creating segments. Segments must reflect realistic consumer behavior for that specific product category. Output strict JSON only.",
        max_tokens=2600,
        provider=provider,
        api_key=api_key,
        allow_fallback=not strict,
    )
    data = _extract_json_array(response)
    if not data:
        raise ValueError("Segment list is empty.")
    return [_coerce_segment(segment, index) for index, segment in enumerate(data)]


def normalize_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validates complete segment fields and normalizes weights to 100."""
    if not segments:
        raise ValueError("No segment data was produced by the external API/MCP flow.")

    normalized = [_coerce_segment(segment, index) for index, segment in enumerate(segments)]
    total_weight = sum(float(seg.get("weight_pct", 0) or 0) for seg in normalized)
    if total_weight <= 0:
        raise ValueError("Segment weights must be greater than zero.")

    for segment in normalized:
        segment["weight_pct"] = round((segment["weight_pct"] / total_weight) * 100.0, 2)

    drift = round(100.0 - sum(seg["weight_pct"] for seg in normalized), 2)
    normalized[-1]["weight_pct"] = round(normalized[-1]["weight_pct"] + drift, 2)
    return normalized


def _split_regions(campaign: Dict[str, Any]) -> List[str]:
    regions = campaign.get("target_regions") or ["Türkiye"]
    if isinstance(regions, str):
        regions = [part.strip() for part in regions.split(",") if part.strip()]
    return [str(region).strip() for region in regions if str(region).strip()] or ["Türkiye"]


def _sample_from(values: List[str], fallback: str) -> str:
    return random.choice(values) if values else fallback


def _bounded_score(base: float, spread: float = 1.3) -> float:
    return round(min(10.0, max(1.0, base + random.uniform(-spread, spread))), 1)


def _target_counts(segments: List[Dict[str, Any]], total_count: int) -> Dict[str, int]:
    remaining = total_count
    targets: Dict[str, int] = {}
    for index, segment in enumerate(segments):
        if index == len(segments) - 1:
            targets[segment["id"]] = remaining
        else:
            count = round(total_count * (segment["weight_pct"] / 100.0))
            targets[segment["id"]] = count
            remaining -= count
    return targets


def generate_mcp_calibrated_agents(
    segments: List[Dict[str, Any]],
    campaign: Dict[str, Any],
    total_count: int = 100,
) -> List[Dict[str, Any]]:
    """
    Creates run-time profiles from MCP/LLM-derived segments.
    Each agent gets a unique Turkish name, MBTI type, and gender
    so that LLM quote generation produces diverse, distinguishable responses.
    """
    # --- Realistic Turkish name pools ---
    MALE_NAMES = [
        "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "İsmail",
        "Yusuf", "Osman", "Murat", "Ömer", "Ramazan", "Halil", "Süleyman", "Abdullah",
        "Recep", "Fatih", "Emre", "Burak", "Serkan", "Onur", "Cem", "Tolga", "Barış",
        "Kerem", "Arda", "Eren", "Kaan", "Berk", "Deniz", "Efe", "Yiğit", "Umut",
        "Furkan", "Oğuz", "Selim", "Volkan", "Taner", "Koray", "Alp", "Caner", "Doruk",
        "Erdem", "Gökhan", "Hakan", "Kadir", "Levent", "Mert", "Sinan",
    ]
    FEMALE_NAMES = [
        "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife",
        "Zehra", "Sultan", "Hanife", "Merve", "Büşra", "Esra", "Derya", "Seda",
        "Özge", "Pınar", "Gül", "Hülya", "Aslı", "Ceren", "Dilan", "Ebru", "Gamze",
        "İrem", "Melis", "Naz", "Rana", "Selin", "Tuğçe", "Yaren", "Burcu", "Cansu",
        "Damla", "Elçin", "Fulya", "Gizem", "Hilal", "Kübra", "Lale", "Nesrin",
        "Sibel", "Tuba", "Ülkü", "Vildan", "Yeliz", "Buse", "Ezgi", "Nur",
    ]
    SURNAMES = [
        "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk",
        "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Koç",
        "Kurt", "Özkan", "Şimşek", "Polat", "Korkmaz", "Aktaş", "Erdoğan", "Ünal",
        "Acar", "Başar", "Güneş", "Kaplan", "Tekin", "Güler", "Balcı", "Bulut",
        "Duran", "Erdem", "Gündüz", "Işık", "Karaca", "Mutlu", "Sarı", "Taş",
    ]
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP",
    ]

    normalized_segments = normalize_segments(segments)
    targets = _target_counts(normalized_segments, total_count)
    target_regions = _split_regions(campaign)
    agents: List[Dict[str, Any]] = []
    agent_id = 1

    # Shuffle name pools to avoid repetition
    available_male = list(MALE_NAMES)
    available_female = list(FEMALE_NAMES)
    random.shuffle(available_male)
    random.shuffle(available_female)
    male_idx = 0
    female_idx = 0

    for segment in normalized_segments:
        for _ in range(targets[segment["id"]]):
            age = random.randint(segment["age_range"][0], segment["age_range"][1])
            income = max(1, int(segment["avg_income"] * random.uniform(0.78, 1.24)))
            household_size = max(1, min(6, round(random.gauss(2.4, 1.0))))
            city = _sample_from(segment["allowed_cities"], _sample_from(target_regions, "Türkiye"))
            occupation = _sample_from(segment["allowed_occupations"], "Belirtilmedi")
            habit = _sample_from(segment["habits"], f"{segment['name']} segmentinin kategori davranışını temsil eder.")

            # Assign gender and pick a real name
            gender = random.choice(["Erkek", "Kadın"])
            surname = random.choice(SURNAMES)
            if gender == "Erkek":
                first_name = available_male[male_idx % len(available_male)]
                male_idx += 1
            else:
                first_name = available_female[female_idx % len(available_female)]
                female_idx += 1
            full_name = f"{first_name} {surname}"

            mbti = random.choice(MBTI_TYPES)

            agents.append({
                "id": f"agent_{agent_id}",
                "source_id": f"mcp_calibrated_run_profile_{agent_id}",
                "data_source": "mcp_calibrated_runtime_generation",
                "segment_id": segment["id"],
                "segment_name": segment["name"],
                "name": full_name,
                "gender": gender,
                "age": age,
                "city": city,
                "occupation": occupation,
                "income_try": income,
                "household_size": household_size,
                "mbti": mbti,
                "core_value": segment["core_value"],
                "price_sensitivity": _bounded_score(segment["price_sensitivity"]),
                "sustainability_focus": _bounded_score(segment["sustainability_focus"]),
                "brand_loyalty": _bounded_score(segment["brand_loyalty"]),
                "ad_receptivity": _bounded_score(segment["ad_receptivity"]),
                "tech_savviness": _bounded_score(segment["tech_savviness"]),
                "lifestyle_habit": habit,
            })
            agent_id += 1

    return agents
