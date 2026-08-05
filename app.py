import base64
import html
import os
import zipfile
from io import BytesIO
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from utils.video_extractor import get_video_metadata
from utils.seo_agents import run_seo_analysis_with_langchain
from utils.output_guard import normalize_timestamps
from utils.thumbnails import (
    build_seo_thumbnail_brief,
    create_thumbnail_preview,
    generate_hd_thumbnail,
    get_relevant_overlay_text,
)

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env", override=True)

for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    if "127.0.0.1:9" in os.environ.get(proxy_key, ""):
        os.environ.pop(proxy_key, None)


def image_to_png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def thumbnails_zip_bytes(items):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in items:
            option = int(item.get("option", 1))
            archive.writestr(
                f"seo_agent_thumbnail_direction_{option:02d}.png",
                item.get("bytes", b""),
            )
    return buffer.getvalue()


def asset_data_uri(path):
    image_path = Path(path)
    if not image_path.exists():
        return ""
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def safe(value):
    return html.escape(str(value or ""))


def icon_svg(name):
    icons = {
        "spark": '<path d="m12 2 2.4 7.1L22 12l-7.6 2.9L12 22l-2.4-7.1L2 12l7.6-2.9L12 2Zm0 6.2-.9 2.8-2.9 1 2.9 1 .9 2.8.9-2.8 2.9-1-2.9-1-.9-2.8Z"/>',
        "search": '<path d="M11 4a7 7 0 1 0 4.9 12l4.1 4 1.4-1.4-4-4A7 7 0 0 0 11 4Zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z"/>',
        "tag": '<path d="M3 12V4h8l10 10-7 7L3 12Zm4-5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"/>',
        "chart": '<path d="M4 20V10h4v10H4Zm6 0V4h4v16h-4Zm6 0V8h4v12h-4Z"/>',
        "image": '<path d="M4 4h16v16H4V4Zm2 2v9.2l3.8-3.8 3.2 3.2 2.1-2.1 2.9 2.9V6H6Zm3 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/>',
        "play": '<path d="M8 5v14l12-7L8 5Z"/>',
    }
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{icons.get(name, icons["spark"])}</svg>'


def feature_card(icon, title, detail):
    return (
        '<div class="aurelia-feature">'
        f'<div class="aurelia-icon">{icon_svg(icon)}</div>'
        f'<strong>{safe(title)}</strong><span>{safe(detail)}</span>'
        '</div>'
    )


