# -*- coding: utf-8 -*-
"""
Minimal survey-first Streamlit UI for the MCP-backed consumer research engine.
"""

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import DECISION_TR, run_focus_group_pipeline
from llm_layer import is_placeholder

BASE_DIR = Path(__file__).resolve().parent

THEMES = {
    "Koyu": {
        "surface": "rgba(255, 255, 255, 0.02)",
        "surface_soft": "rgba(255, 255, 255, 0.04)",
        "text": "#ffffff",
        "muted": "#9ca3af",
        "line": "rgba(255,255,255,0.08)",
        "accent": "#7b61ff",
        "accent_2": "#6366f1",
        "good": "#10b981",
        "warn": "#f59e0b",
        "bad": "#ef4444",
    }
}


st.set_page_config(
    page_title="DualMind — Yapay Zeka Pazarlama Platformu",
    page_icon="ST",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def init_state() -> None:
    defaults = {
        "stage": "landing",
        "theme": "Koyu",
        "company_name": "",
        "product_name": "",
        "campaign_description": "",
        "market_price": "",
        "proposed_price": "",
        "region": "",
        "age_group": "Genel",
        "target_user": "",
        "run_logs": [],
        "pipeline_result": None,
        "run_started": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_theme() -> None:
    theme = THEMES["Koyu"]
    st.markdown(
        f"""
        <style>
        :root {{
            --surface: {theme['surface']};
            --surface-soft: {theme['surface_soft']};
            --text: {theme['text']};
            --muted: {theme['muted']};
            --line: {theme['line']};
            --accent: {theme['accent']};
            --accent-2: {theme['accent_2']};
            --good: {theme['good']};
            --warn: {theme['warn']};
            --bad: {theme['bad']};
        }}
        </style>
        <div class="aurora-bg"></div>
        """,
        unsafe_allow_html=True,
    )
    css_path = BASE_DIR / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def go_to(stage: str) -> None:
    st.session_state.stage = stage
    st.rerun()


def back() -> None:
    order = ["landing", "brief", "target", "results"]
    stage = st.session_state.stage
    if stage == "running":
        return
    idx = order.index(stage) if stage in order else 0
    st.session_state.stage = order[max(0, idx - 1)]
    st.rerun()


def top_bar() -> None:
    left, spacer, right = st.columns([1, 3, 1], gap="small")
    with left:
        if st.session_state.stage not in {"landing", "running"}:
            if st.button("Geri", key="back_button"):
                back()
    with right:
        provider, _ = runtime_api_config()
        strict_external = os.getenv("STRICT_EXTERNAL_DATA", "false").lower() in {"1", "true", "yes", "on"}
        demo_mode = not strict_external or provider == "local"
        if demo_mode:
            st.markdown('<div style="color:#f59e0b; font-weight:bold; text-align:right;">⚠️ Demo Modu (Sentetik Veri)</div>', unsafe_allow_html=True)


def parse_price(val: str, default: float = 100.0) -> float:
    try:
        cleaned = val.replace(',', '.').strip()
        return float(cleaned)
    except:
        return default


def runtime_api_config() -> tuple[str, str]:
    provider = os.getenv("API_PROVIDER", "local").lower()
    if provider == "openai":
        return provider, os.getenv("OPENAI_API_KEY", "")
    if provider == "gemini":
        return provider, os.getenv("GEMINI_API_KEY", "")
    return provider, ""


def form_input() -> dict:
    audience_parts = []
    if st.session_state.age_group and st.session_state.age_group != "Genel":
        audience_parts.append(st.session_state.age_group)
    if st.session_state.target_user.strip():
        audience_parts.append(st.session_state.target_user.strip())
    target_audience = "Genel hedef kitle" if not audience_parts else " / ".join(audience_parts)
    region = st.session_state.region.strip() or "Tüm Bölgeler"

    mp = parse_price(st.session_state.market_price)
    pp = parse_price(st.session_state.proposed_price)
    price_index = pp / mp if mp > 0 else 1.0

    return {
        "brand_name": st.session_state.company_name.strip() or "Firma",
        "campaign_title": st.session_state.product_name.strip() or "Pazarlama Kampanyası",
        "category": st.session_state.product_name.strip() or "Genel",
        "price_index": price_index,
        "region": region,
        "target_audience": target_audience,
        "campaign_description": st.session_state.campaign_description.strip(),
        "key_selling_points": st.session_state.campaign_description.strip()[:260],
    }


def results_to_df(results: list) -> pd.DataFrame:
    rows = []
    for item in results:
        agent = item.get("agent", {})
        metrics = item.get("metrics", {})
        initial_metrics = item.get("initial_metrics", metrics)
        rows.append(
            {
                "segment": agent.get("segment_name", "Segment"),
                "age": agent.get("age"),
                "income": agent.get("income_try"),
                "decision": metrics.get("decision"),
                "decision_tr": DECISION_TR.get(metrics.get("decision"), metrics.get("decision")),
                "purchase_likelihood": metrics.get("purchase_likelihood", 0),
                "initial_likelihood": initial_metrics.get("purchase_likelihood", metrics.get("purchase_likelihood", 0)),
                "mind_shift": item.get("mind_shift", {}).get("delta", 0),
                "resonance": metrics.get("resonance_score", 0),
                "objection": metrics.get("objection_score", 0),
            }
        )
    return pd.DataFrame(rows)


def conversion(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    return len(df[df["decision"].isin(["Buy", "Skeptical Buy"])]) / len(df) * 100


def nps(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    return (len(df[df["decision"] == "Buy"]) - len(df[df["decision"] == "Reject"])) / len(df) * 100


def decision_donut(df: pd.DataFrame, title: str):
    counts = df["decision_tr"].value_counts().reset_index()
    counts.columns = ["Karar", "Ajan"]
    fig = px.pie(
        counts,
        names="Karar",
        values="Ajan",
        hole=0.62,
        color="Karar",
        color_discrete_map={
            "Kesin Alır": THEMES[st.session_state.theme]["good"],
            "Şüpheyle Alır": THEMES[st.session_state.theme]["warn"],
            "Pas Geçer": THEMES[st.session_state.theme]["muted"],
            "Reddeder": THEMES[st.session_state.theme]["bad"],
        },
        title=title,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEMES[st.session_state.theme]["text"]),
        margin=dict(l=0, r=0, t=45, b=0),
        legend=dict(orientation="h", y=-0.12),
    )
    return fig


def comparison_chart(df_initial: pd.DataFrame, df_final: pd.DataFrame):
    data = pd.DataFrame(
        [
            {"Aşama": "İlk Survey", "Dönüşüm": conversion(df_initial)},
            {"Aşama": "Akran Müzakeresi Sonrası", "Dönüşüm": conversion(df_final)},
            {"Aşama": "Ağırlıklı Final", "Dönüşüm": conversion(df_initial) * 0.45 + conversion(df_final) * 0.55},
        ]
    )
    fig = px.bar(data, x="Aşama", y="Dönüşüm", text="Dönüşüm", range_y=[0, 100])
    fig.update_traces(marker_color=THEMES[st.session_state.theme]["accent"], texttemplate="%{text:.1f}%")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEMES[st.session_state.theme]["text"]),
        yaxis_title="Dönüşüm",
        xaxis_title="",
        margin=dict(l=0, r=0, t=20, b=0),
    )
    return fig


def segment_chart(df_initial: pd.DataFrame, df_final: pd.DataFrame):
    rows = []
    for label, df in [("İlk Survey", df_initial), ("Final", df_final)]:
        for segment, group in df.groupby("segment"):
            rows.append({"Segment": segment, "Aşama": label, "Dönüşüm": conversion(group)})
    data = pd.DataFrame(rows)
    fig = px.bar(data, x="Dönüşüm", y="Segment", color="Aşama", orientation="h", range_x=[0, 100])
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEMES[st.session_state.theme]["text"]),
        xaxis_title="Dönüşüm",
        yaxis_title="",
        margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=-0.16),
    )
    return fig


