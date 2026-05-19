# -*- coding: utf-8 -*-
"""
End-to-end 100-agent MCP-backed consumer focus group pipeline.

The pipeline is intentionally callable from both CLI and Streamlit:
it writes all reports/files to disk, emits live progress events, and returns a
structured in-memory result for charts and drill-down inspection.
"""

import json
import os
import random
import re
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv

from agent_factory import generate_mcp_calibrated_agents, normalize_segments, segment_report_mathematically
from llm_layer import call_llm, is_placeholder
from mcp_client import collect_market_context, env_bool
from simulation_engine import calculate_multi_stage_reaction, generate_semantic_quote, map_likelihood_to_decision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
INITIAL_DIR = os.path.join(OUTPUTS_DIR, "initial_reactions")
FINAL_DIR = os.path.join(OUTPUTS_DIR, "final_reactions")

load_dotenv(os.path.join(BASE_DIR, ".env"))

FORM_INPUT = {
    "brand_name": "Firma",
    "campaign_title": "Pazarlama Kampanyası",
    "category": "Genel",
    "price_index": 1.0,
    "region": "Tüm Bölgeler",
    "target_audience": "Genel hedef kitle",
    "campaign_description": "",
    "key_selling_points": "",
}

DECISION_TR = {
    "Buy": "Kesin Alır",
    "Skeptical Buy": "Şüpheyle Alır",
    "Ignore": "Pas Geçer",
    "Reject": "Reddeder",
}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default