def format_duration(total_seconds):
    try:
        seconds = int(total_seconds)
    except (TypeError, ValueError):
        return "Unavailable"
    hours, remaining = divmod(seconds, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


def format_views(value):
    try:
        return f"{int(value):,}" if value is not None else "Unavailable"
    except (TypeError, ValueError):
        return "Unavailable"

st.set_page_config(
    page_title="SEO Agent | Video SEO Studio",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

/* REMOVE STREAMLIT TOP WHITE BAR */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0px !important;
}

[data-testid="stToolbar"] {
    right: 1rem !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stStatusWidget"] {
    display: none !important;
}

.main .block-container {
    padding-top: 1rem !important;
}

/* GLOBAL FONT */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
            
.stApp {
    background:
        radial-gradient(circle at top left, rgba(0,229,255,0.16), transparent 35%),
        radial-gradient(circle at top right, rgba(255,23,68,0.10), transparent 35%),
        linear-gradient(135deg, #020617 0%, #071126 45%, #020617 100%);
    color: #F8FAFC;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #071126 45%, #020617 100%) !important;
    border-right: 1px solid rgba(56,189,248,0.25);
}

section[data-testid="stSidebar"] * {
    color: #E5E7EB !important;
}

.hero {
    padding: 42px;
    border-radius: 30px;
    background:
        linear-gradient(135deg, rgba(15,23,42,0.95), rgba(8,47,73,0.88)),
        radial-gradient(circle at top right, rgba(0,229,255,0.22), transparent 35%);
    border: 1px solid rgba(56,189,248,0.30);
    box-shadow: 0 25px 70px rgba(0,0,0,0.55);
    margin-bottom: 28px;
}

.hero-badge {
    display: inline-block;
    padding: 8px 16px;
    border-radius: 999px;
    background: rgba(14,165,233,0.16);
    color: #67E8F9;
    border: 1px solid rgba(103,232,249,0.35);
    font-size: 0.85rem;
    font-weight: 900;
    margin-bottom: 16px;
}

.hero h1 {
    font-size: 3.4rem;
    line-height: 1.08;
    font-weight: 900;
    margin: 0 0 14px 0;
    background: linear-gradient(90deg, #FFFFFF, #67E8F9, #38BDF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero p {
    font-size: 1.12rem;
    color: #CBD5E1;
    max-width: 900px;
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-top: 24px;
}

.feature-card {
    background: rgba(15,23,42,0.78);
    border: 1px solid rgba(148,163,184,0.20);
    border-radius: 18px;
    padding: 16px;
    color: #E2E8F0;
    font-weight: 800;
}

.glass-card {
    padding: 22px;
    border-radius: 24px;
    background: rgba(15,23,42,0.82);
    border: 1px solid rgba(56,189,248,0.22);
    box-shadow: 0 18px 45px rgba(0,0,0,0.38);
}

.glass-card * {
    color: #F8FAFC !important;
}

.section-title {
    font-size: 1.8rem;
    font-weight: 900;
    color: #67E8F9;
    margin-top: 8px;
    margin-bottom: 18px;
}

.tag-pill {
    background: linear-gradient(135deg, #0EA5E9, #2563EB);
    color: white;
    padding: 9px 15px;
    border-radius: 999px;
    margin: 6px;
    display: inline-block;
    font-weight: 800;
    border: 1px solid rgba(255,255,255,0.16);
    box-shadow: 0 8px 18px rgba(14,165,233,0.18);
}

.timestamp-card {
    background: linear-gradient(135deg, rgba(14,165,233,0.25), rgba(15,23,42,0.92));
    padding: 14px 18px;
    border-radius: 16px;
    margin-bottom: 11px;
    color: white;
    border: 1px solid rgba(56,189,248,0.22);
}

.thumbnail-card {
    background: rgba(15,23,42,0.86);
    border-radius: 26px;
    padding: 24px;
    margin-bottom: 30px;
    border: 1px solid rgba(56,189,248,0.24);
    box-shadow: 0 22px 55px rgba(0,0,0,0.42);
}

.thumbnail-card * {
    color: white !important;
}

/* PREMIUM DARK INPUTS */
.stTextInput input,
.stTextArea textarea {
    background: rgba(15,23,42,0.96) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(56,189,248,0.55) !important;
    border-radius: 16px !important;
    padding: 14px !important;
    font-weight: 700 !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03),
                0 8px 30px rgba(0,0,0,0.28) !important;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #94A3B8 !important;
}

/* PREMIUM DARK SELECTBOX */
.stSelectbox > div > div {
    background: rgba(15,23,42,0.96) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(56,189,248,0.55) !important;
    min-height: 56px !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03),
                0 8px 28px rgba(0,0,0,0.28) !important;
}

.stSelectbox div[data-baseweb="select"] span {
    color: #FFFFFF !important;
    font-weight: 800 !important;
}

.stSelectbox svg {
    fill: #67E8F9 !important;
}

div[role="listbox"] {
    background: #0F172A !important;
    border: 1px solid rgba(56,189,248,0.45) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}

div[role="option"] {
    background: #0F172A !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

div[role="option"]:hover {
    background: rgba(14,165,233,0.24) !important;
}

label {
    color: #E2E8F0 !important;
    font-weight: 800 !important;
}

.stButton > button {
    background: linear-gradient(135deg, #0284C7, #06B6D4);
    color: white;
    border-radius: 14px;
    border: none;
    font-weight: 900;
    padding: 0.78rem 1.45rem;
    box-shadow: 0 12px 28px rgba(14,165,233,0.30);
}

.stDownloadButton > button {
    background: linear-gradient(135deg, #E11D48, #F97316);
    color: white;
    border-radius: 14px;
    border: none;
    font-weight: 900;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-weight: 900;
}

[data-testid="stMetricLabel"] {
    color: #BAE6FD !important;
    font-weight: 800;
}

.stAlert {
    background: linear-gradient(135deg, rgba(14,165,233,0.30), rgba(37,99,235,0.24)) !important;
    color: white !important;
    border-radius: 16px !important;
    border: 1px solid rgba(125,211,252,0.28) !important;
}

.stAlert * {
    color: white !important;
    font-weight: 800 !important;
}

.stApp {
    background:
        radial-gradient(circle at 12% 5%, rgba(34, 197, 94, 0.15), transparent 27rem),
        radial-gradient(circle at 88% 3%, rgba(244, 114, 182, 0.13), transparent 24rem),
        linear-gradient(145deg, #071014 0%, #0d1820 48%, #160f18 100%);
}

.hero {
    border-radius: 8px;
    padding: 38px 42px;
    background:
        linear-gradient(115deg, rgba(6, 15, 19, 0.94), rgba(14, 31, 38, 0.86)),
        linear-gradient(90deg, rgba(34, 197, 94, 0.22), rgba(251, 113, 133, 0.10));
    border: 1px solid rgba(180, 228, 215, 0.20);
}

.hero h1 {
    font-size: 3rem;
    background: linear-gradient(90deg, #f8fafc, #8be0bf, #ffc27c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.feature-card,
.glass-card,
.thumbnail-card {
    border-radius: 8px;
    border-color: rgba(180, 228, 215, 0.18);
    background: rgba(8, 18, 24, 0.82);
}

.feature-card {
    min-height: 62px;
    display: flex;
    align-items: center;
    color: #f1f5f9;
}

.section-title {
    color: #8be0bf;
}

.studio-shell {
    padding: 22px;
    border: 1px solid rgba(180, 228, 215, 0.18);
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(8, 18, 24, 0.92), rgba(28, 18, 25, 0.82));
    margin: 10px 0 20px;
}

.studio-kicker {
    color: #ffc27c;
    font-size: 0.82rem;
    font-weight: 900;
    letter-spacing: 0;
    text-transform: uppercase;
}

.studio-shell h3 {
    margin: 8px 0 8px;
    font-size: 1.7rem;
}

.studio-shell p {
    color: #cbd5e1;
    margin-bottom: 0;
}

.concept-card {
    min-height: 168px;
    padding: 18px;
    margin: 10px 0 18px;
    border-radius: 8px;
    background: rgba(8, 18, 24, 0.70);
    border: 1px solid rgba(255, 194, 124, 0.16);
}

.concept-label {
    color: #ffc27c;
    font-size: 0.78rem;
    font-weight: 900;
    text-transform: uppercase;
}

.concept-card strong {
    color: #f8fafc;
    display: block;
    font-size: 1.05rem;
    margin: 8px 0;
}

.concept-card p {
    color: #cbd5e1;
    margin: 0;
}

.status-chip {
    display: inline-block;
    padding: 7px 11px;
    margin: 0 8px 8px 0;
    border-radius: 999px;
    background: rgba(139, 224, 191, 0.14);
    border: 1px solid rgba(139, 224, 191, 0.24);
    color: #d9fff0;
    font-size: 0.82rem;
    font-weight: 800;
}

.thumbnail-card img {
    border-radius: 8px;
}

.stButton > button {
    border-radius: 8px;
    background: linear-gradient(135deg, #159b70, #2563eb);
}

.stDownloadButton > button {
    border-radius: 8px;
    background: linear-gradient(135deg, #f97316, #e11d48);
}

/* Executive workspace refresh */
:root {
    --ink: #0b0d12;
    --ink-soft: #111625;
    --panel: rgba(16, 21, 34, 0.92);
    --panel-strong: rgba(20, 25, 40, 0.98);
    --paper: #f5f1e8;
    --muted: #b8becb;
    --line: rgba(233, 224, 204, 0.14);
    --teal: #5fd0b5;
    --gold: #e9b873;
    --coral: #e96e74;
    --blue: #7da7ff;
}

html, body, [class*="css"] {
    letter-spacing: 0 !important;
}

.stApp {
    background:
        linear-gradient(145deg, #090b10 0%, #101525 44%, #19121c 100%) !important;
    color: var(--paper);
}

.block-container {
    max-width: 1420px;
    padding-top: 1.2rem !important;
}

section[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, rgba(10, 12, 18, 0.99), rgba(18, 17, 29, 0.98)) !important;
    border-right: 1px solid var(--line);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.4rem;
}

section[data-testid="stSidebar"] img {
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.03);
}

section[data-testid="stSidebar"] h1 {
    color: var(--paper) !important;
    font-size: 1.45rem !important;
    margin-bottom: 0.9rem;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--muted) !important;
}

.hero {
    position: relative;
    overflow: hidden;
    padding: 42px !important;
    margin: 0 0 24px;
    border-radius: 8px !important;
    border: 1px solid rgba(233, 184, 115, 0.24) !important;
    background:
        linear-gradient(125deg, rgba(14, 18, 29, 0.98), rgba(24, 25, 42, 0.95) 52%, rgba(41, 25, 31, 0.90)) !important;
    box-shadow:
        0 28px 72px rgba(0, 0, 0, 0.42),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.hero::after {
    content: "";
    position: absolute;
    inset: auto 0 0 0;
    height: 4px;
    background: linear-gradient(90deg, var(--teal), var(--gold), var(--coral));
}

.hero-badge {
    border-radius: 999px;
    background: rgba(95, 208, 181, 0.10) !important;
    border-color: rgba(95, 208, 181, 0.28) !important;
    color: #b7f2e2 !important;
    padding: 8px 13px !important;
}

.hero h1 {
    max-width: 980px;
    color: var(--paper);
    font-size: 3.2rem !important;
    line-height: 1.02;
    background: linear-gradient(90deg, #fff8ea, #d7efe9 52%, #ffd4a0) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.hero p {
    color: #d2d6df !important;
    max-width: 820px;
    line-height: 1.55;
}

.feature-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
}

.feature-card {
    position: relative;
    min-height: 72px;
    padding: 17px 18px !important;
    border-radius: 8px !important;
    color: var(--paper) !important;
    background: rgba(255, 255, 255, 0.045) !important;
    border: 1px solid var(--line) !important;
    box-shadow: none !important;
}

.feature-card::before {
    content: "";
    width: 9px;
    height: 9px;
    margin-right: 11px;
    flex: 0 0 9px;
    border-radius: 999px;
    background: linear-gradient(135deg, var(--teal), var(--gold));
}

.glass-card,
.thumbnail-card,
.studio-shell,
.concept-card {
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
    background:
        linear-gradient(145deg, rgba(18, 24, 39, 0.95), rgba(20, 19, 31, 0.92)) !important;
    box-shadow:
        0 20px 46px rgba(0, 0, 0, 0.28),
        inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

.glass-card {
    min-height: 100%;
}

.section-title {
    color: var(--paper) !important;
    font-size: 1.65rem;
    letter-spacing: 0;
    padding-left: 14px;
    border-left: 3px solid var(--gold);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    padding: 6px;
    margin: 6px 0 22px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.035);
}

.stTabs [data-baseweb="tab"] {
    height: 48px;
    padding: 0 16px;
    border-radius: 6px;
    color: var(--muted);
    font-weight: 800;
}

.stTabs [aria-selected="true"] {
    color: var(--paper) !important;
    background: linear-gradient(135deg, rgba(95, 208, 181, 0.20), rgba(125, 167, 255, 0.16));
    border: 1px solid rgba(95, 208, 181, 0.24);
}

.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div {
    border-radius: 8px !important;
    border: 1px solid rgba(233, 224, 204, 0.22) !important;
    background: rgba(8, 11, 18, 0.86) !important;
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.03),
        0 10px 28px rgba(0, 0, 0, 0.18) !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: rgba(95, 208, 181, 0.62) !important;
    box-shadow: 0 0 0 1px rgba(95, 208, 181, 0.30) !important;
}

label,
.stSelectbox div[data-baseweb="select"] span {
    color: var(--paper) !important;
}

.stButton > button,
.stDownloadButton > button {
    min-height: 48px;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    color: #091017 !important;
    font-weight: 900 !important;
    transition: transform 120ms ease, filter 120ms ease, box-shadow 120ms ease;
}

.stButton > button {
    background: linear-gradient(135deg, #78e0c8, #6b9fff) !important;
    box-shadow: 0 14px 34px rgba(69, 151, 184, 0.24) !important;
}

.stDownloadButton > button {
    background: linear-gradient(135deg, #f0c57f, #ea737b) !important;
    box-shadow: 0 14px 34px rgba(233, 110, 116, 0.20) !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    transform: translateY(-1px);
    filter: saturate(1.08);
}

.tag-pill {
    margin: 5px 4px;
    padding: 8px 13px;
    border-radius: 999px;
    background: rgba(125, 167, 255, 0.12) !important;
    border: 1px solid rgba(125, 167, 255, 0.24) !important;
    box-shadow: none !important;
    color: #dae5ff !important;
}

.timestamp-card {
    border-radius: 8px !important;
    border: 1px solid var(--line) !important;
    background: linear-gradient(135deg, rgba(95, 208, 181, 0.12), rgba(20, 25, 40, 0.94)) !important;
}

.status-chip {
    background: rgba(233, 184, 115, 0.12) !important;
    border-color: rgba(233, 184, 115, 0.26) !important;
    color: #ffdfb0 !important;
}

.concept-card {
    min-height: 184px;
    padding: 20px !important;
}

.concept-label {
    color: var(--gold) !important;
}

[data-testid="stMetric"] {
    padding: 13px 14px;
    border-radius: 8px;
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.035);
}

[data-testid="stMetricValue"] {
    color: var(--paper) !important;
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
}

.stAlert {
    border-radius: 8px !important;
    background: linear-gradient(135deg, rgba(95, 208, 181, 0.13), rgba(125, 167, 255, 0.10)) !important;
    border: 1px solid rgba(95, 208, 181, 0.22) !important;
}

hr {
    border-color: var(--line) !important;
}

@media (max-width: 860px) {
    .hero {
        padding: 28px !important;
    }

    .hero h1 {
        font-size: 2.25rem !important;
    }

    .feature-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 520px) {
    .feature-grid {
        grid-template-columns: 1fr;
    }
}

h1, h2, h3, h4, h5, h6, p, span {
    color: inherit;
}
</style>
""", unsafe_allow_html=True)

hero_image_uri = asset_data_uri("assets/logo.png")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');

:root {{
    --aur-bg: #070a12;
    --aur-panel: rgba(14, 20, 34, 0.86);
    --aur-panel-strong: rgba(17, 25, 42, 0.96);
    --aur-line: rgba(233, 213, 172, 0.16);
    --aur-text: #f7f3ea;
    --aur-muted: #a8b2c3;
    --aur-gold: #e8c77f;
    --aur-gold-soft: #fff0b8;
    --aur-aqua: #59dfc7;
    --aur-blue: #7ea6ff;
    --aur-coral: #f47d78;
}}

html, body, [class*="css"] {{
    font-family: "Manrope", sans-serif !important;
    letter-spacing: 0 !important;
}}

.stApp {{
    background:
        radial-gradient(circle at 78% -10%, rgba(126, 166, 255, 0.16), transparent 31rem),
        radial-gradient(circle at 16% 11%, rgba(89, 223, 199, 0.10), transparent 27rem),
        linear-gradient(145deg, #060810 0%, #09101d 44%, #0d1422 100%) !important;
    color: var(--aur-text) !important;
}}

.block-container {{
    max-width: 1440px !important;
    padding-top: 1.45rem !important;
}}

section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #080c16 0%, #0c1321 100%) !important;
    border-right: 1px solid var(--aur-line) !important;
}}

.aurelia-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 0 24px;
}}

.aurelia-mark {{
    width: 48px;
    height: 48px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    background: linear-gradient(145deg, var(--aur-gold-soft), var(--aur-gold));
    color: #07101b;
    font-family: "Playfair Display", serif;
    font-size: 28px;
    font-weight: 700;
    box-shadow: 0 14px 34px rgba(232, 199, 127, 0.16);
}}

.aurelia-brand strong {{
    display: block;
    color: var(--aur-text);
    font-size: 1.15rem;
    line-height: 1.1;
}}

.aurelia-brand span,
.side-label {{
    display: block;
    color: var(--aur-gold);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}}

.side-label {{
    margin: 24px 0 9px;
}}

.sidebar-note {{
    padding: 13px;
    margin-top: 16px;
    border-radius: 14px;
    border: 1px solid rgba(89, 223, 199, 0.17);
    background: rgba(89, 223, 199, 0.06);
    color: #c7d7d5;
    font-size: 0.82rem;
    line-height: 1.5;
}}

.hero {{
    position: relative !important;
    overflow: hidden !important;
    display: block !important;
    min-height: auto !important;
    padding: 0 !important;
    border-radius: 26px !important;
    border: 1px solid var(--aur-line) !important;
    background:
        radial-gradient(circle at 92% 20%, rgba(232, 199, 127, 0.11), transparent 22rem),
        linear-gradient(125deg, rgba(14, 21, 36, 0.97), rgba(15, 25, 44, 0.93)) !important;
    box-shadow: 0 30px 74px rgba(0, 0, 0, 0.34) !important;
    margin-bottom: 24px !important;
}}

.hero::after {{
    content: "";
    position: absolute;
    left: 48px;
    right: 48px;
    bottom: 0;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--aur-gold), var(--aur-aqua), transparent) !important;
}}

.hero-layout {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) 390px;
    gap: 38px;
    align-items: center;
    padding: 52px 50px 38px;
}}

.hero-copy {{
    min-width: 0;
}}

.hero-badge {{
    display: inline-flex !important;
    align-items: center;
    gap: 8px;
    padding: 8px 14px !important;
    border-radius: 999px !important;
    color: var(--aur-gold-soft) !important;
    background: rgba(232, 199, 127, 0.08) !important;
    border: 1px solid rgba(232, 199, 127, 0.25) !important;
    font-size: 0.72rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}

.hero-badge svg {{
    width: 14px;
    height: 14px;
    fill: var(--aur-gold-soft);
}}

.hero h1 {{
    max-width: 850px !important;
    margin: 20px 0 16px !important;
    color: var(--aur-text) !important;
    font-family: "Playfair Display", serif !important;
    font-size: clamp(2.75rem, 4.8vw, 4.35rem) !important;
    font-weight: 600 !important;
    line-height: 1.05 !important;
    letter-spacing: 0 !important;
    background: none !important;
    -webkit-text-fill-color: currentColor !important;
}}

.hero h1 em {{
    color: var(--aur-gold-soft);
    font-style: normal;
}}

.hero p {{
    max-width: 720px !important;
    color: var(--aur-muted) !important;
    font-size: 1.05rem !important;
    line-height: 1.72 !important;
    margin: 0 !important;
}}

.hero-actions {{
    margin-top: 24px !important;
}}

.hero-chip,
.status-chip {{
    display: inline-flex !important;
    align-items: center;
    margin: 0 8px 10px 0 !important;
    padding: 8px 13px !important;
    border-radius: 999px !important;
    border: 1px solid rgba(89, 223, 199, 0.18) !important;
    background: rgba(89, 223, 199, 0.07) !important;
    color: #bdf7ed !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
}}

.hero-visual {{
    position: relative;
    min-height: 350px;
    display: grid;
    place-items: center;
}}

.preview-orbit {{
    position: absolute;
    width: 330px;
    height: 330px;
    border-radius: 50%;
    border: 1px solid rgba(232, 199, 127, 0.15);
}}

.preview-panel {{
    position: relative;
    width: min(100%, 340px);
    overflow: hidden;
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.13);
    background: rgba(5, 8, 14, 0.74);
    box-shadow: 0 26px 58px rgba(0, 0, 0, 0.42);
}}

.preview-panel img {{
    display: block;
    width: 100%;
    aspect-ratio: 16 / 11;
    object-fit: cover;
    filter: saturate(0.9) contrast(1.05);
}}

.preview-bars {{
    padding: 16px;
}}

.preview-line {{
    height: 9px;
    border-radius: 999px;
    margin: 9px 0;
    background: rgba(255, 255, 255, 0.14);
}}

.preview-line:nth-child(1) {{
    width: 76%;
    background: linear-gradient(90deg, var(--aur-gold), var(--aur-aqua));
}}

.preview-line:nth-child(2) {{ width: 58%; }}
.preview-line:nth-child(3) {{ width: 88%; }}

.live-chip {{
    position: absolute;
    left: 8px;
    bottom: 24px;
    padding: 9px 13px;
    border-radius: 999px;
    color: var(--aur-text);
    background: rgba(7, 10, 18, 0.84);
    border: 1px solid var(--aur-line);
    font-size: 0.72rem;
    font-weight: 800;
}}

.aur-features {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    padding: 0 50px 42px;
}}

.hero > .feature-grid,
.workflow-grid {{
    display: none !important;
}}

.aurelia-feature {{
    min-height: 142px;
    padding: 18px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.13);
    background: rgba(255, 255, 255, 0.027);
    transition: transform 0.2s ease, border-color 0.2s ease;
}}

.aurelia-feature:hover {{
    transform: translateY(-3px);
    border-color: rgba(232, 199, 127, 0.34);
}}

.aurelia-icon {{
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    margin-bottom: 14px;
    border-radius: 12px;
    background: rgba(232, 199, 127, 0.10);
}}

.aurelia-icon svg {{
    width: 21px;
    height: 21px;
    fill: var(--aur-gold-soft);
}}

.aurelia-feature strong {{
    display: block;
    color: var(--aur-text);
    font-size: 0.95rem;
    margin-bottom: 5px;
}}

.aurelia-feature span {{
    display: block;
    color: var(--aur-muted);
    font-size: 0.78rem;
    line-height: 1.45;
}}

.input-panel {{
    border: 1px solid var(--aur-line);
    border-radius: 20px;
    padding: 22px 25px 15px;
    margin-bottom: 22px;
    background: rgba(14, 21, 36, 0.78);
}}

.input-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--aur-text);
    font-weight: 800;
    margin-bottom: 14px;
}}

.input-title svg {{
    width: 21px;
    height: 21px;
    fill: var(--aur-gold);
}}

.glass-card,
.thumbnail-card,
.studio-shell,
.concept-card {{
    border-radius: 18px !important;
    border: 1px solid var(--aur-line) !important;
    background: linear-gradient(145deg, rgba(15, 24, 41, 0.94), rgba(12, 19, 33, 0.91)) !important;
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.20) !important;
}}

.section-title {{
    font-family: "Playfair Display", serif !important;
    border-left: 0 !important;
    padding-left: 0 !important;
    color: var(--aur-text) !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    border-radius: 14px !important;
    background: rgba(14, 21, 36, 0.78) !important;
    border: 1px solid var(--aur-line) !important;
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 10px !important;
}}

.stTabs [aria-selected="true"] {{
    background: rgba(232, 199, 127, 0.12) !important;
    color: var(--aur-text) !important;
}}

.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div {{
    min-height: 50px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(148, 163, 184, 0.19) !important;
    background: rgba(7, 10, 18, 0.74) !important;
}}

.stTextInput input:focus,
.stTextArea textarea:focus {{
    border-color: rgba(232, 199, 127, 0.62) !important;
    box-shadow: 0 0 0 1px rgba(232, 199, 127, 0.20) !important;
}}

.stButton > button {{
    min-height: 50px !important;
    border-radius: 12px !important;
    color: #07101b !important;
    background: linear-gradient(125deg, var(--aur-gold-soft), var(--aur-gold)) !important;
    box-shadow: 0 13px 28px rgba(232, 199, 127, 0.14) !important;
}}

.stDownloadButton > button {{
    min-height: 50px !important;
    border-radius: 12px !important;
    color: var(--aur-text) !important;
    background: rgba(89, 223, 199, 0.09) !important;
    border: 1px solid rgba(89, 223, 199, 0.25) !important;
}}

.tag-pill {{
    background: rgba(126, 166, 255, 0.12) !important;
    border-color: rgba(126, 166, 255, 0.20) !important;
    color: #dfe7ff !important;
}}

.timestamp-card {{
    border-radius: 14px !important;
    background: rgba(89, 223, 199, 0.055) !important;
    border-color: rgba(89, 223, 199, 0.15) !important;
}}

.thumbnail-card img,
[data-testid="stImage"] img {{
    border-radius: 14px !important;
}}

h4[style*="margin-bottom:8px"] {{
    display: none !important;
}}

@media (max-width: 1120px) {{
    .hero-layout {{
        grid-template-columns: 1fr;
    }}
    .hero-visual {{
        min-height: 310px;
    }}
    .aur-features {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}

@media (max-width: 620px) {{
    .hero-layout {{
        padding: 32px 24px 28px;
    }}
    .aur-features {{
        grid-template-columns: 1fr;
        padding: 0 24px 28px;
    }}
}}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
:root {{
    --studio-bg: #070a10;
    --studio-panel: rgba(12, 18, 31, 0.84);
    --studio-panel-strong: rgba(14, 21, 35, 0.96);
    --studio-line: rgba(223, 236, 255, 0.14);
    --studio-text: #f6f8fb;
    --studio-muted: #aab6c9;
    --studio-teal: #52e6c4;
    --studio-blue: #6aa9ff;
    --studio-coral: #ff746d;
    --studio-gold: #ffd084;
}}

.stApp {{
    background:
        linear-gradient(135deg, rgba(7, 10, 16, 0.96), rgba(10, 14, 24, 0.97)),
        radial-gradient(circle at 18% 0%, rgba(82, 230, 196, 0.13), transparent 32rem),
        radial-gradient(circle at 92% 8%, rgba(255, 116, 109, 0.10), transparent 30rem) !important;
    color: var(--studio-text);
}}

.block-container {{
    max-width: 1440px;
    padding-top: 1.1rem !important;
}}

section[data-testid="stSidebar"] {{
    background:
        linear-gradient(180deg, rgba(8, 11, 18, 0.98), rgba(13, 18, 31, 0.98)) !important;
    border-right: 1px solid var(--studio-line) !important;
}}

section[data-testid="stSidebar"] img {{
    border: 0 !important;
    background: transparent !important;
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.24);
}}

.hero {{
    min-height: 420px;
    display: grid;
    align-items: end;
    padding: 44px !important;
    margin-bottom: 22px !important;
    border-radius: 18px !important;
    border: 1px solid rgba(223, 236, 255, 0.16) !important;
    background-image:
        linear-gradient(90deg, rgba(5, 8, 14, 0.96) 0%, rgba(5, 8, 14, 0.86) 39%, rgba(5, 8, 14, 0.20) 72%),
        linear-gradient(180deg, rgba(5, 8, 14, 0.10), rgba(5, 8, 14, 0.84)),
        url("{hero_image_uri}") !important;
    background-size: cover !important;
    background-position: center !important;
    box-shadow: 0 30px 90px rgba(0, 0, 0, 0.48) !important;
}}

.hero::after {{
    height: 5px !important;
    background: linear-gradient(90deg, var(--studio-teal), var(--studio-blue), var(--studio-coral), var(--studio-gold)) !important;
}}

.hero-content {{
    max-width: 790px;
}}

.hero-badge {{
    color: #d9fff6 !important;
    background: rgba(82, 230, 196, 0.12) !important;
    border: 1px solid rgba(82, 230, 196, 0.34) !important;
    box-shadow: 0 0 28px rgba(82, 230, 196, 0.10);
}}

.hero h1 {{
    max-width: 780px;
    margin-bottom: 16px !important;
    font-size: clamp(2.4rem, 5vw, 4.65rem) !important;
    line-height: 0.98 !important;
    letter-spacing: 0 !important;
    background: linear-gradient(92deg, #ffffff, #ccfff3 42%, #ffd99d) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}}

.hero p {{
    max-width: 690px;
    color: #d7deeb !important;
    font-size: 1.1rem !important;
}}

.hero-actions {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 22px;
}}

.hero-chip,
.status-chip {{
    border-radius: 999px !important;
    padding: 8px 12px !important;
    border: 1px solid rgba(223, 236, 255, 0.16) !important;
    background: rgba(255, 255, 255, 0.07) !important;
    color: #eef6ff !important;
    font-size: 0.84rem !important;
    font-weight: 800 !important;
}}

.feature-grid {{
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
}}

.hero > .feature-grid {{
    display: none !important;
}}

.feature-card,
.glass-card,
.thumbnail-card,
.studio-shell,
.concept-card,
.workflow-card {{
    border-radius: 14px !important;
    border: 1px solid var(--studio-line) !important;
    background: linear-gradient(145deg, rgba(14, 21, 35, 0.90), rgba(12, 16, 27, 0.78)) !important;
    box-shadow: 0 22px 54px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}}

.feature-card {{
    min-height: 86px !important;
    display: block !important;
    padding: 16px !important;
    font-size: 0.98rem;
}}

.feature-card::before {{
    display: none !important;
}}

.feature-card span {{
    display: block;
    margin-bottom: 7px;
    color: var(--studio-teal);
    font-size: 0.78rem;
    font-weight: 900;
    text-transform: uppercase;
}}

.workflow-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin: 8px 0 24px;
}}

.workflow-card {{
    padding: 18px;
    min-height: 128px;
}}

.workflow-step {{
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    margin-bottom: 14px;
    border-radius: 10px;
    color: #061018;
    font-weight: 900;
    background: linear-gradient(135deg, var(--studio-teal), var(--studio-gold));
}}

.workflow-card strong {{
    display: block;
    margin-bottom: 6px;
    color: var(--studio-text);
}}

.workflow-card p {{
    margin: 0;
    color: var(--studio-muted);
    font-size: 0.9rem;
}}

.section-title {{
    color: var(--studio-text) !important;
    border-left: 4px solid var(--studio-teal) !important;
}}

.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div {{
    border-radius: 12px !important;
    border-color: rgba(223, 236, 255, 0.18) !important;
    background: rgba(7, 10, 16, 0.88) !important;
}}

.stButton > button {{
    border-radius: 12px !important;
    background: linear-gradient(135deg, var(--studio-teal), var(--studio-blue)) !important;
    color: #061018 !important;
}}

h4[style*="margin-bottom:8px"] {{
    font-size: 0 !important;
}}

h4[style*="margin-bottom:8px"]::after {{
    content: "Enter YouTube Video URL";
    font-size: 1rem;
    color: #ffffff;
    font-weight: 900;
}}

.stDownloadButton > button {{
    border-radius: 12px !important;
    background: linear-gradient(135deg, var(--studio-gold), var(--studio-coral)) !important;
    color: #16100a !important;
}}

.tag-pill {{
    background: rgba(106, 169, 255, 0.13) !important;
    border-color: rgba(106, 169, 255, 0.28) !important;
    color: #dce9ff !important;
}}

.thumbnail-card img,
[data-testid="stImage"] img {{
    border-radius: 14px;
}}

@media (max-width: 900px) {{
    .hero {{
        min-height: 520px;
        padding: 28px !important;
        background-position: 58% center !important;
    }}

    .feature-grid,
    .workflow-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }}
}}

@media (max-width: 560px) {{
    .feature-grid,
    .workflow-grid {{
        grid-template-columns: 1fr !important;
    }}
}}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
.stApp {{
    background:
        radial-gradient(circle at 78% -10%, rgba(126, 166, 255, 0.16), transparent 31rem),
        radial-gradient(circle at 16% 11%, rgba(89, 223, 199, 0.10), transparent 27rem),
        linear-gradient(145deg, #060810 0%, #09101d 44%, #0d1422 100%) !important;
}}

.hero {{
    display: block !important;
    min-height: auto !important;
    padding: 0 !important;
    border-radius: 26px !important;
    border: 1px solid rgba(233, 213, 172, 0.16) !important;
    background:
        radial-gradient(circle at 92% 20%, rgba(232, 199, 127, 0.11), transparent 22rem),
        linear-gradient(125deg, rgba(14, 21, 36, 0.97), rgba(15, 25, 44, 0.93)) !important;
    box-shadow: 0 30px 74px rgba(0, 0, 0, 0.34) !important;
}}

.hero-layout {{
    display: grid;
    grid-template-columns: minmax(0, 1fr) 390px;
    gap: 38px;
    align-items: center;
    padding: 52px 50px 38px;
}}

.hero-badge {{
    display: inline-flex !important;
    gap: 8px;
    align-items: center;
    color: #fff0b8 !important;
    background: rgba(232, 199, 127, 0.08) !important;
    border-color: rgba(232, 199, 127, 0.25) !important;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}}

.hero-badge svg {{
    width: 14px;
    height: 14px;
    fill: #fff0b8;
}}

.hero h1 {{
    font-family: "Playfair Display", serif !important;
    font-size: clamp(2.75rem, 4.8vw, 4.35rem) !important;
    font-weight: 600 !important;
    line-height: 1.05 !important;
    background: none !important;
    -webkit-text-fill-color: currentColor !important;
    color: #f7f3ea !important;
}}

.hero h1 em {{
    color: #fff0b8;
    font-style: normal;
}}

.hero p {{
    color: #a8b2c3 !important;
    line-height: 1.72 !important;
}}

.hero-visual {{
    position: relative;
    min-height: 350px;
    display: grid;
    place-items: center;
}}

.preview-orbit {{
    position: absolute;
    width: 330px;
    height: 330px;
    border-radius: 50%;
    border: 1px solid rgba(232, 199, 127, 0.15);
}}

.preview-panel {{
    position: relative;
    width: min(100%, 340px);
    overflow: hidden;
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.13);
    background: rgba(5, 8, 14, 0.74);
    box-shadow: 0 26px 58px rgba(0, 0, 0, 0.42);
}}

.preview-panel img {{
    display: block;
    width: 100%;
    aspect-ratio: 16 / 11;
    object-fit: cover;
    filter: saturate(0.9) contrast(1.05);
}}

.preview-bars {{
    padding: 16px;
}}

.preview-line {{
    height: 9px;
    border-radius: 999px;
    margin: 9px 0;
    background: rgba(255, 255, 255, 0.14);
}}

.preview-line:nth-child(1) {{
    width: 76%;
    background: linear-gradient(90deg, #e8c77f, #59dfc7);
}}

.preview-line:nth-child(2) {{ width: 58%; }}
.preview-line:nth-child(3) {{ width: 88%; }}

.live-chip {{
    position: absolute;
    left: 8px;
    bottom: 24px;
    padding: 9px 13px;
    border-radius: 999px;
    color: #f7f3ea;
    background: rgba(7, 10, 18, 0.84);
    border: 1px solid rgba(233, 213, 172, 0.16);
    font-size: 0.72rem;
    font-weight: 800;
}}

.aur-features {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    padding: 0 50px 42px;
}}

.hero > .feature-grid,
.workflow-grid {{
    display: none !important;
}}

.aurelia-feature {{
    min-height: 142px;
    padding: 18px;
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, 0.13);
    background: rgba(255, 255, 255, 0.027);
}}

.aurelia-icon {{
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    margin-bottom: 14px;
    border-radius: 12px;
    background: rgba(232, 199, 127, 0.10);
}}

.aurelia-icon svg {{
    width: 21px;
    height: 21px;
    fill: #fff0b8;
}}

.aurelia-feature strong {{
    display: block;
    color: #f7f3ea;
    font-size: 0.95rem;
    margin-bottom: 5px;
}}

.aurelia-feature span {{
    display: block;
    color: #a8b2c3;
    font-size: 0.78rem;
    line-height: 1.45;
}}

.input-panel {{
    border: 1px solid rgba(233, 213, 172, 0.16);
    border-radius: 20px;
    padding: 22px 25px 15px;
    margin-bottom: 22px;
    background: rgba(14, 21, 36, 0.78);
}}

.input-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    color: #f7f3ea;
    font-weight: 800;
    margin-bottom: 14px;
}}

.input-title svg {{
    width: 21px;
    height: 21px;
    fill: #e8c77f;
}}

@media (max-width: 1120px) {{
    .hero-layout {{
        grid-template-columns: 1fr;
    }}
    .aur-features {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}

@media (max-width: 620px) {{
    .hero-layout {{
        padding: 32px 24px 28px;
    }}
    .aur-features {{
        grid-template-columns: 1fr;
        padding: 0 24px 28px;
    }}
}}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root {
    --brand-bg: #050b16;
    --brand-panel: rgba(8, 18, 34, 0.84);
    --brand-panel-strong: rgba(10, 24, 45, 0.96);
    --brand-line: rgba(93, 195, 255, 0.18);
    --brand-text: #f7fbff;
    --brand-muted: #a7b8cc;
    --brand-cyan: #21d6ff;
    --brand-blue: #256fff;
    --brand-red: #ff364c;
    --brand-white: #ffffff;
}

.stApp {
    background:
        radial-gradient(circle at 18% 4%, rgba(33, 214, 255, 0.16), transparent 28rem),
        radial-gradient(circle at 86% 12%, rgba(255, 54, 76, 0.09), transparent 24rem),
        linear-gradient(145deg, #030812 0%, #061426 48%, #08101f 100%) !important;
    color: var(--brand-text) !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(4, 10, 20, 0.99), rgba(5, 16, 31, 0.98)) !important;
    border-right: 1px solid var(--brand-line) !important;
}

.aurelia-brand {
    display: block !important;
    padding: 12px 10px 18px;
    margin: 0 0 18px !important;
    border-radius: 20px;
    border: 1px solid rgba(33, 214, 255, 0.16);
    background: linear-gradient(180deg, rgba(9, 26, 48, 0.82), rgba(4, 10, 20, 0.50));
    text-align: center;
}

.aurelia-brand img {
    width: min(100%, 230px);
    display: block;
    margin: 0 auto 12px;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.32), 0 0 32px rgba(33, 214, 255, 0.10);
}

.aurelia-brand strong {
    color: var(--brand-white) !important;
    font-size: 1.16rem !important;
    letter-spacing: 0 !important;
}

.aurelia-brand span,
.side-label {
    color: var(--brand-cyan) !important;
    letter-spacing: 0.13em !important;
}

.sidebar-note {
    background: rgba(33, 214, 255, 0.07) !important;
    border-color: rgba(33, 214, 255, 0.18) !important;
    color: #d4e9f7 !important;
}

.hero {
    border-radius: 24px !important;
    border: 1px solid rgba(93, 195, 255, 0.18) !important;
    background:
        radial-gradient(circle at 84% 20%, rgba(33, 214, 255, 0.13), transparent 24rem),
        radial-gradient(circle at 92% 78%, rgba(255, 54, 76, 0.11), transparent 19rem),
        linear-gradient(135deg, rgba(8, 18, 34, 0.96), rgba(5, 12, 24, 0.94)) !important;
    box-shadow: 0 32px 76px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

.hero::after {
    height: 3px !important;
    left: 50px !important;
    right: 50px !important;
    background: linear-gradient(90deg, transparent, var(--brand-cyan), var(--brand-blue), var(--brand-red), transparent) !important;
}

.hero-layout {
    grid-template-columns: minmax(0, 1.05fr) minmax(330px, 0.95fr) !important;
    gap: 46px !important;
}

.hero-badge {
    color: #c9f7ff !important;
    background: rgba(33, 214, 255, 0.10) !important;
    border-color: rgba(33, 214, 255, 0.30) !important;
}

.hero-badge svg {
    fill: var(--brand-cyan) !important;
}

.hero h1 {
    font-family: "Manrope", sans-serif !important;
    font-weight: 900 !important;
    font-size: clamp(2.65rem, 4.9vw, 4.55rem) !important;
    line-height: 0.98 !important;
    color: var(--brand-white) !important;
}

.hero h1 em {
    color: var(--brand-cyan) !important;
    text-shadow: 0 0 28px rgba(33, 214, 255, 0.20);
}

.hero p {
    color: var(--brand-muted) !important;
    max-width: 680px !important;
}

.hero-chip,
.status-chip {
    background: rgba(33, 214, 255, 0.08) !important;
    border-color: rgba(33, 214, 255, 0.20) !important;
    color: #dcf8ff !important;
}

.preview-orbit {
    width: 390px !important;
    height: 390px !important;
    border-color: rgba(33, 214, 255, 0.22) !important;
    box-shadow: inset 0 0 34px rgba(33, 214, 255, 0.08);
}

.preview-panel {
    width: min(100%, 470px) !important;
    overflow: visible !important;
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

.brand-stage {
    position: relative;
    padding: 22px;
    border-radius: 34px;
    background:
        linear-gradient(145deg, rgba(8, 23, 44, 0.88), rgba(4, 10, 20, 0.62)),
        radial-gradient(circle at 50% 42%, rgba(33, 214, 255, 0.20), transparent 15rem);
    border: 1px solid rgba(93, 195, 255, 0.24);
    box-shadow:
        0 28px 78px rgba(0, 0, 0, 0.55),
        0 0 70px rgba(33, 214, 255, 0.16),
        inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.brand-stage::before,
.brand-stage::after {
    content: "";
    position: absolute;
    border-radius: 999px;
    pointer-events: none;
}

.brand-stage::before {
    inset: -18px;
    border: 1px solid rgba(33, 214, 255, 0.18);
    box-shadow: inset 0 0 38px rgba(33, 214, 255, 0.07);
}

.brand-stage::after {
    width: 120px;
    height: 120px;
    right: -22px;
    top: -24px;
    background: radial-gradient(circle, rgba(255, 54, 76, 0.30), transparent 66%);
    filter: blur(2px);
}

.brand-stage img {
    position: relative;
    z-index: 2;
    display: block;
    width: 100%;
    aspect-ratio: 16 / 10;
    object-fit: cover;
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.10);
    filter: saturate(1.12) contrast(1.05);
}

.float-chip {
    position: absolute;
    z-index: 3;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 13px;
    border-radius: 999px;
    color: #effbff;
    background: rgba(3, 8, 18, 0.82);
    border: 1px solid rgba(33, 214, 255, 0.24);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.26);
    font-size: 0.74rem;
    font-weight: 900;
}

.float-chip.one {
    left: -22px;
    top: 58px;
}

.float-chip.two {
    right: -18px;
    bottom: 64px;
    border-color: rgba(255, 54, 76, 0.28);
}

.float-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--brand-cyan);
    box-shadow: 0 0 18px rgba(33, 214, 255, 0.9);
}

.float-chip.two .float-dot {
    background: var(--brand-red);
    box-shadow: 0 0 18px rgba(255, 54, 76, 0.8);
}

.live-chip {
    left: 50%;
    bottom: -4px;
    transform: translateX(-50%);
    background: linear-gradient(135deg, rgba(33, 214, 255, 0.14), rgba(45, 125, 255, 0.16)) !important;
    border-color: rgba(33, 214, 255, 0.28) !important;
    color: #effbff !important;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.28);
}

.hero-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    max-width: 660px;
    margin-top: 28px;
}

.hero-stat {
    min-height: 92px;
    padding: 16px;
    border-radius: 18px;
    border: 1px solid rgba(93, 195, 255, 0.16);
    background: linear-gradient(145deg, rgba(11, 28, 52, 0.72), rgba(5, 12, 24, 0.54));
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.hero-stat b {
    display: block;
    color: var(--brand-white);
    font-size: 1.35rem;
    line-height: 1;
}

.hero-stat span {
    display: block;
    margin-top: 8px;
    color: var(--brand-muted);
    font-size: 0.76rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.aurelia-feature,
.glass-card,
.thumbnail-card,
.studio-shell,
.concept-card,
.input-panel {
    border-color: rgba(93, 195, 255, 0.17) !important;
    background: linear-gradient(145deg, rgba(9, 23, 43, 0.92), rgba(5, 13, 27, 0.88)) !important;
}

.aurelia-icon {
    background: rgba(33, 214, 255, 0.10) !important;
}

.aurelia-icon svg {
    fill: var(--brand-cyan) !important;
}

.aurelia-feature {
    position: relative;
    overflow: hidden;
    min-height: 158px !important;
    transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.aurelia-feature::after {
    content: "";
    position: absolute;
    inset: auto -20% 0 -20%;
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--brand-cyan), var(--brand-red), transparent);
    opacity: 0.78;
}

.aurelia-feature:hover {
    transform: translateY(-4px);
    border-color: rgba(33, 214, 255, 0.34) !important;
    box-shadow: 0 22px 48px rgba(0, 0, 0, 0.24), 0 0 28px rgba(33, 214, 255, 0.10) !important;
}

.aurelia-feature strong,
.input-title {
    color: var(--brand-white) !important;
}

.input-title svg {
    fill: var(--brand-cyan) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--brand-cyan), #2d7dff) !important;
    color: #03101c !important;
    box-shadow: 0 14px 34px rgba(33, 214, 255, 0.19) !important;
}

.stDownloadButton > button {
    background: rgba(255, 54, 76, 0.12) !important;
    border-color: rgba(255, 54, 76, 0.26) !important;
    color: #ffe8ec !important;
}

.section-title {
    color: var(--brand-white) !important;
}

.tag-pill {
    background: rgba(33, 214, 255, 0.10) !important;
    border-color: rgba(33, 214, 255, 0.22) !important;
    color: #d9f8ff !important;
}

@media (max-width: 1120px) {
    .hero-layout {
        grid-template-columns: 1fr !important;
    }
    .preview-panel {
        max-width: 520px;
    }
}

@media (max-width: 680px) {
    .hero-stats {
        grid-template-columns: 1fr;
    }
    .float-chip {
        position: relative;
        left: auto !important;
        right: auto !important;
        top: auto !important;
        bottom: auto !important;
        margin: 10px 6px 0 0;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root {
    --ref-bg: #060b14;
    --ref-sidebar: #050914;
    --ref-panel: #111827;
    --ref-panel-soft: rgba(17, 24, 39, 0.92);
    --ref-line: rgba(238, 205, 147, 0.16);
    --ref-gold: #f0cd86;
    --ref-gold-soft: #fee6aa;
    --ref-teal: #51e0d1;
    --ref-muted: #9aa8bd;
    --ref-white: #f7f4ed;
}

.stApp {
    background:
        linear-gradient(90deg, #050913 0 27%, #07151a 27% 32%, #0a101d 32% 100%) !important;
    color: var(--ref-white) !important;
}

.block-container {
    max-width: 1360px !important;
    padding-top: 0.9rem !important;
}

section[data-testid="stSidebar"] {
    background: var(--ref-sidebar) !important;
    border-right: 1px solid rgba(238, 205, 147, 0.12) !important;
}

section[data-testid="stSidebar"] > div {
    padding: 2.35rem 1.45rem 1.5rem !important;
}

.aurelia-brand {
    display: block !important;
    padding: 24px 24px 26px !important;
    margin: 0 0 26px !important;
    border: 1px solid rgba(238, 205, 147, 0.13) !important;
    border-radius: 22px !important;
    background:
        radial-gradient(circle at 100% 0%, rgba(81, 224, 209, 0.10), transparent 9rem),
        linear-gradient(145deg, rgba(14, 21, 34, 0.72), rgba(5, 9, 18, 0.42)) !important;
    text-align: left !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.aurelia-brand img {
    display: none !important;
}

.aurelia-mark {
    display: none !important;
}

.aurelia-brand strong {
    display: block;
    max-width: 360px;
    color: var(--ref-white) !important;
    font-size: clamp(1.34rem, 2vw, 1.68rem) !important;
    font-weight: 900 !important;
    line-height: 1.12 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    background: linear-gradient(90deg, #ffffff 0%, #ffe7a8 44%, #bffff6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
}

.aurelia-brand span,
.side-label {
    color: var(--ref-gold) !important;
    font-size: 0.78rem !important;
    font-weight: 900 !important;
    letter-spacing: 0.19em !important;
}

.aurelia-brand span {
    display: block;
    position: relative;
    margin-top: 20px !important;
    max-width: 360px;
    font-size: 0.68rem !important;
    line-height: 1.45 !important;
    color: #d7f8f3 !important;
    letter-spacing: 0.24em !important;
    text-transform: uppercase !important;
    text-shadow: 0 0 18px rgba(81, 224, 209, 0.12);
}

.aurelia-brand span::after {
    content: "";
    display: block;
    width: 140px;
    height: 2px;
    margin-top: 16px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--ref-gold), var(--ref-teal));
}

.side-label {
    margin: 30px 0 14px !important;
}

.sidebar-note {
    border-color: rgba(81, 224, 209, 0.20) !important;
    background: rgba(81, 224, 209, 0.07) !important;
    color: #bfd7d5 !important;
    border-radius: 18px !important;
}

.side-workflow-step {
    display: flex;
    align-items: center;
    gap: 16px;
    margin: 13px 0 18px;
    color: #a9c8ef;
    font-size: 0.94rem;
    line-height: 1.45;
}

.side-workflow-step b {
    width: 36px;
    height: 36px;
    display: grid;
    place-items: center;
    flex: 0 0 36px;
    border-radius: 11px;
    border: 1px solid rgba(240, 205, 134, 0.23);
    color: var(--ref-gold-soft);
    background: rgba(3, 7, 14, 0.30);
    font-size: 0.78rem;
    font-weight: 900;
}

.side-workflow-step span {
    color: #a9c8ef;
}

.connection-pill {
    display: inline-flex;
    align-items: center;
    gap: 9px;
    margin: 4px 0 18px;
    padding: 11px 16px;
    border-radius: 999px;
    border: 1px solid rgba(81, 224, 209, 0.26);
    background:
        linear-gradient(135deg, rgba(81, 224, 209, 0.14), rgba(11, 30, 42, 0.72)),
        radial-gradient(circle at 0% 0%, rgba(81, 224, 209, 0.18), transparent 7rem);
    color: #9ffcf3;
    font-size: 0.78rem;
    font-weight: 900;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035), 0 10px 24px rgba(0, 0, 0, 0.12);
}

.connection-pill::before {
    content: "";
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: var(--ref-teal);
    box-shadow: 0 0 16px rgba(81, 224, 209, 0.65);
}

.field-help {
    margin: 2px 0 15px;
    color: #e5e7eb;
    font-size: 0.86rem;
    line-height: 1.45;
}

.stTextInput input,
.stTextArea textarea,
.stSelectbox > div > div {
    background: #030712 !important;
    border-color: rgba(148, 163, 184, 0.16) !important;
    border-radius: 16px !important;
}

.hero {
    max-width: 1120px;
    margin: 12px auto 26px !important;
    min-height: 570px !important;
    border-radius: 30px !important;
    border: 1px solid rgba(238, 205, 147, 0.14) !important;
    background:
        radial-gradient(circle at 86% 42%, rgba(240, 205, 134, 0.13), transparent 22rem),
        linear-gradient(145deg, rgba(20, 27, 40, 0.97), rgba(13, 20, 34, 0.98)) !important;
    box-shadow: 0 36px 90px rgba(0, 0, 0, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
}

.hero::after {
    display: none !important;
}

.hero-layout {
    grid-template-columns: minmax(0, 1fr) 360px !important;
    gap: 32px !important;
    align-items: center !important;
    padding: 54px 68px 30px !important;
}

.hero-badge {
    color: var(--ref-gold-soft) !important;
    background: transparent !important;
    border: 1px solid rgba(238, 205, 147, 0.18) !important;
    border-radius: 999px !important;
    padding: 10px 16px !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.19em !important;
}

.hero-badge svg {
    fill: var(--ref-gold-soft) !important;
}

.hero h1 {
    max-width: 620px !important;
    margin: 34px 0 24px !important;
    font-family: "Playfair Display", Georgia, serif !important;
    font-size: clamp(2.95rem, 4.25vw, 4.15rem) !important;
    font-weight: 700 !important;
    line-height: 1.08 !important;
    letter-spacing: 0 !important;
    color: var(--ref-white) !important;
}

.hero h1 span {
    display: block;
    white-space: nowrap;
}

.hero h1 em {
    display: inline;
    color: var(--ref-gold-soft) !important;
    text-shadow: none !important;
}

.hero p {
    max-width: 610px !important;
    color: var(--ref-muted) !important;
    font-size: 1.03rem !important;
    line-height: 1.72 !important;
}

.hero-actions {
    display: none !important;
}

.hero-stats {
    display: none !important;
    margin-top: 36px !important;
    max-width: 640px !important;
}

.hero-stat {
    min-height: 78px !important;
    padding: 14px !important;
    border-radius: 18px !important;
    border-color: rgba(238, 205, 147, 0.12) !important;
    background: rgba(8, 13, 24, 0.62) !important;
}

.hero-stat b {
    color: var(--ref-gold-soft) !important;
    font-size: 1.14rem !important;
}

.hero-stat span {
    font-size: 0.68rem !important;
}

.hero-visual {
    min-height: 360px !important;
    overflow: visible;
}

.preview-orbit {
    width: 370px !important;
    height: 370px !important;
    right: -40px;
    border-color: rgba(240, 205, 134, 0.10) !important;
    box-shadow: none !important;
}

.preview-panel {
    width: 390px !important;
    transform: translateX(28px);
}

.brand-stage {
    padding: 8px !important;
    border-radius: 24px !important;
    background: rgba(5, 9, 18, 0.62) !important;
    border: 8px solid rgba(238, 205, 147, 0.30) !important;
    box-shadow: 0 32px 78px rgba(0, 0, 0, 0.45) !important;
}

.brand-stage::before {
    inset: -48px !important;
    border-color: rgba(238, 205, 147, 0.08) !important;
    box-shadow: none !important;
}

.brand-stage::after {
    display: none !important;
}

.brand-stage img {
    aspect-ratio: 16 / 10.6 !important;
    border-radius: 16px !important;
    object-position: center center;
    border: 0 !important;
}

.float-chip {
    display: none !important;
}

.live-chip {
    left: 18px !important;
    bottom: 20px !important;
    transform: none !important;
    border-radius: 999px !important;
    color: var(--ref-white) !important;
    background: rgba(3, 7, 14, 0.86) !important;
    border: 1px solid rgba(238, 205, 147, 0.15) !important;
}

.live-chip::before {
    content: "";
    width: 10px;
    height: 10px;
    display: inline-block;
    margin-right: 9px;
    border-radius: 999px;
    background: var(--ref-teal);
    box-shadow: 0 0 18px rgba(81, 224, 209, 0.8);
}

.aur-features {
    padding: 0 68px 38px !important;
}

.aurelia-feature,
.input-panel,
.glass-card,
.thumbnail-card,
.studio-shell,
.concept-card {
    border-color: rgba(238, 205, 147, 0.13) !important;
    background: linear-gradient(145deg, rgba(14, 21, 34, 0.92), rgba(8, 13, 24, 0.86)) !important;
}

.aurelia-icon {
    background: rgba(240, 205, 134, 0.10) !important;
}

.aurelia-icon svg,
.input-title svg {
    fill: var(--ref-gold-soft) !important;
}

.aurelia-feature::after {
    background: linear-gradient(90deg, transparent, var(--ref-gold), var(--ref-teal), transparent) !important;
}

.stButton > button {
    background: linear-gradient(135deg, var(--ref-gold-soft), var(--ref-gold)) !important;
    color: #07101b !important;
}

.stDownloadButton > button {
    background: rgba(81, 224, 209, 0.08) !important;
    border-color: rgba(81, 224, 209, 0.24) !important;
    color: #d9fffb !important;
}

.tag-pill {
    background: rgba(81, 224, 209, 0.08) !important;
    border-color: rgba(81, 224, 209, 0.20) !important;
    color: #d7fffb !important;
}

@media (max-width: 1120px) {
    .stApp {
        background: linear-gradient(145deg, #050913, #0d1422) !important;
    }
    .hero {
        min-height: auto !important;
    }
    .hero-layout {
        grid-template-columns: 1fr !important;
        padding: 34px 28px 26px !important;
    }
    .hero h1 {
        margin-top: 28px !important;
        font-size: clamp(2.4rem, 7.6vw, 3.8rem) !important;
    }
    .preview-panel {
        transform: none;
        width: min(100%, 390px) !important;
    }
    .aur-features {
        padding: 0 30px 34px !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Final reference hero layout: natural title wrapping, bounded logo card. */
.hero {
    width: min(100%, 1154px) !important;
    max-width: 1154px !important;
    min-height: 560px !important;
    overflow: hidden !important;
}

.hero-layout {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) 340px !important;
    gap: 58px !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 48px 66px 30px !important;
}

.hero-copy {
    width: auto !important;
    max-width: 700px !important;
    min-width: 0 !important;
}

.hero h1 {
    width: auto !important;
    max-width: 700px !important;
    margin: 44px 0 24px !important;
    font-size: clamp(3.15rem, 4.35vw, 4.35rem) !important;
    line-height: 1.04 !important;
}

.hero h1 span {
    display: inline !important;
    white-space: normal !important;
}

.hero p {
    max-width: 670px !important;
}

.hero-visual {
    width: 340px !important;
    min-width: 340px !important;
    justify-self: center !important;
}

.preview-panel {
    width: 340px !important;
    transform: none !important;
}

.brand-stage {
    width: 340px !important;
    box-sizing: border-box !important;
}

@media (max-width: 1350px) {
    .hero {
        width: min(100%, 1040px) !important;
    }

    .hero-layout {
        grid-template-columns: minmax(0, 1fr) 300px !important;
        gap: 48px !important;
        padding: 44px 52px 30px !important;
    }

    .hero-copy,
    .hero h1 {
        width: auto !important;
        max-width: 650px !important;
    }

    .hero h1 {
        font-size: clamp(2.85rem, 3.75vw, 3.75rem) !important;
    }

    .hero-visual,
    .preview-panel,
    .brand-stage {
        width: 300px !important;
        min-width: 0 !important;
    }
}

@media (max-width: 980px) {
    .hero {
        min-height: auto !important;
    }

    .hero-layout {
        grid-template-columns: 1fr !important;
        gap: 34px !important;
        padding: 38px 28px 30px !important;
    }

    .hero-copy,
    .hero h1 {
        width: 100% !important;
        max-width: 100% !important;
    }

    .hero h1 {
        font-size: clamp(2.45rem, 8vw, 3.5rem) !important;
    }

    .hero-visual,
    .preview-panel,
    .brand-stage {
        width: min(100%, 390px) !important;
        justify-self: center !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Reference lower section: feature cards, import panel, URL field, and actions. */
.aur-features {
    display: grid !important;
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    gap: 14px !important;
    padding: 0 74px 44px !important;
}

.aurelia-feature {
    min-height: 92px !important;
    padding: 16px 18px !important;
    border-radius: 16px !important;
    background: rgba(18, 26, 42, 0.72) !important;
    border: 1px solid rgba(148, 163, 184, 0.12) !important;
    box-shadow: none !important;
}

.aurelia-feature::after {
    display: none !important;
}

.aurelia-icon {
    width: 48px !important;
    height: 48px !important;
    display: grid !important;
    place-items: center !important;
    margin-bottom: 14px !important;
    border-radius: 14px !important;
    background: rgba(255, 255, 255, 0.075) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035) !important;
}

.aurelia-icon svg {
    width: 24px !important;
    height: 24px !important;
    fill: var(--ref-gold-soft) !important;
}

.aurelia-feature strong {
    font-size: 0.98rem !important;
    color: #f7f4ed !important;
    margin-bottom: 6px !important;
}

.aurelia-feature span {
    font-size: 0.82rem !important;
    color: #9aa8bd !important;
}

.input-panel {
    width: min(100%, 1154px) !important;
    margin: 40px auto 28px !important;
    padding: 30px 48px !important;
    border-radius: 28px !important;
    background: rgba(8, 13, 24, 0.70) !important;
    border: 1px solid rgba(238, 205, 147, 0.13) !important;
    box-shadow: none !important;
}

.input-title {
    margin: 0 !important;
    font-size: 1.12rem !important;
    font-weight: 900 !important;
    color: #f7f4ed !important;
}

.input-title svg {
    fill: #d8b46e !important;
}

.stTextInput input {
    min-height: 58px !important;
    border-radius: 10px !important;
    background: #050914 !important;
    border: 1px solid rgba(148, 163, 184, 0.10) !important;
    color: #f7f4ed !important;
    font-size: 1rem !important;
}

.stButton > button {
    min-height: 64px !important;
    border-radius: 16px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    background: linear-gradient(135deg, #f2d99f, #d8b46e) !important;
    color: #050914 !important;
    border: 0 !important;
}

.footer-credit {
    width: min(100%, 1154px);
    margin: 46px auto 22px;
    padding: 18px 20px;
    color: #9aa8bd;
    text-align: center;
    font-size: 0.9rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
}

@media (max-width: 1050px) {
    .aur-features {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        padding: 0 28px 34px !important;
    }

    .input-panel {
        padding: 24px !important;
        margin-top: 28px !important;
    }
}

@media (max-width: 620px) {
    .aur-features {
        grid-template-columns: 1fr !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ANIMATION ENHANCEMENT START - remove this block to undo premium motion */
.hero {
    position: relative !important;
}

.hero::before {
    content: "";
    position: absolute;
    inset: 1px;
    border-radius: 30px;
    pointer-events: none;
    background:
        linear-gradient(120deg, transparent 0%, rgba(240, 205, 134, 0.10) 28%, rgba(81, 224, 209, 0.12) 42%, transparent 58%);
    opacity: 0.65;
    transform: translateX(-42%);
    animation: hero-sheen 9s ease-in-out infinite;
}

.hero-badge {
    position: relative;
    overflow: hidden;
}

.hero-badge::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 0%, rgba(255, 255, 255, 0.16) 45%, transparent 62%);
    transform: translateX(-120%);
    animation: badge-sweep 5.8s ease-in-out infinite;
}

.preview-orbit {
    animation: orbit-breathe 7s ease-in-out infinite;
}

.brand-stage {
    animation: logo-float 6.5s ease-in-out infinite;
}

.brand-stage::before {
    animation: orbit-turn 18s linear infinite;
}

.brand-stage img {
    animation: logo-glow 5.5s ease-in-out infinite;
}

.live-chip::before {
    animation: live-pulse 1.9s ease-out infinite;
}

.aurelia-feature {
    transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease, background 180ms ease !important;
}

.aurelia-feature:hover {
    transform: translateY(-5px);
    border-color: rgba(240, 205, 134, 0.28) !important;
    background: linear-gradient(145deg, rgba(18, 26, 42, 0.88), rgba(10, 16, 28, 0.92)) !important;
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22), 0 0 26px rgba(81, 224, 209, 0.06) !important;
}

.stButton > button {
    transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px);
    filter: saturate(1.04);
    box-shadow: 0 18px 38px rgba(216, 180, 110, 0.18) !important;
}

@keyframes hero-sheen {
    0%, 44% { transform: translateX(-55%); opacity: 0; }
    56% { opacity: 0.72; }
    100% { transform: translateX(55%); opacity: 0; }
}

@keyframes badge-sweep {
    0%, 52% { transform: translateX(-130%); }
    76%, 100% { transform: translateX(130%); }
}

@keyframes orbit-breathe {
    0%, 100% { transform: scale(0.98); opacity: 0.48; }
    50% { transform: scale(1.04); opacity: 0.78; }
}

@keyframes orbit-turn {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes logo-float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}

@keyframes logo-glow {
    0%, 100% { filter: saturate(1.03) contrast(1.03) drop-shadow(0 0 0 rgba(81, 224, 209, 0)); }
    50% { filter: saturate(1.12) contrast(1.04) drop-shadow(0 0 18px rgba(81, 224, 209, 0.16)); }
}

@keyframes live-pulse {
    0% { box-shadow: 0 0 0 0 rgba(81, 224, 209, 0.62); }
    75%, 100% { box-shadow: 0 0 0 12px rgba(81, 224, 209, 0); }
}

@media (prefers-reduced-motion: reduce) {
    .hero::before,
    .hero-badge::after,
    .preview-orbit,
    .brand-stage,
    .brand-stage::before,
    .brand-stage img,
    .live-chip::before {
        animation: none !important;
    }
}
/* ANIMATION ENHANCEMENT END */
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* PRESENTATION GLANCE START - extra premium polish, removable as one block */
.stApp::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 30% 12%, rgba(81, 224, 209, 0.08), transparent 22rem),
        radial-gradient(circle at 78% 34%, rgba(240, 205, 134, 0.08), transparent 24rem);
    animation: ambient-shift 16s ease-in-out infinite alternate;
}

.block-container,
section[data-testid="stSidebar"] {
    position: relative;
    z-index: 1;
}

section[data-testid="stSidebar"] {
    box-shadow: inset -1px 0 0 rgba(240, 205, 134, 0.08), 18px 0 54px rgba(0, 0, 0, 0.20);
}

.aurelia-brand {
    position: relative;
    overflow: hidden;
}

.aurelia-brand::before {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.08) 46%, transparent 62%);
    transform: translateX(-120%);
    animation: brand-sweep 7.5s ease-in-out infinite;
}

.aurelia-brand span::after {
    animation: underline-glow 3.8s ease-in-out infinite;
}

.connection-pill {
    animation: pill-breathe 4.8s ease-in-out infinite;
}

.side-workflow-step b {
    transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.side-workflow-step:hover b {
    transform: translateY(-1px);
    border-color: rgba(240, 205, 134, 0.42);
    box-shadow: 0 0 20px rgba(240, 205, 134, 0.08);
}

.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: rgba(240, 205, 134, 0.72) !important;
    box-shadow: 0 0 0 1px rgba(240, 205, 134, 0.20), 0 0 26px rgba(240, 205, 134, 0.08) !important;
}

.stSelectbox > div > div:hover {
    border-color: rgba(81, 224, 209, 0.30) !important;
}

.input-panel {
    position: relative;
    overflow: hidden;
}

.input-panel::after {
    content: "";
    position: absolute;
    left: 42px;
    right: 42px;
    bottom: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(240, 205, 134, 0.62), rgba(81, 224, 209, 0.54), transparent);
    animation: line-breathe 4.5s ease-in-out infinite;
}

.footer-credit {
    animation: footer-glow 5.5s ease-in-out infinite;
}

@keyframes ambient-shift {
    from { opacity: 0.52; transform: translate3d(-1.2%, -0.8%, 0) scale(1); }
    to { opacity: 0.88; transform: translate3d(1.2%, 0.8%, 0) scale(1.03); }
}

@keyframes brand-sweep {
    0%, 56% { transform: translateX(-130%); }
    78%, 100% { transform: translateX(130%); }
}

@keyframes underline-glow {
    0%, 100% { opacity: 0.72; box-shadow: 0 0 0 rgba(81, 224, 209, 0); }
    50% { opacity: 1; box-shadow: 0 0 18px rgba(81, 224, 209, 0.26); }
}

@keyframes pill-breathe {
    0%, 100% { box-shadow: 0 0 0 rgba(81, 224, 209, 0); }
    50% { box-shadow: 0 0 26px rgba(81, 224, 209, 0.08); }
}

@keyframes line-breathe {
    0%, 100% { opacity: 0.35; }
    50% { opacity: 0.9; }
}

@keyframes footer-glow {
    0%, 100% { color: #9aa8bd; text-shadow: none; }
    50% { color: #c1ccdb; text-shadow: 0 0 18px rgba(81, 224, 209, 0.10); }
}

@media (prefers-reduced-motion: reduce) {
    .stApp::before,
    .aurelia-brand::before,
    .aurelia-brand span::after,
    .connection-pill,
    .input-panel::after,
    .footer-credit {
        animation: none !important;
    }
}
/* PRESENTATION GLANCE END */
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* SIDEBAR BRAND MOTION START - remove this block to undo sidebar/app-name animation */
section[data-testid="stSidebar"]::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
        radial-gradient(circle at 18% 10%, rgba(240, 205, 134, 0.08), transparent 9rem),
        radial-gradient(circle at 82% 34%, rgba(81, 224, 209, 0.07), transparent 11rem);
    animation: sidebar-ambient 12s ease-in-out infinite alternate;
}

.aurelia-brand {
    isolation: isolate;
    position: relative;
    overflow: hidden;
    padding: 22px 22px 24px !important;
    transform-style: preserve-3d;
    background:
        linear-gradient(115deg, rgba(255, 255, 255, 0.055), transparent 24%),
        radial-gradient(circle at 90% 12%, rgba(81, 224, 209, 0.22), transparent 7.2rem),
        radial-gradient(circle at 0% 100%, rgba(240, 205, 134, 0.15), transparent 8.8rem),
        linear-gradient(145deg, rgba(13, 22, 36, 0.94), rgba(3, 8, 17, 0.72)) !important;
    animation: brand-rise 700ms ease-out both, brand-breathe 5.5s ease-in-out 900ms infinite;
}

.aurelia-brand::after {
    content: "";
    position: absolute;
    inset: -1px;
    z-index: -1;
    border-radius: 22px;
    padding: 1px;
    background: linear-gradient(135deg, rgba(240, 205, 134, 0.40), rgba(81, 224, 209, 0.22), rgba(240, 205, 134, 0.10));
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0.78;
    animation: brand-border-glow 4.6s ease-in-out infinite;
}

.aurelia-brand strong {
    position: relative;
    z-index: 1;
    display: block;
    font-family: "Trebuchet MS", "Segoe UI", sans-serif !important;
    font-size: clamp(1.48rem, 2.25vw, 1.86rem) !important;
    font-weight: 900 !important;
    line-height: 1.15 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: transparent !important;
    background: linear-gradient(115deg, #ffffff 0%, #ffe7a8 28%, #e9ffca 52%, #7cf6ea 78%, #ffffff 100%);
    background-size: 240% auto;
    -webkit-background-clip: text;
    background-clip: text;
    text-shadow: 0 0 28px rgba(81, 224, 209, 0.12);
    animation: wordmark-gradient 5.8s ease-in-out infinite;
}

.aurelia-brand strong::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(105deg, transparent 0%, rgba(255, 255, 255, 0.42) 42%, transparent 58%);
    mix-blend-mode: screen;
    transform: translateX(-130%);
    animation: wordmark-shine 6.2s ease-in-out infinite;
}

.aurelia-brand span {
    position: relative;
    z-index: 1;
    display: block;
    margin-top: 22px !important;
    font-family: "Segoe UI", sans-serif !important;
    font-size: 0.72rem !important;
    font-weight: 900 !important;
    line-height: 1.65 !important;
    letter-spacing: 0.30em !important;
    color: #d9fffb !important;
    text-shadow: 0 0 18px rgba(81, 224, 209, 0.18);
    animation: subtitle-focus 4.2s ease-in-out infinite;
}

.aurelia-brand span::after {
    width: 74% !important;
    height: 3px !important;
    margin-top: 18px !important;
    background: linear-gradient(90deg, #f0cd86, #dff8bd, #51e0d1, #f0cd86) !important;
    background-size: 220% auto !important;
    box-shadow: 0 0 20px rgba(81, 224, 209, 0.20);
    animation: underline-flow 3.6s ease-in-out infinite, underline-glow 3.8s ease-in-out infinite !important;
}

.brand-topline {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 18px;
}

.brand-orb {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    border-radius: 14px;
    color: #07101b;
    font-family: "Segoe UI", sans-serif;
    font-size: 0.88rem;
    font-weight: 950;
    letter-spacing: 0.04em;
    background: linear-gradient(135deg, #f4d88e, #dbf8c4 48%, #58e5d9);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.24), 0 0 22px rgba(81, 224, 209, 0.16);
    animation: orb-pulse 4.8s ease-in-out infinite;
}

.brand-eyebrow {
    color: #b9fff8;
    font-family: "Segoe UI", sans-serif;
    font-size: 0.63rem;
    font-weight: 900;
    letter-spacing: 0.18em;
    line-height: 1.35;
    text-transform: uppercase;
}

.brand-wordmark {
    position: relative;
    z-index: 1;
    font-family: "Segoe UI Black", "Arial Black", "Segoe UI", sans-serif;
    font-size: clamp(1.45rem, 2.2vw, 1.82rem);
    font-weight: 950;
    line-height: 1.02;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

.brand-wordmark div {
    width: fit-content;
    color: transparent;
    background: linear-gradient(105deg, #ffffff 0%, #ffe3a1 35%, #eefcc8 55%, #75f4ea 82%, #ffffff 100%);
    background-size: 240% auto;
    -webkit-background-clip: text;
    background-clip: text;
    text-shadow: 0 16px 34px rgba(0, 0, 0, 0.28);
    animation: wordmark-gradient 5.8s ease-in-out infinite;
}

.brand-wordmark div:nth-child(2) {
    animation-delay: -1.6s;
}

.brand-subtitle {
    position: relative;
    z-index: 1;
    margin-top: 16px;
    color: #d7fffb;
    font-family: "Segoe UI", sans-serif;
    font-size: 0.76rem;
    font-weight: 900;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    text-shadow: 0 0 18px rgba(81, 224, 209, 0.16);
}

.brand-signal {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: 1.5fr 0.8fr 1fr;
    gap: 7px;
    width: 76%;
    margin-top: 20px;
}

.brand-signal i {
    height: 3px;
    border-radius: 999px;
    background: linear-gradient(90deg, #f0cd86, #dff8bd, #51e0d1);
    box-shadow: 0 0 16px rgba(81, 224, 209, 0.18);
    animation: signal-run 2.8s ease-in-out infinite;
}

.brand-signal i:nth-child(2) {
    animation-delay: 180ms;
}

.brand-signal i:nth-child(3) {
    animation-delay: 360ms;
}

.aurelia-brand .brand-name {
    position: relative;
    z-index: 1;
    display: block;
    max-width: 100%;
    font-family: "Manrope", "Inter", "Segoe UI", sans-serif !important;
    font-size: clamp(1.12rem, 1.48vw, 1.30rem) !important;
    font-weight: 900 !important;
    line-height: 1.18 !important;
    letter-spacing: 0.025em !important;
    text-transform: none !important;
    text-shadow: 0 16px 34px rgba(0, 0, 0, 0.26);
}

.aurelia-brand .brand-name span {
    display: block !important;
    margin: 0 !important;
    color: transparent !important;
    font: inherit !important;
    letter-spacing: inherit !important;
    line-height: inherit !important;
    text-shadow: inherit !important;
    background: linear-gradient(105deg, #ffffff 0%, #ffe2a2 40%, #f0fbc7 61%, #80f1e7 100%);
    background-size: 220% auto;
    -webkit-background-clip: text;
    background-clip: text;
    white-space: nowrap !important;
    animation: wordmark-gradient 6s ease-in-out infinite !important;
}

.aurelia-brand .brand-name span:nth-child(2) {
    animation-delay: -1.4s !important;
}

.aurelia-brand .brand-name span:nth-child(3) {
    animation-delay: -2.2s !important;
}

.aurelia-brand .brand-name span:nth-child(4) {
    animation-delay: -3s !important;
}

.aurelia-brand .brand-name span::after {
    content: none !important;
    display: none !important;
}

.aurelia-brand .brand-tagline {
    display: none !important;
}

.aurelia-brand .brand-tagline::after {
    content: "";
    display: block;
    width: 68% !important;
    height: 3px !important;
    margin-top: 18px !important;
    border-radius: 999px;
    background: linear-gradient(90deg, #f0cd86, #dff8bd, #51e0d1, #f0cd86) !important;
    background-size: 220% auto !important;
    box-shadow: 0 0 20px rgba(81, 224, 209, 0.20);
    animation: underline-flow 3.6s ease-in-out infinite, underline-glow 3.8s ease-in-out infinite !important;
}

@keyframes sidebar-ambient {
    from { opacity: 0.45; transform: translateY(-8px); }
    to { opacity: 0.88; transform: translateY(10px); }
}

@keyframes brand-rise {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes brand-breathe {
    0%, 100% { box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 18px 46px rgba(0, 0, 0, 0.18), 0 0 0 rgba(81, 224, 209, 0); }
    50% { box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07), 0 20px 54px rgba(0, 0, 0, 0.26), 0 0 34px rgba(81, 224, 209, 0.11); }
}

@keyframes brand-border-glow {
    0%, 100% { opacity: 0.54; filter: saturate(0.95) hue-rotate(0deg); }
    50% { opacity: 1; filter: saturate(1.35) hue-rotate(12deg); }
}

@keyframes wordmark-gradient {
    0%, 100% { background-position: 0% center; filter: drop-shadow(0 0 0 rgba(81, 224, 209, 0)); }
    50% { background-position: 100% center; filter: drop-shadow(0 0 10px rgba(81, 224, 209, 0.12)); }
}

@keyframes orb-pulse {
    0%, 100% { transform: translateY(0) scale(1); filter: saturate(1); }
    50% { transform: translateY(-1px) scale(1.035); filter: saturate(1.18); }
}

@keyframes signal-run {
    0%, 100% { opacity: 0.42; transform: scaleX(0.72); transform-origin: left center; }
    50% { opacity: 1; transform: scaleX(1); transform-origin: left center; }
}

@keyframes wordmark-shine {
    0%, 54% { transform: translateX(-135%); opacity: 0; }
    66% { opacity: 0.48; }
    82%, 100% { transform: translateX(135%); opacity: 0; }
}

@keyframes subtitle-focus {
    0%, 100% { color: #d7f8f3; }
    50% { color: #fff0c2; }
}

@keyframes underline-flow {
    0%, 100% { background-position: 0% center; transform: scaleX(0.86); transform-origin: left center; }
    50% { background-position: 100% center; transform: scaleX(1); transform-origin: left center; }
}

@media (prefers-reduced-motion: reduce) {
    section[data-testid="stSidebar"]::before,
    .aurelia-brand,
    .aurelia-brand::after,
    .aurelia-brand strong::after,
    .aurelia-brand strong,
    .aurelia-brand span::after,
    .aurelia-brand span,
    .brand-orb,
    .brand-wordmark div,
    .brand-name,
    .brand-tagline,
    .brand-tagline::after,
    .brand-signal i {
        animation: none !important;
    }
}
/* SIDEBAR BRAND MOTION END */
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    configured_groq_key = bool(os.environ.get("GROQ_API_KEY"))
    configured_hf_token = bool(os.environ.get("HF_TOKEN"))
    configured_youtube_key = bool(os.environ.get("YOUTUBE_API_KEY"))

    st.markdown(
        f"""
        <div class="aurelia-brand">
            <strong class="brand-name">
                <span>Multi Model AI</span>
                <span>SEO System</span>
                <span>for Automated</span>
                <span>Video SEO</span>
            </strong>
            <div class="brand-signal"><i></i><i></i><i></i></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="side-label">Workspace Access</div>', unsafe_allow_html=True)
    if configured_groq_key:
        st.markdown('<div class="connection-pill">SEO Key Configured</div>', unsafe_allow_html=True)

    groq_api_key = st.text_input(
        "Groq API Key",
        type="password",
        key="groq_key",
        placeholder="Configured securely" if configured_groq_key else "Required for SEO analysis",
        help="Optional when GROQ_API_KEY is configured as a Hugging Face Space secret.",
    )
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key

    hf_token = st.text_input(
        "Hugging Face Token",
        type="password",
        key="hf_token",
        placeholder="Required for image generation",
        help="Free Hugging Face token used only when you generate fresh HD thumbnail artwork.",
    )
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token

    if configured_youtube_key:
        st.markdown('<div class="connection-pill">YouTube Key Configured</div>', unsafe_allow_html=True)

    st.markdown('<div class="side-label">Output Setup</div>', unsafe_allow_html=True)
    selected_language = st.selectbox("Output Language", ["English"], index=0)

    model_option = st.selectbox(
        "AI Engine",
        ["Groq + LangChain Agent"],
        index=0,
    )

    st.markdown(
        """
        <div class="side-label">Workflow</div>
        <div class="side-workflow-step"><b>01</b><span>Connect your analysis credentials.</span></div>
        <div class="side-workflow-step"><b>02</b><span>Import a public YouTube video.</span></div>
        <div class="side-workflow-step"><b>03</b><span>Generate strategy and premium artwork.</span></div>
        <div class="sidebar-note">Hosted deployments can securely provide credentials through Space Secrets. Manually entered keys remain in this app session only.</div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(f"""
<div class="hero">
    <div class="hero-layout">
        <div class="hero-copy">
            <div class="hero-badge">{icon_svg("spark")} AI CREATIVE INTELLIGENCE</div>
            <h1>Shape Every Video Into A <em>Search-Worthy Story.</em></h1>
            <p>A premium workspace for metadata strategy, high-intent titles, chapter architecture, and cinematic thumbnail direction grounded in your content.</p>
            <div class="hero-actions">
                <span class="hero-chip">Content intelligence</span>
                <span class="hero-chip">Thumbnail studio</span>
                <span class="hero-chip">Publish-ready exports</span>
            </div>
            <div class="hero-stats">
                <div class="hero-stat"><b>35+</b><span>SEO Tags</span></div>
                <div class="hero-stat"><b>4</b><span>Thumbnail Directions</span></div>
                <div class="hero-stat"><b>1 URL</b><span>Full Strategy</span></div>
            </div>
        </div>
        <div class="hero-visual">
            <div class="preview-orbit"></div>
            <div class="preview-panel">
                <div class="brand-stage">
                    <span class="float-chip one"><span class="float-dot"></span> SEO SCORE READY</span>
                    <img src="{hero_image_uri}" alt="SEO Agent logo preview">
                    <span class="float-chip two"><span class="float-dot"></span> RANK SIGNALS</span>
                </div>
            </div>
            <div class="live-chip">LIVE CREATIVE ENGINE</div>
        </div>
    </div>
    <div class="aur-features">
        {feature_card("search", "Discovery", "Search intent mapping")}
        {feature_card("tag", "Metadata", "Tags and descriptions")}
        {feature_card("chart", "Strategy", "Titles and structure")}
        {feature_card("image", "Studio", "HD artwork exports")}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="workflow-grid">
    <div class="workflow-card">
        <div class="workflow-step">1</div>
        <strong>Connect</strong>
        <p>Add your API keys once from the sidebar.</p>
    </div>
    <div class="workflow-card">
        <div class="workflow-step">2</div>
        <strong>Analyze</strong>
        <p>Extract title, creator, duration, and current thumbnail.</p>
    </div>
    <div class="workflow-card">
        <div class="workflow-step">3</div>
        <strong>Generate</strong>
        <p>Create metadata, titles, tags, and timestamps.</p>
    </div>
    <div class="workflow-card">
        <div class="workflow-step">4</div>
        <strong>Export</strong>
        <p>Download presentation-ready HD thumbnail options.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="input-panel">
        <div class="input-title">{icon_svg("play")} Import a YouTube Video for Analysis</div>
    """,
    unsafe_allow_html=True,
)

video_url = st.text_input(
    label="YouTube Video URL",
    placeholder="Paste a public YouTube URL here",
    label_visibility="collapsed"
)
st.markdown("</div>", unsafe_allow_html=True)

import_col, retry_col = st.columns([4.2, 1], gap="large")
with import_col:
    import_video_clicked = st.button("Import Video Details", type="primary", use_container_width=True)
with retry_col:
    retry_stats_clicked = st.button("Retry Stats", use_container_width=True)

if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "video_metadata" not in st.session_state:
    st.session_state.video_metadata = None
if "generated_thumbnails" not in st.session_state:
    st.session_state.generated_thumbnails = []

if video_url:
    try:
        with st.spinner("Fetching video information..."):
            metadata = get_video_metadata(video_url)
            st.session_state.video_metadata = metadata

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("🎬 Video Details")
            st.write(f"**Title:** {metadata.get('title', 'N/A')}")
            st.write(f"**Creator:** {metadata.get('author', 'N/A')}")
            st.write(f"**Platform:** {metadata.get('platform', 'YouTube')}")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            duration = metadata.get("duration", 0)
            views = metadata.get("views")
            st.metric("Duration", format_duration(duration) if duration else "N/A")
            st.metric("Views", format_views(views) if views is not None else "N/A")
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            if metadata.get("thumbnail_url"):
                st.image(metadata.get("thumbnail_url"), caption="Current Thumbnail", use_container_width=True)

        st.info(f"Analysis will be performed in **{selected_language}** using **{model_option}**")

        if st.button("🚀 Generate SEO Recommendations"):
            if model_option == "OpenAI GPT-3.5-turbo":
                st.error("OpenAI option needs paid OpenAI API billing. For free usage, select Groq + LangChain Agent.")
            else:
                if not os.environ.get("GROQ_API_KEY"):
                    st.warning("Groq API key is missing, so SEO will be generated from video metadata fallback.")
                with st.spinner("Generating professional SEO recommendations..."):
                    try:
                        results = run_seo_analysis_with_langchain(
                            video_url,
                            st.session_state.video_metadata,
                            language=selected_language
                        )
                        st.session_state.analysis_results = results
                        st.session_state.analysis_complete = True
                        st.session_state.generated_thumbnails = []
                        st.success("Analysis complete!")
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")

    except Exception as e:
        st.error(f"Error processing video URL: {str(e)}")

if st.session_state.analysis_complete and st.session_state.analysis_results:
    results = st.session_state.analysis_results
    metadata = st.session_state.video_metadata

    tabs = st.tabs([
        "📊 Analysis",
        "🏷️ Tags",
        "📝 Description",
        "⏱️ Timestamps",
        "🔥 Titles",
        "🎨 Thumbnail Studio"
    ])

    with tabs[0]:
        st.markdown('<h2 class="section-title">Content Analysis</h2>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.write(results.get("analysis", "No analysis available."))
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<h2 class="section-title">35+ Recommended Tags</h2>', unsafe_allow_html=True)
        tags = results.get("seo", {}).get("tags", [])
        for tag in tags:
            st.markdown(f'<span class="tag-pill">#{tag}</span>', unsafe_allow_html=True)

        if st.button("Copy All Tags"):
            st.code(" ".join([f"#{tag}" for tag in tags]))

    with tabs[2]:
        st.markdown('<h2 class="section-title">SEO Optimized Description</h2>', unsafe_allow_html=True)
        description = results.get("seo", {}).get("description", "")
        st.text_area("Copy this description", description, height=330)

        c1, c2 = st.columns(2)
        c1.metric("Words", len(description.split()))
        c2.metric("Characters", len(description))

    with tabs[3]:
        st.markdown('<h2 class="section-title">Smart Video Timestamps</h2>', unsafe_allow_html=True)
        timestamps = results.get("seo", {}).get("timestamps", [])
        timestamp_text = ""

        for ts in timestamps:
            st.markdown(
                f'<div class="timestamp-card"><b>{ts.get("time", "00:00")}</b> — {ts.get("description", "")}</div>',
                unsafe_allow_html=True
            )
            timestamp_text += f'{ts.get("time", "00:00")} - {ts.get("description", "")}\n'

        if st.button("Copy All Timestamps"):
            st.code(timestamp_text)

    with tabs[4]:
        st.markdown('<h2 class="section-title">Unique SEO Title Suggestions</h2>', unsafe_allow_html=True)
        titles = results.get("seo", {}).get("titles", [])

        for title in titles:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(f"### #{title.get('rank', '')} {title.get('title', '')}")
            st.write(f"**Reason:** {title.get('reason', '')}")
            st.markdown('</div>', unsafe_allow_html=True)
            st.write("")

    with tabs[5]:
        st.markdown('<h2 class="section-title">Professional Thumbnail Studio</h2>', unsafe_allow_html=True)
        seo_thumbnail_brief = build_seo_thumbnail_brief(metadata, results)

        custom_text = st.text_input(
            "Shared Headline Override",
            value="",
            placeholder="Leave blank to use a relevant headline for each concept",
        )

        st.info("Each HD thumbnail now uses its own topic-based headline. Add a shared override only when you want the same words on all options.")

        thumbnail_concepts = results.get("thumbnails", [])

        if not thumbnail_concepts or len(thumbnail_concepts) < 4:
            thumbnail_concepts = [
                {"concept": "Topic-specific hero subject grounded in the video title", "text_overlay": metadata.get("title", "Watch This")[:28]},
                {"concept": "Real story scene grounded in the video description", "text_overlay": "Key Moment"},
                {"concept": "Relevant prop or subject detail for the video type", "text_overlay": "What Changed"},
                {"concept": "Action or reaction frame that matches the video topic", "text_overlay": "Watch Closely"},
            ]

        st.markdown(
            """
            <div class="studio-shell">
                <div class="studio-kicker">Fresh image generation</div>
                <h3>Create new HD artwork for the thumbnail.</h3>
                <p>The generated image uses the same analysis, SEO description, title angles, tags, and video themes created above.</p>
            </div>
            <span class="status-chip">1280 x 720 export</span>
            <span class="status-chip">New generated scene</span>
            <span class="status-chip">SEO brief grounded</span>
            """,
            unsafe_allow_html=True,
        )

        add_overlay = st.toggle("Add relevant headline text to HD images", value=True)
        concept_cols = st.columns(2)
        for i, concept in enumerate(thumbnail_concepts[:4]):
            with concept_cols[i % 2]:
                st.markdown(
                    f"""
                    <div class="concept-card">
                        <div class="concept-label">Concept {i + 1}</div>
                        <strong>{concept.get("text_overlay", "Thumbnail direction")}</strong>
                        <p>{concept.get("concept", "Professional visual direction for this video.")}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if st.button("Generate Fresh HD Thumbnails", type="primary", use_container_width=True):
            hf_token = os.environ.get("HF_TOKEN")
            if not hf_token:
                st.error("Add a free Hugging Face token in the sidebar to generate fresh HD artwork.")
            else:
                generated = []
                progress = st.progress(0, text="Preparing HD thumbnail generation...")
                for i, concept in enumerate(thumbnail_concepts[:4]):
                    progress.progress(i / 4, text=f"Generating HD thumbnail {i + 1} of 4...")
                    try:
                        overlay_text = get_relevant_overlay_text(
                            concept,
                            metadata.get("title", "Video"),
                            custom_text,
                        )
                        image = generate_hd_thumbnail(
                            concept,
                            metadata.get("title", "Video"),
                            overlay_text=overlay_text if add_overlay else "",
                            platform=metadata.get("platform", "YouTube"),
                            variant=i,
                            api_key=hf_token,
                            video_context=seo_thumbnail_brief,
                        )
                        generated.append(
                            {
                                "bytes": image_to_png_bytes(image),
                                "concept": concept,
                                "option": i + 1,
                            }
                        )
                    except Exception as e:
                        st.error(f"Thumbnail {i + 1} could not be generated: {e}")

                progress.progress(1.0, text="HD generation finished.")
                st.session_state.generated_thumbnails = generated
                if generated:
                    st.success(f"Generated {len(generated)} fresh HD thumbnail image(s).")

        if st.session_state.generated_thumbnails:
            for item in st.session_state.generated_thumbnails:
                option = item["option"]
                st.markdown('<div class="thumbnail-card">', unsafe_allow_html=True)
                st.markdown(f"### HD Thumbnail Option {option}")
                st.image(
                    item["bytes"],
                    caption=item["concept"].get("concept", f"Generated option {option}"),
                    use_container_width=True,
                )
                st.download_button(
                    label=f"Download HD Thumbnail Option {option}",
                    data=item["bytes"],
                    file_name=f"hd_thumbnail_option_{option}.png",
                    mime="image/png",
                    key=f"download_hd_thumb_{option}",
                )
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Generate the HD gallery above to turn these varied concepts into fresh realistic thumbnail artwork.")

        for i, concept in enumerate([]):
            concept["text_overlay"] = custom_text

            st.markdown('<div class="thumbnail-card">', unsafe_allow_html=True)
            st.markdown(f"### Fallback Mockup {i + 1}")

            preview = create_thumbnail_preview(
                concept,
                metadata.get("title", ""),
                metadata.get("thumbnail_url"),
                variant=i
            )

            buf = BytesIO()
            preview.save(buf, format="PNG")

            st.image(
                buf.getvalue(),
                caption=f"Viral YouTube Style — Option {i + 1}",
                use_container_width=True
            )

            st.download_button(
                label=f"Download Thumbnail Option {i + 1}",
                data=buf.getvalue(),
                file_name=f"thumbnail_option_{i + 1}.png",
                mime="image/png",
                key=f"download_thumb_{i}"
            )

            st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("How to Use This Tool"):
        st.write("""
        1. Add your Groq API key in the sidebar.
        2. Paste a YouTube video URL.
        3. Select Groq + LangChain Agent for free usage.
        4. Click Generate SEO Recommendations.
        5. Use tags, titles, description, timestamps and thumbnails.
        """)

st.markdown(
    '<div class="footer-credit">A PROJECT DEVELOPED BY SYED SHAHEER AND ASNA MARRIUM</div>',
    unsafe_allow_html=True,
)