def insight_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def report_panel(title: str, eyebrow: str, body: str, chart=None) -> None:
    with st.container(border=False):
        st.markdown(
            f"""
            <section class="report-panel">
                <div class="eyebrow">{eyebrow}</div>
                <h2>{title}</h2>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if chart is not None:
            st.plotly_chart(chart, use_container_width=True)
        st.markdown(body)


def render_landing() -> None:
    # Full width, no columns for the pure hero look
    st.markdown(
        """
        <div class="hero">
            <h1><span class="gradient-text">DualMind</span><br>Yapay Zeka Destekli Pazarlama Simülasyon Platformu</h1>
            <p>
                Otonom yapay zeka ajanlarıyla tüketici davranışını simüle edin,<br>
                pazar dinamiklerini analiz edin ve kampanyalarınızı optimize edin.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Başla", type="primary", key="start_button", use_container_width=True):
            go_to("brief")


def render_brief() -> None:
    st.markdown('<div class="step-label">1 / 2</div><h1>Pazarlama Briefi</h1>', unsafe_allow_html=True)
    st.session_state.company_name = st.text_input("Firmanızın ismi nedir?", value=st.session_state.company_name)
    st.session_state.product_name = st.text_input("Pazarlamak istediğiniz ürün veya kampanya nedir?", value=st.session_state.product_name)
    st.session_state.campaign_description = st.text_area(
        "Pazarlama fikrini ve detaylarını açıklar mısınız?",
        value=st.session_state.campaign_description,
        height=220,
        placeholder="Ürün ne yapıyor, vaadi ne, neden şimdi pazara çıkıyor?",
    )
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.market_price = st.text_input("Piyasa ortalaması fiyat nedir?", value=st.session_state.market_price, placeholder="Örn: 500")
    with col2:
        st.session_state.proposed_price = st.text_input("Sizin düşündüğünüz fiyat nedir?", value=st.session_state.proposed_price, placeholder="Örn: 650")
    if st.button("Devam", type="primary", key="brief_next"):
        missing = not st.session_state.company_name.strip() or not st.session_state.product_name.strip() or not st.session_state.campaign_description.strip()
        if missing:
            st.warning("Devam etmeden önce firma, ürün/kampanya ve açıklama alanlarını doldurun.")
        else:
            go_to("target")


def render_target() -> None:
    st.markdown('<div class="step-label">2 / 2</div><h1>Hedefleme</h1>', unsafe_allow_html=True)
    st.session_state.region = st.text_input(
        "Bu pazarlamayı nerede yapmak istiyorsunuz?",
        value=st.session_state.region,
        placeholder="Ege Bölgesi, İstanbul, İzmir, Türkiye geneli...",
    )
    st.session_state.age_group = st.selectbox(
        "Hangi yaş grubunu hedefliyorsunuz?",
        ["Genel", "18-25", "26-35", "36-50", "50+", "Serbest"],
        index=["Genel", "18-25", "26-35", "36-50", "50+", "Serbest"].index(st.session_state.age_group),
    )
    st.session_state.target_user = st.text_area(
        "Hedef kullanıcı tipini serbestçe anlatabilirsiniz. Boş bırakırsanız genel kabul edilir.",
        value=st.session_state.target_user,
        height=170,
        placeholder="Örneğin: üniversite öğrencileri, yoğun çalışan beyaz yakalılar, emekli tüketiciler...",
    )
    st.markdown('<div class="brief-summary">Bu bilgiler MCP sorgularına ve 100 ajan profilinin oluşturulmasına brief olarak gönderilecek.</div>', unsafe_allow_html=True)
    if st.button("Analizi Başlat", type="primary", key="run_analysis"):
        st.session_state.stage = "running"
        st.session_state.run_started = False
        st.session_state.pipeline_result = None
        st.session_state.run_logs = []
        st.rerun()


def render_running() -> None:
    st.markdown('<div class="running-shell"><div class="eyebrow">Analiz çalışıyor</div><h1>MCP verileri alınıyor, ajanlar üretiliyor ve tartışmalar yürütülüyor.</h1></div>', unsafe_allow_html=True)
    console = st.empty()
    progress = st.progress(0)
    provider, api_key = runtime_api_config()
    strict_external = os.getenv("STRICT_EXTERNAL_DATA", "false").lower() in {"1", "true", "yes", "on"}
    demo_mode = not strict_external or provider == "local"

    if not demo_mode and (provider not in {"openai", "gemini"} or is_placeholder(api_key)):
        st.error("Analizi çalıştırmak için `.env` içinde API_PROVIDER=openai veya gemini seçilmeli ve ilgili API anahtarı doldurulmalı.")
        if st.button("Hedeflemeye Dön", key="api_back"):
            st.session_state.run_started = False
            go_to("target")
        return

    def on_progress(event: dict) -> None:
        message = event.get("message", "")
        phase = event.get("phase", "log")
        pct = event.get("progress")
        if pct is not None:
            progress.progress(max(0, min(1, float(pct))))
        st.session_state.run_logs.append(f"<span>{phase.upper()}</span> {message}")
        console.markdown(
            f"<div class='console'>{'<br>'.join(st.session_state.run_logs[-12:])}</div>",
            unsafe_allow_html=True,
        )

    if not st.session_state.run_started:
        st.session_state.run_started = True
        try:
            result = run_focus_group_pipeline(
                form_input=form_input(),
                market_report_text=None,
                agent_count=100,
                provider=provider,
                api_key=api_key,
                use_mcp=True,
                progress_callback=on_progress,
                sleep_seconds=0,
            )
            st.session_state.pipeline_result = result
            st.session_state.stage = "results"
            st.rerun()
        except Exception as exc:
            st.session_state.run_started = False
            st.error("Entegrasyon tamamlanmadan analiz başlatılamadı. API anahtarlarını ve MCP sunucu yollarını kontrol edin.")
            st.code(str(exc), language="text")
            if st.button("Hedeflemeye Dön", key="runtime_back"):
                go_to("target")


def render_results() -> None:
    result = st.session_state.pipeline_result
    if not result:
        st.info("Henüz rapor yok.")
        if st.button("Başa Dön"):
            go_to("landing")
        return

    df_initial = results_to_df(result["initial_results"])
    df_final = results_to_df(result["final_results"])
    weighted = conversion(df_initial) * 0.45 + conversion(df_final) * 0.55
    delta = conversion(df_final) - conversion(df_initial)

    st.markdown(
        f"""
        <div class="result-hero">
            <div class="eyebrow">Yönetici Raporu</div>
            <h1>{result['campaign']['brand']} için tüketici araştırması tamamlandı.</h1>
            <p>İlk survey, akran müzakeresi ve ağırlıklı final tek raporda birleştirildi.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        insight_card("İlk Survey", f"%{conversion(df_initial):.1f}", "İlk temas dönüşümü")
    with c2:
        insight_card("Müzakere Sonrası", f"%{conversion(df_final):.1f}", f"{delta:+.1f} puan değişim")
    with c3:
        insight_card("Ağırlıklı Final", f"%{weighted:.1f}", "Yönetici karar skoru")
    with c4:
        insight_card("NPS", f"{nps(df_final):+.1f}", "Final net tepki")

    st.plotly_chart(comparison_chart(df_initial, df_final), use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["1. İlk Survey", "2. Akran Müzakeresi", "3. Ağırlıklı Final"])
    with tab1:
        left, right = st.columns([0.9, 1.1])
        with left:
            st.plotly_chart(decision_donut(df_initial, "İlk Karar Dağılımı"), use_container_width=True)
        with right:
            report_panel(
                "İlk Temas Sonucu",
                "Survey 1",
                result["reports"].get("report_1_initial", ""),
            )
    with tab2:
        left, right = st.columns([0.95, 1.05])
        with left:
            st.plotly_chart(segment_chart(df_initial, df_final), use_container_width=True)
        with right:
            report_panel(
                "Ajanlar konuşunca ne değişti?",
                "Survey 2",
                result["reports"].get("report_2_post_debate", ""),
            )
    with tab3:
        left, right = st.columns([0.9, 1.1])
        with left:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=weighted,
                number={"suffix": "%"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": THEMES[st.session_state.theme]["accent"]},
                    "steps": [
                        {"range": [0, 35], "color": "rgba(239,68,68,.25)"},
                        {"range": [35, 65], "color": "rgba(245,158,11,.25)"},
                        {"range": [65, 100], "color": "rgba(34,197,94,.25)"},
                    ],
                },
                title={"text": "Ağırlıklı Final Skor"},
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color=THEMES[st.session_state.theme]["text"]),
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        with right:
            report_panel(
                "Yönetici Aksiyon Planı",
                "Final",
                result["reports"].get("report_3_final", ""),
            )

    report_bundle = "\n\n---\n\n".join(
        [
            result["reports"].get("report_1_initial", ""),
            result["reports"].get("report_2_post_debate", ""),
            result["reports"].get("report_3_final", ""),
        ]
    )
    dl1, dl2 = st.columns([1, 1])
    with dl1:
        st.download_button("Raporu İndir (Markdown)", report_bundle, "yonetici_raporu.md", "text/markdown", use_container_width=True)
    with dl2:
        st.download_button(
            "Sonuçları İndir (JSON)",
            json.dumps(result["stats"], ensure_ascii=False, indent=2),
            "simulasyon_ozet.json",
            "application/json",
            use_container_width=True,
        )


init_state()
apply_theme()
top_bar()

if st.session_state.stage == "landing":
    render_landing()
elif st.session_state.stage == "brief":
    render_brief()
elif st.session_state.stage == "target":
    render_target()
elif st.session_state.stage == "running":
    render_running()
elif st.session_state.stage == "results":
    render_results()