def _split_points(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _emit(progress_callback, phase: str, message: str, progress: Optional[float] = None, payload: Optional[Dict[str, Any]] = None) -> None:
    print(f"[{phase.upper()}] {message}")
    if progress_callback:
        progress_callback({
            "phase": phase,
            "message": message,
            "progress": progress,
            "payload": payload or {},
        })


def _safe_float(value: Any, default: float = 1.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _resolve_api_key(provider: str, api_key: Optional[str]) -> str:
    if api_key:
        return api_key
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY", "")
    return ""


def _require_external_runtime(provider: str, api_key: str, use_mcp: bool) -> None:
    if provider not in {"openai", "gemini"}:
        raise RuntimeError("Üretim modunda API_PROVIDER yalnızca 'openai' veya 'gemini' olabilir.")
    if is_placeholder(api_key):
        raise RuntimeError(f"{provider.upper()} API anahtarı eksik veya placeholder görünüyor.")
    if not use_mcp:
        raise RuntimeError("Üretim modunda use_mcp=False kapalıdır; pazar verisi MCP'den gelmelidir.")


def normalize_campaign_config(form_input: Dict[str, Any]) -> Dict[str, Any]:
    """Maps UI or CLI form payloads into the canonical campaign schema."""
    region_value = form_input.get("region") or form_input.get("target_region") or form_input.get("target_regions") or "Tüm Bölgeler"
    if isinstance(region_value, list):
        target_regions = region_value
    else:
        target_regions = [part.strip() for part in str(region_value).split(",") if part.strip()]

    return {
        "brand": form_input.get("brand_name") or form_input.get("brand") or "Marka",
        "name": form_input.get("campaign_title") or form_input.get("name") or "Kampanya",
        "category": form_input.get("category") or "Genel",
        "price_index": _safe_float(form_input.get("price_index", 1.0), 1.0),
        "target_regions": target_regions or ["Tüm Bölgeler"],
        "target_audience": form_input.get("target_audience", ""),
        "description": form_input.get("campaign_description") or form_input.get("description") or "",
        "key_selling_points": _split_points(form_input.get("key_selling_points") or form_input.get("selling_points")),
    }


def _ensure_output_dirs(output_dir: Optional[str] = None) -> Dict[str, str]:
    base = output_dir or OUTPUTS_DIR
    paths = {
        "base": base,
        "initial": os.path.join(base, "initial_reactions"),
        "final": os.path.join(base, "final_reactions"),
    }
    for path in paths.values():
        os.makedirs(path, exist_ok=True)
    return paths


def _clean_json_dir(path: str) -> None:
    if not os.path.exists(path):
        return
    for filename in os.listdir(path):
        if filename.endswith(".json"):
            os.remove(os.path.join(path, filename))


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def _agent_sort_key(result: Dict[str, Any]) -> int:
    agent_id = str(result["agent"].get("id", "agent_0"))
    match = re.search(r"(\d+)$", agent_id)
    return int(match.group(1)) if match else 0


def compute_stats(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = max(1, len(results))
    decision_counts = {key: 0 for key in DECISION_TR}
    segment_counts: Dict[str, int] = {}
    segment_positive: Dict[str, int] = {}
    likelihoods = []
    objection_scores = []

    for result in results:
        decision = result["metrics"]["decision"]
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        segment = result["agent"]["segment_name"]
        segment_counts[segment] = segment_counts.get(segment, 0) + 1
        if decision in {"Buy", "Skeptical Buy"}:
            segment_positive[segment] = segment_positive.get(segment, 0) + 1
        likelihoods.append(result["metrics"]["purchase_likelihood"])
        objection_scores.append(result["metrics"]["objection_score"])

    positives = decision_counts.get("Buy", 0) + decision_counts.get("Skeptical Buy", 0)
    nps = ((decision_counts.get("Buy", 0) - decision_counts.get("Reject", 0)) / total) * 100.0
    segment_conversion = {
        segment: round((segment_positive.get(segment, 0) / count) * 100.0, 1)
        for segment, count in segment_counts.items()
    }

    return {
        "total_agents": len(results),
        "decision_counts": decision_counts,
        "conversion_rate": round((positives / total) * 100.0, 1),
        "avg_likelihood": round(sum(likelihoods) / total, 1),
        "nps": round(nps, 1),
        "avg_objection": round(sum(objection_scores) / total, 2),
        "segment_conversion": segment_conversion,
        "dominant_objection": "Fiyat Hassasiyeti" if (sum(objection_scores) / total) > 5.5 else "Değer Rezonansı Eksikliği",
    }


def build_academic_market_report(form_input: Dict[str, Any], campaign: Dict[str, Any], mcp_context: Dict[str, Any]) -> str:
    dynamics = mcp_context.get("tuik_market_dynamics", {})
    brand_context = mcp_context.get("tuik_brand_context", {})
    current_context = mcp_context.get("tuik_current_context", {})
    brand_news = mcp_context.get("brand_news_context", {})

    def format_section(title: str, data: Dict[str, Any]) -> str:
        if not data:
            return f"## {title}\nVeri bulunamadı.\n"
        
        lines = [f"## {title}"]
        
        findings = data.get("findings", [])
        if findings:
            lines.append("**Bulgular:**")
            lines.extend(f"- {f}" for f in findings)
            
        signals = data.get("signals", [])
        if signals:
            lines.append("\n**Sinyaller:**")
            lines.extend(f"- {s}" for s in signals)
            
        segment_clues = data.get("segment_clues", [])
        if segment_clues:
            lines.append("\n**Segment İpuçları:**")
            lines.extend(f"- {c}" for c in segment_clues)
            
        effects = data.get("parameter_effects", {})
        if effects:
            lines.append("\n**Parametre Etkileri:**")
            for k, v in effects.items():
                lines.append(f"- {k}: {v}")
                
        confidence = data.get("confidence", 0)
        lines.append(f"\n*Güven Skoru: {confidence}%*\n")
        
        return "\n".join(lines)

    return f"""# Akademik Pazar Araştırma Raporu
**Tarih:** {datetime.now().strftime("%Y-%m-%d")}  
**Marka:** {campaign['brand']}  
**Kategori:** {campaign['category']}  
**Hedef Bölge:** {', '.join(campaign['target_regions'])}

{format_section("1. MCP Pazar Dinamikleri", dynamics)}
{format_section("2. Marka ve Rekabet Bağlamı", brand_context)}
{format_section("3. Mevcut Durum Bağlamı", current_context)}
{format_section("4. Sektör ve Haber Bağlamı", brand_news)}

## 5. Segmentasyon İçin Dış Veri Özeti
Bu rapor hazır segment tablosu içermez. Segmentler bir sonraki aşamada, yukarıdaki MCP verileri ve kullanıcının hedefleme briefi üzerinden canlı LLM çağrısıyla üretilecektir.

**Kullanıcı hedef kitlesi:** {form_input.get('target_audience', 'Genel hedef kitle')}  
**Kampanya açıklaması:** {campaign['description']}

Segmentasyon motoru şu alanları dış veriyle gerekçelendirmek zorundadır: segment ağırlıkları, yaş aralığı, temsilî gelir, fiyat hassasiyeti, sürdürülebilirlik odağı, marka sadakati, reklam alıcılığı ve teknoloji yatkınlığı.

## 6. Modelleme Hipotezi
Kampanya vaadi şu ana eksenlerde test edilecektir: {', '.join(campaign['key_selling_points']) or 'kampanya faydaları'}. Satın alma eğilimi, dikkat, değer rezonansı, ekonomik itiraz ve akran iknası katmanlarının birleşimiyle ölçülecektir.
"""


def _representative_quotes(results: List[Dict[str, Any]], decisions: Iterable[str]) -> str:
    lines = []
    for decision in decisions:
        match = next((r for r in results if r["metrics"]["decision"] == decision), None)
        if match:
            agent = match["agent"]
            lines.append(f"* **{agent['name']} ({agent['age']}, {agent['occupation']} - {DECISION_TR[decision]}):** \"{match['quote']}\"")
    return "\n".join(lines) or "* Temsili kotasyon üretilemedi."


def build_report_1(campaign: Dict[str, Any], initial_results: List[Dict[str, Any]], initial_stats: Dict[str, Any]) -> str:
    segment_lines = "\n".join(
        f"| {segment} | %{rate:.1f} |"
        for segment, rate in initial_stats["segment_conversion"].items()
    )
    decision_lines = "\n".join(
        f"| {DECISION_TR.get(decision, decision)} | {count} | %{(count / max(1, len(initial_results))) * 100:.1f} |"
        for decision, count in initial_stats["decision_counts"].items()
    )
    return f"""# Rapor 1: İlk Tepki Odak Grubu Raporu
**Kampanya:** {campaign['name']}  
**Marka/Kategori:** {campaign['brand']} / {campaign['category']}  
**Katılımcı:** {len(initial_results)} MCP verisiyle anlık oluşturulmuş tüketici profili

## Yönetici Özeti
İlk temas aşamasında genel dönüşüm oranı **%{initial_stats['conversion_rate']:.1f}**, ortalama satın alma eğilimi **%{initial_stats['avg_likelihood']:.1f}** ve NPS benzeri net tepki skoru **{initial_stats['nps']:+.1f}** olarak hesaplanmıştır. Baskın itiraz teması **{initial_stats['dominant_objection']}** görünmektedir.

## Karar Dağılımı
| Karar | Ajan | Pay |
| :--- | ---: | ---: |
{decision_lines}

## Segment Dönüşümü
| Segment | İlk Dönüşüm |
| :--- | ---: |
{segment_lines}

## İlk Tüketici Kotasyonları
{_representative_quotes(initial_results, ["Buy", "Skeptical Buy", "Ignore", "Reject"])}
"""


def build_report_2(
    campaign: Dict[str, Any],
    final_results: List[Dict[str, Any]],
    debates: List[Dict[str, Any]],
    initial_stats: Dict[str, Any],
    final_stats: Dict[str, Any],
) -> str:
    delta = final_stats["conversion_rate"] - initial_stats["conversion_rate"]
    avg_shift = sum(abs(item["mind_shift_a"]["delta"]) + abs(item["mind_shift_b"]["delta"]) for item in debates) / max(1, len(debates) * 2)
    sample_debates = "\n\n".join(
        f"### Grup {item['pair_index']}\n{item['dialogue']}"
        for item in debates[:3]
    )
    return f"""# Rapor 2: Akran Müzakeresi Sonrası Rapor
**Kampanya:** {campaign['name']}  
**Tartışma Yapısı:** {len(debates)} zıt kutuplu çift, 3 turlu Türkçe diyalog

## Müzakere Sonrası Özet
Akran tartışması sonrası dönüşüm oranı **%{final_stats['conversion_rate']:.1f}** oldu. İlk tepkiye göre net değişim **{delta:+.1f} puan**. Ortalama mutlak fikir kayması **{avg_shift:.1f} puan** ölçüldü.

## Güncellenmiş KPI
| Metrik | İlk Tepki | Müzakere Sonrası |
| :--- | ---: | ---: |
| Dönüşüm Oranı | %{initial_stats['conversion_rate']:.1f} | %{final_stats['conversion_rate']:.1f} |
| Ortalama Satın Alma Eğilimi | %{initial_stats['avg_likelihood']:.1f} | %{final_stats['avg_likelihood']:.1f} |
| NPS | {initial_stats['nps']:+.1f} | {final_stats['nps']:+.1f} |
| Ortalama İtiraz | {initial_stats['avg_objection']:.2f} | {final_stats['avg_objection']:.2f} |

## Sosyal İkna Yorumları
Olumlu profiller özellikle kalite, sürdürülebilirlik ve uzun vadeli değer argümanlarıyla düşük eğilimli profilleri yukarı çekti. Buna karşılık fiyat hassasiyeti yüksek profiller, bazı yüksek eğilimli profillerin kararını daha temkinli hale getirdi.

## Örnek Diyaloglar
{sample_debates}

## Final Tüketici Kotasyonları
{_representative_quotes(final_results, ["Buy", "Skeptical Buy", "Ignore", "Reject"])}
"""


def build_report_3(campaign: Dict[str, Any], initial_stats: Dict[str, Any], final_stats: Dict[str, Any]) -> str:
    conversion_delta = final_stats["conversion_rate"] - initial_stats["conversion_rate"]
    likelihood_delta = final_stats["avg_likelihood"] - initial_stats["avg_likelihood"]
    weighted_score = (initial_stats["conversion_rate"] * 0.45) + (final_stats["conversion_rate"] * 0.55)
    return f"""# Rapor 3: Yönetici Strateji ve Aksiyon Planı
**Kampanya:** {campaign['name']}  
**Karşılaştırma:** Bilinç 1 ilk tepki ve Bilinç 2 akran müzakeresi sonrası

## Karşılaştırmalı İstatistik Matrisi
| Metrik | İlk Tepki | Final | Değişim |
| :--- | ---: | ---: | ---: |
| Dönüşüm Oranı | %{initial_stats['conversion_rate']:.1f} | %{final_stats['conversion_rate']:.1f} | {conversion_delta:+.1f} puan |
| Ortalama Satın Alma Eğilimi | %{initial_stats['avg_likelihood']:.1f} | %{final_stats['avg_likelihood']:.1f} | {likelihood_delta:+.1f} puan |
| NPS | {initial_stats['nps']:+.1f} | {final_stats['nps']:+.1f} | {final_stats['nps'] - initial_stats['nps']:+.1f} |
| Ağırlıklı Başarı Skoru | - | %{weighted_score:.1f} | - |

## Stratejik Okuma
Kampanya sosyal tartışmaya girdiğinde dönüşüm **{conversion_delta:+.1f} puan** değişmektedir. Bu, kararın yalnızca bireysel fiyat algısıyla değil, akranlardan gelen kalite ve toplumsal fayda argümanlarıyla da şekillendiğini gösterir.

## 3 Final Aksiyon Planı
1. **Şeffaf Değer Kanıtı:** Sürdürülebilirlik, kalite veya sağlık iddiaları sertifika, kaynak hikayesi ve ölçülebilir etki verisiyle gösterilmeli.
2. **Fiyat Bariyerini Yumuşatma:** Deneme paketi, aile/ekonomik paket ve fiyat koruma seçeneğiyle yüksek itirazlı segmentin riski azaltılmalı.
3. **Akran Yayılımı:** Olumlu segmentlerden seçilecek mikro-elçilerle gerçek yorum, karşılaştırma ve kısa diyalog formatlı içerikler üretilmeli.
"""


def maybe_enhance_report(
    local_report: str,
    prompt: str,
    provider: Optional[str],
    api_key: Optional[str],
    max_tokens: int = 2200,
    strict: bool = True,
) -> str:
    if not provider or provider == "local" or is_placeholder(api_key or ""):
        if strict:
            raise RuntimeError("Canlı LLM API anahtarı olmadan rapor dili üretilemez.")
        return local_report
    try:
        enhanced = call_llm(
            prompt + "\n\nUse the following computed report as the source of truth:\n" + local_report,
            system_prompt="You are a senior Turkish market research strategist. Keep all numeric values unchanged.",
            max_tokens=max_tokens,
            provider=provider,
            api_key=api_key,
            allow_fallback=not strict,
        )
        if enhanced and len(enhanced) > 300:
            return enhanced
    except Exception as exc:
        if strict:
            raise RuntimeError(f"Rapor LLM zenginleştirmesi başarısız: {exc}") from exc
    return local_report


def _local_debate(agent_a: Dict[str, Any], agent_b: Dict[str, Any], campaign: Dict[str, Any], metrics_a: Dict[str, Any], metrics_b: Dict[str, Any]) -> str:
    a_name = agent_a["name"].split()[0]
    b_name = agent_b["name"].split()[0]
    selling_point = (campaign.get("key_selling_points") or ["değer önerisi"])[0]
    return (
        f"[{a_name}]: Benim için mesele fiyat. %{metrics_a['purchase_likelihood']} eğilimle bakıyorum ama aylık bütçemde bunun yeri net değil.\n"
        f"[{b_name}]: Haklısın, fakat {selling_point} tarafı güçlü. Uzun vadeli kalite ve güven varsa fiyat tek başına karar verdirmemeli.\n"
        f"[{a_name}]: Bu argüman beni biraz yumuşattı. Deneme paketi veya net belge sunarlarsa kararımı yukarı çekebilirim."
    )


def generate_debate_dialogue(
    agent_a: Dict[str, Any],
    agent_b: Dict[str, Any],
    campaign: Dict[str, Any],
    metrics_a: Dict[str, Any],
    metrics_b: Dict[str, Any],
    provider: Optional[str],
    api_key: Optional[str],
    strict: bool = True,
) -> str:
    if not provider or provider == "local" or is_placeholder(api_key or ""):
        if strict:
            raise RuntimeError("Canlı LLM API anahtarı olmadan akran müzakeresi üretilemez.")
        return _local_debate(agent_a, agent_b, campaign, metrics_a, metrics_b)

    prompt = f"""
Conduct a 3-turn debate in Turkish between two consumers about the campaign "{campaign['name']}".
Consumer A: {agent_a['name']} ({agent_a['age']}, {agent_a['occupation']}, {agent_a['city']}). Initial decision: {metrics_a['decision']} ({metrics_a['purchase_likelihood']}%). Core value: {agent_a['core_value']}. Price Sensitivity: {agent_a['price_sensitivity']}/10.
Consumer B: {agent_b['name']} ({agent_b['age']}, {agent_b['occupation']}, {agent_b['city']}). Initial decision: {metrics_b['decision']} ({metrics_b['purchase_likelihood']}%). Core value: {agent_b['core_value']}. Price Sensitivity: {agent_b['price_sensitivity']}/10.
Turn 1: Consumer A voices doubts.
Turn 2: Consumer B responds with sustainability, quality, economic, or tradition arguments.
Turn 3: Consumer A updates their thinking.
Format exactly:
[Name A]: ...
[Name B]: ...
[Name A]: ...
"""
    dialogue = call_llm(prompt, max_tokens=600, provider=provider, api_key=api_key, allow_fallback=not strict)
    if not dialogue or "Sanal Tüketici" in dialogue:
        if strict:
            raise RuntimeError("LLM debate response was empty or invalid.")
        return _local_debate(agent_a, agent_b, campaign, metrics_a, metrics_b)
    return dialogue.strip()


def run_focus_group_pipeline(
    form_input: Optional[Dict[str, Any]] = None,
    market_report_text: Optional[str] = None,
    agent_count: Optional[int] = None,
    segments: Optional[List[Dict[str, Any]]] = None,
    agents: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    extra_mcp_server_paths: Optional[Iterable[str]] = None,
    output_dir: Optional[str] = None,
    clean_outputs: bool = True,
    progress_callback=None,
    sleep_seconds: float = 0.0,
    random_seed: Optional[int] = None,
    use_mcp: bool = True,
) -> Dict[str, Any]:
    form_input = dict(form_input or FORM_INPUT)
    agent_count = agent_count or _env_int("AGENT_COUNT", 100)
    provider = (provider or os.getenv("API_PROVIDER", "openai")).lower()
    api_key = _resolve_api_key(provider, api_key)
    strict_external = env_bool("STRICT_EXTERNAL_DATA", True)
    if strict_external:
        _require_external_runtime(provider, api_key, use_mcp)
    random_seed = random_seed if random_seed is not None else _env_int("SIMULATION_RANDOM_SEED", 42)
    random.seed(random_seed)

    output_paths = _ensure_output_dirs(output_dir)
    if clean_outputs:
        _clean_json_dir(output_paths["initial"])
        _clean_json_dir(output_paths["final"])

    _emit(progress_callback, "start", f"{agent_count} MCP kalibrasyonlu tüketici profiliyle araştırma başlatıldı.", 0.01)

    campaign = normalize_campaign_config(form_input)
    _emit(progress_callback, "input", f"Kampanya yapılandırıldı: {campaign['brand']} / {campaign['name']}", 0.04, {"campaign": campaign})

    if use_mcp:
        mcp_context = collect_market_context(
            form_input,
            extra_server_paths=extra_mcp_server_paths,
            progress_callback=progress_callback,
            strict=strict_external,
        )
    else:
        from mcp_client import MCPClient
        offline = MCPClient(server_path="", name="offline", strict=False)
        mcp_context = {
            "tuik_market_dynamics": offline.get_mock_payload("get_market_dynamics", {
                "region": form_input.get("region", "Türkiye"),
                "category": form_input.get("category", "Genel"),
            }),
            "tuik_brand_context": offline.get_mock_payload("get_brand_context", {"brand_name": form_input.get("brand_name", "Demo Marka")}),
            "tuik_current_context": offline.get_mock_payload("get_current_context", {
                "region": form_input.get("region", "Türkiye"),
                "category": form_input.get("category", "Genel"),
                "brand_name": form_input.get("brand_name", "Demo Marka"),
            }),
            "brand_news_context": offline.get_mock_payload("generate_report", {
                "brand": form_input.get("brand_name", "Demo Marka"),
                "category": form_input.get("category", "Genel"),
            }),
            "optional_mcp_context": [],
        }
    _emit(progress_callback, "mcp", "MCP pazar bağlamı hazır.", 0.12)

    academic_report = market_report_text or build_academic_market_report(form_input, campaign, mcp_context)
    if not market_report_text:
        academic_report = maybe_enhance_report(
            academic_report,
            "Generate a Turkish academic market research report for this campaign and MCP data.",
            provider,
            api_key,
            max_tokens=2500,
            strict=strict_external,
        )
    academic_report_path = os.path.join(output_paths["base"], "academic_market_report.md")
    _write_text(academic_report_path, academic_report)
    _emit(progress_callback, "report", "Akademik pazar raporu diske yazıldı.", 0.18)

    if segments is None:
        segments = segment_report_mathematically(
            academic_report,
            api_key=api_key if provider in {"openai", "gemini"} else None,
            provider=provider if provider in {"openai", "gemini"} else "openai",
            strict=strict_external,
        )
    segments = normalize_segments(segments)
    _emit(progress_callback, "segments", f"{len(segments)} pazar segmenti dış veriden normalize edildi.", 0.22, {"segments": segments})

    if agents is None:
        agents = generate_mcp_calibrated_agents(segments, campaign, total_count=agent_count)
    elif len(agents) != agent_count:
        raise ValueError(f"Provided agent list has {len(agents)} profiles; {agent_count} required.")
    _emit(progress_callback, "agents", f"{len(agents)} profil MCP segmentlerine göre anlık oluşturuldu.", 0.28)

    initial_results = []
    for index, agent in enumerate(agents, start=1):
        metrics = calculate_multi_stage_reaction(agent, campaign)
        quote = generate_semantic_quote(agent, campaign, metrics, api_key=api_key, provider=provider, strict=strict_external)
        reaction_profile = {
            "agent": agent,
            "campaign": campaign,
            "phase": "initial",
            "metrics": metrics,
            "quote": quote,
        }
        _write_json(os.path.join(output_paths["initial"], f"agent_{agent['id']}.json"), reaction_profile)
        initial_results.append(reaction_profile)
        if sleep_seconds:
            time.sleep(sleep_seconds)
        _emit(
            progress_callback,
            "initial",
            f"{index}/{len(agents)} {agent['name']} ilk bilinç skorları: dikkat={metrics['attention_score']}, rezonans={metrics['resonance_score']}, itiraz={metrics['objection_score']}, karar={DECISION_TR[metrics['decision']]} %{metrics['purchase_likelihood']}",
            0.28 + (0.34 * index / max(1, len(agents))),
            {"agent": agent, "metrics": metrics},
        )

    initial_stats = compute_stats(initial_results)
    report_1 = build_report_1(campaign, initial_results, initial_stats)
    report_1 = maybe_enhance_report(report_1, "Generate Rapor 1: initial focus group report.", provider, api_key, strict=strict_external)
    report_1_path = os.path.join(output_paths["base"], "report_1_initial.md")
    _write_text(report_1_path, report_1)
    _emit(progress_callback, "report", "Rapor 1 üretildi.", 0.64)

    sorted_results = sorted(initial_results, key=lambda item: item["metrics"]["purchase_likelihood"])
    debates = []
    final_results = []
    pair_count = len(sorted_results) // 2
    for pair_index in range(pair_count):
        low_result = sorted_results[pair_index]
        high_result = sorted_results[-(pair_index + 1)]
        agent_a = low_result["agent"]
        agent_b = high_result["agent"]
        metrics_a = low_result["metrics"]
        metrics_b = high_result["metrics"]

        dialogue = generate_debate_dialogue(agent_a, agent_b, campaign, metrics_a, metrics_b, provider, api_key, strict=strict_external)
        delta_a = (metrics_b["purchase_likelihood"] - metrics_a["purchase_likelihood"]) * 0.25
        delta_b = (metrics_a["purchase_likelihood"] - metrics_b["purchase_likelihood"]) * 0.15
        noise_a = random.uniform(-2.0, 2.0)
        noise_b = random.uniform(-2.0, 2.0)
        new_lik_a = min(100, max(0, round(metrics_a["purchase_likelihood"] + delta_a + noise_a)))
        new_lik_b = min(100, max(0, round(metrics_b["purchase_likelihood"] + delta_b + noise_b)))

        final_metrics_a = dict(metrics_a)
        final_metrics_b = dict(metrics_b)
        final_metrics_a.update({"purchase_likelihood": new_lik_a, "decision": map_likelihood_to_decision(new_lik_a)})
        final_metrics_b.update({"purchase_likelihood": new_lik_b, "decision": map_likelihood_to_decision(new_lik_b)})

        quote_a = generate_semantic_quote(agent_a, campaign, final_metrics_a, api_key=api_key, provider=provider, strict=strict_external)
        quote_b = generate_semantic_quote(agent_b, campaign, final_metrics_b, api_key=api_key, provider=provider, strict=strict_external)

        profile_a = {
            "agent": agent_a,
            "campaign": campaign,
            "phase": "final",
            "initial_metrics": metrics_a,
            "metrics": final_metrics_a,
            "initial_quote": low_result["quote"],
            "quote": quote_a,
            "debate_partner": agent_b["name"],
            "debate_partner_id": agent_b["id"],
            "debate_dialogue": dialogue,
            "mind_shift": {
                "before": metrics_a["purchase_likelihood"],
                "delta": round(delta_a + noise_a, 2),
                "after": new_lik_a,
            },
        }
        profile_b = {
            "agent": agent_b,
            "campaign": campaign,
            "phase": "final",
            "initial_metrics": metrics_b,
            "metrics": final_metrics_b,
            "initial_quote": high_result["quote"],
            "quote": quote_b,
            "debate_partner": agent_a["name"],
            "debate_partner_id": agent_a["id"],
            "debate_dialogue": dialogue,
            "mind_shift": {
                "before": metrics_b["purchase_likelihood"],
                "delta": round(delta_b + noise_b, 2),
                "after": new_lik_b,
            },
        }
        final_results.extend([profile_a, profile_b])

        debates.append({
            "pair_index": pair_index + 1,
            "agent_a_id": agent_a["id"],
            "agent_a_name": agent_a["name"],
            "agent_b_id": agent_b["id"],
            "agent_b_name": agent_b["name"],
            "dialogue": dialogue,
            "mind_shift_a": profile_a["mind_shift"],
            "mind_shift_b": profile_b["mind_shift"],
        })
        if sleep_seconds:
            time.sleep(sleep_seconds)
        _emit(
            progress_callback,
            "debate",
            f"Grup {pair_index + 1}/{pair_count}: {agent_a['name']} ↔ {agent_b['name']} fikir kayması {new_lik_a}% / {new_lik_b}%",
            0.64 + (0.24 * (pair_index + 1) / max(1, pair_count)),
            {"dialogue": dialogue},
        )

    if len(sorted_results) % 2 == 1:
        middle = sorted_results[pair_count]
        final_results.append({
            **middle,
            "phase": "final",
            "initial_metrics": middle["metrics"],
            "initial_quote": middle["quote"],
            "debate_partner": None,
            "debate_partner_id": None,
            "debate_dialogue": "",
            "mind_shift": {
                "before": middle["metrics"]["purchase_likelihood"],
                "delta": 0,
                "after": middle["metrics"]["purchase_likelihood"],
            },
        })

    final_results = sorted(final_results, key=_agent_sort_key)
    for profile in final_results:
        _write_json(os.path.join(output_paths["final"], f"agent_{profile['agent']['id']}.json"), profile)

    final_stats = compute_stats(final_results)
    report_2 = build_report_2(campaign, final_results, debates, initial_stats, final_stats)
    report_2 = maybe_enhance_report(report_2, "Generate Rapor 2: post-debate focus group report.", provider, api_key, strict=strict_external)
    report_2_path = os.path.join(output_paths["base"], "report_2_post_debate.md")
    _write_text(report_2_path, report_2)
    _emit(progress_callback, "report", "Rapor 2 üretildi.", 0.91)

    report_3 = build_report_3(campaign, initial_stats, final_stats)
    report_3 = maybe_enhance_report(report_3, "Generate Rapor 3: final executive action report.", provider, api_key, strict=strict_external)
    report_3_path = os.path.join(output_paths["base"], "report_3_final.md")
    _write_text(report_3_path, report_3)
    _emit(progress_callback, "done", f"Araştırma tamamlandı: 3 rapor ve {len(initial_results) + len(final_results)} profil reaksiyon dosyası hazır.", 1.0)

    return {
        "campaign": campaign,
        "mcp_context": mcp_context,
        "academic_report": academic_report,
        "segments": segments,
        "agents": agents,
        "initial_results": initial_results,
        "final_results": final_results,
        "debates": debates,
        "reports": {
            "academic_market_report": academic_report,
            "report_1_initial": report_1,
            "report_2_post_debate": report_2,
            "report_3_final": report_3,
        },
        "stats": {
            "initial": initial_stats,
            "final": final_stats,
        },
        "output_paths": {
            "base": output_paths["base"],
            "academic_market_report": academic_report_path,
            "report_1_initial": report_1_path,
            "report_2_post_debate": report_2_path,
            "report_3_final": report_3_path,
            "initial_reactions": output_paths["initial"],
            "final_reactions": output_paths["final"],
        },
    }


if __name__ == "__main__":
    run_focus_group_pipeline()
