import os
import sys
import time
import textwrap
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import streamlit as st
import joblib
import pandas as pd
import numpy as np
import plotly.express as px
import sklearn
from dotenv import load_dotenv

from streamlit_searchbox import st_searchbox
from streamlit_js_eval import get_geolocation

# Local modules
from utils import (
    recommend_fertilizer,
    get_crop_profit_data,
    get_breakeven_yield,
    append_prediction_history,
    load_history,
    load_user_history,
    clear_user_history,
)
import config
import weather_service
import soil_analysis
import market_service
import risk_engine
import report_generator

from weather_service import (
    get_coordinates,
    get_current_weather,
    get_weather_forecast,
    get_seasonal_climate_average,
    search_locations,
    reverse_geocode,
)
from soil_analysis import analyze_soil, INDIAN_SOIL_TYPES
from market_service import get_market_price_for_crop, MarketDataStatus, cached_get_bulk_market_prices
from risk_engine import compute_risk
from report_generator import build_report, build_pdf_report, build_whatsapp_share_url
from auth_db import register_user, verify_user, init_db
from config import (
    MODEL_PATH,
    WEATHER_CACHE_TTL,
    FORECAST_CACHE_TTL,
    WEATHER_FALLBACK_ALLOWED,
    IRRIGATION_EFFECTIVE_RAINFALL_MM,
    DECISION_WEIGHTS,
    get_normalized_weights,
    REFERENCE_RANGE_CROPS,
    REFERENCE_RANGE_DISCLAIMER,
    CROP_MIN_WATER_REQUIREMENTS,
    get_crop_min_water_requirement,
    CROP_GEOGRAPHIC_RESTRICTIONS,
    check_crop_geographic_eligibility,
)

# Initialize SQLite Users Database
init_db()

# Page Configuration
st.set_page_config(
    page_title="Smart Agriculture Decision Support System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html(html_str: str):
    """Render HTML safely without Markdown line-indentation bugs."""
    if not html_str:
        return
    # Strip leading whitespace from EVERY line so Markdown never treats 4+ spaces as a code block
    clean_lines = [line.lstrip() for line in html_str.strip().splitlines()]
    clean_html = "\n".join(clean_lines)
    st.markdown(clean_html, unsafe_allow_html=True)


def inject_custom_css():
    """Inject lightweight custom CSS animations and visual polish for a modern AI agriculture dashboard."""
    # Register fallback PWA service worker
    render_html("""
        <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('./service-worker.js').catch(function(err) {
                console.log('[PWA Fallback] Registration:', err);
            });
        }
        </script>
    """)
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Global Typography */
    html, body, [data-testid="stAppViewContainer"], .stMarkdown {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 1. ELEGANT DARK NAVY-EMERALD BACKGROUND */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 40%, #081d19 100%) !important;
        background-attachment: fixed !important;
    }

    /* Header Accent Styling */
    h1 {
        background: linear-gradient(90deg, #ffffff 0%, #a7f3d0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
    }
    h2, h3 {
        color: #f3f4f6 !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px;
    }

    /* 2. HERO SECTION STYLING */
    .ag-hero-container {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 78, 59, 0.25) 50%, rgba(17, 24, 39, 0.8) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        animation: heroSlideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @keyframes heroSlideUp {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .ag-hero-badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 20px;
        color: #6ee7b7;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 10px;
    }
    .ag-hero-title {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        margin-bottom: 6px !important;
    }
    .ag-hero-subtitle {
        color: #9ca3af;
        font-size: 0.98rem;
        margin-bottom: 14px;
        max-width: 800px;
    }
    .ag-hero-pills {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .ag-pill {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        color: #e5e7eb;
    }

    /* 3. PAGE TRANSITION (SMOOTH FADE & UPWARD SLIDE) */
    [data-testid="stMainBlockContainer"] {
        animation: dashboardFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    @keyframes dashboardFadeIn {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* 4. METRIC CARDS & GLASSMORPHISM CONTAINERS */
    [data-testid="stMetric"], .stMetric {
        background: rgba(17, 24, 39, 0.7) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s ease, border-color 0.25s ease !important;
        animation: cardStagger 0.45s ease-out forwards;
    }
    [data-testid="stMetric"]:hover, .stMetric:hover {
        transform: translateY(-4px) scale(1.01) !important;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5), 0 0 16px rgba(16, 185, 129, 0.2) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
    }

    /* 5. BEST CROP HIGHLIGHT CARD */
    .best-crop-card {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(17, 24, 39, 0.85) 100%) !important;
        border: 2px solid #10b981 !important;
        border-radius: 16px !important;
        padding: 24px 28px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(16, 185, 129, 0.25) !important;
        margin-bottom: 24px !important;
        animation: bestCropReveal 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
    }
    .best-crop-card:hover {
        transform: translateY(-3px) scale(1.006) !important;
        box-shadow: 0 14px 36px rgba(0, 0, 0, 0.6), 0 0 28px rgba(16, 185, 129, 0.35) !important;
    }
    @keyframes bestCropReveal {
        from { opacity: 0; transform: translateY(14px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .best-crop-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .best-crop-badge {
        background: rgba(16, 185, 129, 0.2);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 20px;
        padding: 4px 14px;
        color: #6ee7b7;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .best-crop-score {
        color: #f3f4f6;
        font-size: 0.95rem;
    }
    .best-crop-name {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        margin-bottom: 16px !important;
    }
    .best-crop-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 16px;
    }
    .best-crop-item {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px 14px;
    }
    .bc-label {
        font-size: 0.78rem;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .bc-val {
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
    }

    /* 6. STATUS DOT ANIMATIONS */
    .pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .green-pulse {
        background: #10b981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulseGreen 2s infinite;
    }
    @keyframes pulseGreen {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    .red-pulse {
        background: #ef4444;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        animation: pulseRed 1.8s infinite;
    }
    @keyframes pulseRed {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .yellow-dot { background: #f59e0b; }
    .blue-dot { background: #3b82f6; }

    /* 7. RISK BADGES */
    .risk-low { color: #10b981 !important; font-weight: 700; }
    .risk-medium { color: #f59e0b !important; font-weight: 700; }
    .risk-high { color: #ef4444 !important; font-weight: 700; }

    /* 8. BUTTON & INPUT POLISH */
    .stButton > button {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 18px rgba(16, 185, 129, 0.3) !important;
        border-color: #10b981 !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        box-shadow: 0 8px 22px rgba(16, 185, 129, 0.5) !important;
    }

    div[data-baseweb="input"] input, div[data-baseweb="select"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        border-radius: 10px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #10b981 !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25) !important;
    }

    [data-testid="stSidebar"] {
        background: rgba(11, 15, 25, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
    }

    /* ================================================================== */
    /* PREMIUM FRONTEND LOGIN UI STYLING & ANIMATIONS                     */
    /* ================================================================== */
    .login-brand-panel {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 78, 59, 0.28) 50%, rgba(17, 24, 39, 0.85) 100%);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 20px;
        padding: 36px 32px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 440px;
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
        animation: loginFadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    .login-brand-panel:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.5), 0 0 30px rgba(16, 185, 129, 0.2);
    }

    @keyframes loginFadeIn {
        from { opacity: 0; transform: translateY(18px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .brand-header-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        background: rgba(16, 185, 129, 0.18);
        border: 1px solid rgba(16, 185, 129, 0.4);
        border-radius: 30px;
        color: #6ee7b7;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        width: fit-content;
        margin-bottom: 16px;
    }

    .brand-hero-title {
        font-size: 2.3rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        line-height: 1.2 !important;
        margin-bottom: 10px !important;
        background: linear-gradient(90deg, #ffffff 0%, #a7f3d0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .brand-hero-tagline {
        color: #d1d5db;
        font-size: 1.05rem;
        font-style: italic;
        margin-bottom: 28px;
        line-height: 1.5;
    }

    .features-list {
        display: flex;
        flex-direction: column;
        gap: 14px;
        margin-bottom: 28px;
    }

    .feature-item {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 12px 16px;
        border-radius: 12px;
        color: #f3f4f6;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.25s ease;
    }
    .feature-item:hover {
        background: rgba(16, 185, 129, 0.12);
        border-color: rgba(16, 185, 129, 0.35);
        transform: translateX(4px);
    }
    .feature-check {
        color: #10b981;
        font-weight: 800;
        font-size: 1.1rem;
    }

    .ai-agri-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        padding-top: 18px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        color: #9ca3af;
        font-size: 0.82rem;
    }

    /* RIGHT PROFESSIONAL LOGIN CARD */
    .login-card {
        background: rgba(17, 24, 39, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 28px 28px 16px 28px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), 0 0 25px rgba(16, 185, 129, 0.12);
        transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
        animation: cardSlideUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        margin-bottom: 14px;
    }
    .login-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6), 0 0 35px rgba(16, 185, 129, 0.2);
        border-color: rgba(16, 185, 129, 0.4);
    }

    @keyframes cardSlideUp {
        from { opacity: 0; transform: translateY(22px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .login-header-title {
        font-size: 1.85rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        margin-bottom: 6px !important;
    }
    .login-header-sub {
        color: #9ca3af;
        font-size: 0.92rem;
    }

    .login-divider {
        display: flex;
        align-items: center;
        text-align: center;
        color: #6b7280;
        font-size: 0.8rem;
        margin: 18px 0 12px 0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .login-divider::before, .login-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }
    .login-divider:not(:empty)::before {
        margin-right: .75em;
    }
    .login-divider:not(:empty)::after {
        margin-left: .75em;
    }

    /* ACCESSIBILITY: REDUCED MOTION SUPPORT */
    @media (prefers-reduced-motion: reduce) {
        *, ::before, ::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


inject_custom_css()


def inject_sidebar_css():
    """Inject CSS animations and visual polish specifically for sidebar radio navigation."""
    css = """
    <style>
    /* SIDEBAR RADIO NAVIGATION CONTAINER SPACING */
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 6px !important;
        padding-top: 4px !important;
    }

    /* ALL SIDEBAR RADIO ITEM LABELS */
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        padding: 8px 12px !important;
        margin-bottom: 2px !important;
        border-radius: 8px !important;
        border-left: 3px solid transparent !important;
        transition: background-color 0.2s ease, transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease !important;
        cursor: pointer !important;
        width: 100% !important;
    }

    /* HOVER EFFECT ON NON-ACTIVE ITEMS */
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        transform: translateX(4px) !important;
        border-left-color: rgba(16, 185, 129, 0.5) !important;
    }

    /* ACTIVE SELECTED ITEM HIGHLIGHT */
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked),
    div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.22) 0%, rgba(16, 185, 129, 0.06) 100%) !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 0 10px 10px 0 !important;
        box-shadow: 0 2px 10px rgba(16, 185, 129, 0.15) !important;
        transform: translateX(4px) !important;
    }

    /* TEXT & ICON TYPOGRAPHY POLISH */
    div[data-testid="stRadio"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.94rem !important;
        font-weight: 500 !important;
        transition: color 0.2s ease, transform 0.2s ease !important;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"] div[role="radiogroup"] label[aria-checked="true"] div[data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label:hover div[data-testid="stMarkdownContainer"] p {
        color: #a7f3d0 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


inject_sidebar_css()

load_dotenv()

# === Caching Wrappers ===

@st.cache_data(ttl=WEATHER_CACHE_TTL)
def cached_get_coordinates(query: str):
    """Cached geocoding wrapper around get_coordinates."""
    return get_coordinates(query)


@st.cache_data(ttl=WEATHER_CACHE_TTL)
def cached_get_current_weather(lat: float, lon: float):
    """Cached current weather wrapper."""
    return get_current_weather(lat, lon)


@st.cache_data(ttl=FORECAST_CACHE_TTL)
def cached_get_weather_forecast(lat: float, lon: float):
    """Cached weather forecast wrapper."""
    return get_weather_forecast(lat, lon)


def clear_weather_caches():
    """Clear cached weather/geocode results."""
    try:
        cached_get_current_weather.clear()
    except Exception:
        pass
    try:
        cached_get_weather_forecast.clear()
    except Exception:
        pass
    try:
        cached_get_coordinates.clear()
    except Exception:
        pass


@st.cache_resource
def load_model(path=MODEL_PATH):
    """Load Random Forest classifier model."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found at: {path}")
    return joblib.load(path)


# Model Loading with Graceful Error Handling
MODEL_LOADED = False
model = None
model_error_msg = ""
try:
    model = load_model()
    MODEL_LOADED = True
except Exception as e:
    model_error_msg = str(e)
    MODEL_LOADED = False


# === Initialize Session State ===
if 'location_meta' not in st.session_state:
    st.session_state['location_meta'] = None

if 'weather_mode' not in st.session_state:
    st.session_state['weather_mode'] = 'AUTO'

if 'manual_weather' not in st.session_state:
    st.session_state['manual_weather'] = {'temp': 25.0, 'humidity': 70.0, 'rainfall': 100.0, 'wind': 2.5}

if 'last_results' not in st.session_state:
    st.session_state['last_results'] = None


@st.cache_data(ttl=604800)
def cached_get_seasonal_climate_average(lat: float, lon: float, season_name: str):
    return get_seasonal_climate_average(lat, lon, season_name)


# Helper to format Plotly charts
def format_plotly_figure(fig, title=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="Plus Jakarta Sans, sans-serif",
        margin=dict(l=20, r=20, t=45, b=20),
        transition={'duration': 500, 'easing': 'cubic-in-out'},
    )
    return fig


# Helper to get Weather Emoji
def get_weather_emoji(condition: str) -> str:
    c = str(condition).lower()
    if 'sun' in c or 'clear' in c:
        return '☀️'
    elif 'cloud' in c or 'overcast' in c:
        return '☁️'
    elif 'rain' in c or 'drizzle' in c:
        return '🌧'
    elif 'storm' in c or 'thunder' in c:
        return '⛈'
    elif 'snow' in c:
        return '❄️'
    elif 'fog' in c or 'mist' in c:
        return '🌫'
    return '🌤'


def render_hero_banner():
    """Render an attractive animated hero section."""
    html = """
    <div class="ag-hero-container">
        <div class="ag-hero-badge">🌱 SMART AGRICULTURE INTELLIGENCE</div>
        <div class="ag-hero-title">Decision Intelligence for Better Farming</div>
        <p class="ag-hero-subtitle">Real-Time AI Multi-Factor Analytics: Soil Screening + Live Weather + Market Pricing + Machine Learning Risk Engine</p>
        <div class="ag-hero-pills">
            <span class="ag-pill">🧪 Soil Analysis</span>
            <span class="ag-pill">☀️ Live Weather</span>
            <span class="ag-pill">🤖 RandomForest AI</span>
            <span class="ag-pill">💰 ROI & Market Economics</span>
            <span class="ag-pill">⚖️ Risk Assessment</span>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_empty_state(title: str, subtitle: str, icon: str = "🌾", button_label: str = "🌾 Go to Crop Recommendation", target_page: str = "🌾 Crop Recommendation"):
    """Render a rich, styled empty-state container with a direct CTA button."""
    empty_html = f"""
    <div class="empty-state-card">
        <div class="empty-state-icon">{icon}</div>
        <h3 class="empty-state-title">{title}</h3>
        <p class="empty-state-sub">{subtitle}</p>
    </div>
    """
    st.markdown(empty_html, unsafe_allow_html=True)

    if button_label and target_page:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            key_id = f"empty_cta_{target_page.replace(' ', '_').replace('🌾', 'crop')}"
            if st.button(button_label, use_container_width=True, type="primary", key=key_id):
                st.session_state["nav_choice"] = target_page
                st.rerun()


def render_app_footer():
    """Render a consistent grounding disclaimer and branding footer across all pages."""
    footer_html = """
    <div class="app-global-footer">
        <hr class="footer-divider" />
        <div class="footer-creator-text">Built &amp; Developed by <span class="footer-author-name">Tharanibalan B.</span></div>
        <div class="footer-app-title">Smart Agriculture Decision Support System</div>
        <div class="footer-copyright-text">© 2026 Tharanibalan B. All Rights Reserved.</div>
        <div class="footer-disclaimer-note">Not a substitute for professional agricultural field advice.</div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)


def get_current_user():
    """
    Unified authentication helper combining Streamlit Google OAuth (st.user)
    and SQLite email/password session (st.session_state.local_user).
    """
    is_google_logged_in = getattr(st.user, "is_logged_in", False) if hasattr(st, "user") else False
    if is_google_logged_in:
        u_name = getattr(st.user, "name", "User") or "Authenticated User"
        u_email = getattr(st.user, "email", "") or ""
        return {
            "is_logged_in": True,
            "name": u_name,
            "email": u_email,
            "auth_method": "google"
        }

    local_user = st.session_state.get("local_user")
    if local_user and isinstance(local_user, dict) and local_user.get("email"):
        return {
            "is_logged_in": True,
            "name": local_user.get("name", "Local User"),
            "email": local_user.get("email", ""),
            "auth_method": "local"
        }

    return {
        "is_logged_in": False,
        "name": "",
        "email": "",
        "auth_method": None
    }


def require_authentication() -> bool:
    """Centralized authentication guard for protected pages.

    Returns True if user is authenticated (via local bcrypt login or Google OAuth).
    Otherwise renders a clean access restriction notice and halts execution to prevent
    unauthorized data access, ML model execution, or API calls.
    """
    user_info = get_current_user()
    if user_info and user_info.get("is_logged_in"):
        return True

    # Render clean unauthenticated access warning
    st.warning("🔐 Please sign in to access this feature.")

    st.markdown("""
        <div class="empty-state-card" style="border-color: rgba(239, 68, 68, 0.4);">
            <div class="empty-state-icon">🔒</div>
            <h3 class="empty-state-title">Authentication Required</h3>
            <p class="empty-state-sub">
                This section contains decision intelligence tools, historical data, or analytical engines.
                Please sign in with your email account or Google OAuth to continue.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔑 Go to Sign In", use_container_width=True, type="primary", key="auth_guard_login_btn"):
            st.session_state["nav_choice"] = "🔑 Sign In"
            st.rerun()

    render_app_footer()
    try:
        st.stop()
    except Exception:
        pass
    return False


def get_user_avatar_color(identifier: str) -> str:
    """Generate a deterministic HSL color string based on user name/email hash."""
    import hashlib
    if not identifier:
        identifier = "User"
    h = int(hashlib.md5(identifier.lower().strip().encode('utf-8')).hexdigest(), 16)
    hue = h % 360
    return f"hsl({hue}, 65%, 40%)"


# Check unified authentication status
curr_user = get_current_user()
is_logged_in = curr_user["is_logged_in"]

# === Sidebar: Navigation & Data Status ===
with st.sidebar:
    st.title("🌱 Smart Ag DSS")
    
    # Sidebar User Profile CSS Styling
    st.markdown("""
    <style>
    .sidebar-user-card {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(30, 41, 59, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 12px 14px;
        margin-top: 8px;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        backdrop-filter: blur(10px);
    }
    .sidebar-avatar-circle {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
        font-weight: 800;
        color: #ffffff;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        text-transform: uppercase;
        border: 2px solid rgba(255, 255, 255, 0.2);
    }
    .sidebar-user-details {
        display: flex;
        flex-direction: column;
        overflow: hidden;
        flex: 1;
    }
    .sidebar-user-name {
        font-weight: 700;
        font-size: 0.95rem;
        color: #f3f4f6;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.25;
    }
    .sidebar-user-email {
        font-size: 0.76rem;
        color: #9ca3af;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 2px;
        margin-bottom: 5px;
    }
    .sidebar-auth-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 20px;
        width: fit-content;
        line-height: 1.3;
    }
    .badge-google {
        background-color: rgba(59, 130, 246, 0.18);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.35);
    }
    .badge-local {
        background-color: rgba(16, 185, 129, 0.18);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .sidebar-logged-out-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px dashed rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 10px 14px;
        margin-top: 8px;
        margin-bottom: 8px;
        color: #9ca3af;
        font-size: 0.82rem;
        text-align: center;
    }
    div[data-testid="stSidebar"] div.stButton > button[key="sidebar_logout_btn"] {
        background-color: rgba(255, 255, 255, 0.04) !important;
        color: #d1d5db !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 6px 12px !important;
        margin-top: 2px !important;
        margin-bottom: 4px !important;
        transition: all 0.18s ease-in-out !important;
    }
    div[data-testid="stSidebar"] div.stButton > button[key="sidebar_logout_btn"]:hover {
        background-color: rgba(239, 68, 68, 0.2) !important;
        color: #f87171 !important;
        border-color: rgba(239, 68, 68, 0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* Streamlit Alert Styling Harmonization */
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
        backdrop-filter: blur(10px) !important;
        font-size: 0.92rem !important;
        border-width: 1px !important;
        border-style: solid !important;
    }
    div[data-testid="stAlert"]:has(div:contains("🟢")),
    div[data-testid="stAlert"]:has(div:contains("✅")),
    div[data-testid="stAlert"][kind="success"] {
        background-color: rgba(16, 185, 129, 0.12) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        color: #6ee7b7 !important;
    }
    div[data-testid="stAlert"]:has(div:contains("⚠️")),
    div[data-testid="stAlert"][kind="error"] {
        background-color: rgba(239, 68, 68, 0.12) !important;
        border-color: rgba(239, 68, 68, 0.4) !important;
        color: #fca5a5 !important;
    }
    div[data-testid="stAlert"][kind="warning"] {
        background-color: rgba(245, 158, 11, 0.12) !important;
        border-color: rgba(245, 158, 11, 0.4) !important;
        color: #fcd34d !important;
    }
    div[data-testid="stAlert"][kind="info"] {
        background-color: rgba(59, 130, 246, 0.12) !important;
        border-color: rgba(59, 130, 246, 0.4) !important;
        color: #93c5fd !important;
    }

    /* Empty State Card Styling */
    .empty-state-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(17, 24, 39, 0.85) 100%);
        border: 1px dashed rgba(16, 185, 129, 0.4);
        border-radius: 16px;
        padding: 36px 24px;
        text-align: center;
        margin: 20px 0 24px 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .empty-state-icon {
        font-size: 3.2rem;
        margin-bottom: 12px;
        filter: drop-shadow(0 4px 12px rgba(16, 185, 129, 0.3));
    }
    .empty-state-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #f3f4f6;
        margin-bottom: 8px;
    }
    .empty-state-sub {
        font-size: 0.92rem;
        color: #9ca3af;
        max-width: 520px;
        margin: 0 auto 16px auto;
        line-height: 1.5;
    }

    /* Global App Footer */
    .app-global-footer {
        margin-top: 45px;
        margin-bottom: 25px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .footer-divider {
        width: 100%;
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        margin-bottom: 14px;
    }
    .footer-creator-text {
        font-size: 0.96rem;
        font-weight: 600;
        color: #f3f4f6;
        letter-spacing: 0.2px;
    }
    .footer-author-name {
        color: #34d399;
        font-weight: 700;
    }
    .footer-app-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #9ca3af;
        letter-spacing: 0.3px;
    }
    .footer-copyright-text {
        font-size: 0.78rem;
        color: #6b7280;
    }
    .footer-disclaimer-note {
        font-size: 0.74rem;
        font-style: italic;
        color: #4b5563;
        margin-top: 2px;
    }

    /* WhatsApp Share Button Styling */
    .whatsapp-share-btn {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        width: 100% !important;
        height: 42px !important;
        background-color: rgba(37, 211, 102, 0.12) !important;
        color: #25D366 !important;
        border: 1px solid rgba(37, 211, 102, 0.4) !important;
        border-radius: 12px !important;
        padding: 0 16px !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        text-decoration: none !important;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.15) !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-sizing: border-box !important;
    }
    .whatsapp-share-btn:hover {
        background-color: #25D366 !important;
        color: #ffffff !important;
        border-color: #25D366 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.35) !important;
    }
    .whatsapp-share-btn:hover .whatsapp-btn-svg path {
        fill: #ffffff !important;
    }
    .whatsapp-btn-svg {
        flex-shrink: 0 !important;
        vertical-align: middle !important;
        transition: fill 0.18s ease !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if is_logged_in:
        u_name = curr_user["name"] or "User"
        u_email = curr_user["email"] or ""
        initial = (u_name[0] if u_name else (u_email[0] if u_email else "U")).upper()
        avatar_bg = get_user_avatar_color(u_email or u_name)
        
        if curr_user["auth_method"] == "google":
            badge_class = "badge-google"
            badge_icon = "🔑"
            badge_text = "Google"
        else:
            badge_class = "badge-local"
            badge_icon = "📧"
            badge_text = "Local Account"

        st.markdown(f"""
            <div class="sidebar-user-card">
                <div class="sidebar-avatar-circle" style="background-color: {avatar_bg};">
                    {initial}
                </div>
                <div class="sidebar-user-details">
                    <div class="sidebar-user-name" title="{u_name}">{u_name}</div>
                    <div class="sidebar-user-email" title="{u_email}">{u_email}</div>
                    <div class="sidebar-auth-badge {badge_class}">
                        {badge_icon} {badge_text}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Log Out", type="secondary", use_container_width=True, key="sidebar_logout_btn"):
            if curr_user["auth_method"] == "google":
                st.logout()
            else:
                st.session_state["local_user"] = None
                st.rerun()
    else:
        st.markdown("""
            <div class="sidebar-logged-out-card">
                🔒 Authentication: Not Logged In
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="margin: 10px 0 14px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.12);" />', unsafe_allow_html=True)

    # Dynamic navigation menu filtering based on authentication status
    if is_logged_in:
        nav_options = [
            "🏠 Dashboard",
            "🌾 Crop Recommendation",
            "🧪 Soil Analysis",
            "💰 Profit Analysis",
            "📊 Crop Comparison",
            "📜 Prediction History",
            "📄 Reports",
            "ℹ️ About",
        ]
    else:
        nav_options = [
            "🔑 Sign In",
            "ℹ️ About",
        ]

    saved_nav = st.session_state.get("nav_choice")
    if not saved_nav or saved_nav not in nav_options:
        saved_nav = nav_options[0]
        st.session_state["nav_choice"] = saved_nav

    default_index = nav_options.index(saved_nav)

    nav_choice = st.radio(
        "Navigation",
        nav_options,
        index=default_index,
        key="main_sidebar_nav_radio",
    )
    st.session_state["nav_choice"] = nav_choice

    st.markdown("---")
    st.subheader("🔎 Data Status Panel")

    market_key = os.getenv("MARKET_API_KEY")
    market_url = os.getenv("MARKET_API_URL")

    # 1. Model Status
    model_dot = "<span class='pulse-dot green-pulse'></span> <b>READY</b>" if MODEL_LOADED else "<span class='pulse-dot red-pulse'></span> <b>MISSING</b>"
    st.markdown(f"**ML Model:** {model_dot}", unsafe_allow_html=True)

    # 2. Location Status
    loc_meta = st.session_state.get('location_meta')
    if loc_meta and loc_meta.get('lat') is not None:
        if loc_meta.get('is_manual'):
            loc_dot = "<span class='pulse-dot blue-dot'></span> <b>USER INPUT</b>"
        else:
            loc_dot = "<span class='pulse-dot green-pulse'></span> <b>LIVE</b>"
    else:
        loc_dot = "<span class='pulse-dot red-pulse'></span> <b>NOT SET</b>"
    st.markdown(f"**Location:** {loc_dot}", unsafe_allow_html=True)

    # 3. Weather Status
    if loc_meta and loc_meta.get('lat') is not None:
        weather_dot = "<span class='pulse-dot green-pulse'></span> <b>LIVE</b>"
    else:
        weather_dot = "<span class='pulse-dot blue-dot'></span> <b>USER INPUT</b>"
    st.markdown(f"**Weather Data:** {weather_dot}", unsafe_allow_html=True)

    # 4. Soil Status
    st.markdown("**Soil Data:** <span class='pulse-dot blue-dot'></span> <b>USER INPUT</b>", unsafe_allow_html=True)

    # 5. Market Status
    if market_key and market_url:
        market_dot = "<span class='pulse-dot green-pulse'></span> <b>LIVE</b>"
    else:
        market_dot = "<span class='pulse-dot yellow-dot'></span> <b>DEMO</b>"
    st.markdown(f"**Market Data:** {market_dot}", unsafe_allow_html=True)

    st.markdown("---")

    # Weather Cache Control
    if st.button("🔄 Refresh Weather"):
        clear_weather_caches()
        st.success("Weather cache cleared!")
        time.sleep(0.5)
        st.rerun()

    st.markdown("---")
    st.caption(f"scikit-learn: v{sklearn.__version__}")
    st.caption("Model: RandomForest (22 crops)")


# === Main Content Router ===

# -------------------------------------------------------------------
def is_google_oauth_configured():
    """Verify if secrets.toml has valid Google OAuth credentials configured."""
    try:
        if not hasattr(st, "secrets") or "auth" not in st.secrets:
            return False, "Missing [auth] section in .streamlit/secrets.toml"
        auth = st.secrets["auth"]
        cid = str(auth.get("client_id", "")).strip()
        csec = str(auth.get("client_secret", "")).strip()
        if not cid or "YOUR_GOOGLE_CLIENT_ID" in cid:
            return False, "Google Client ID is set to placeholder in .streamlit/secrets.toml"
        if not csec or "YOUR_GOOGLE_CLIENT_SECRET" in csec:
            return False, "Google Client Secret is set to placeholder in .streamlit/secrets.toml"
        return True, "OK"
    except Exception as e:
        return False, f"Could not read secrets configuration: {str(e)}"


def inject_login_css():
    """Inject specialized farm-field background photo and CSS animations for Login/Registration."""
    css = """
    <style>
    /* Full-screen agricultural farm-field background with dark overlay & fallback color */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #111827 !important;
        background-image: linear-gradient(rgba(0, 0, 0, 0.65), rgba(0, 0, 0, 0.65)),
                    url('https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1920&auto=format&fit=crop') !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    .login-hero-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        max-width: 480px;
        margin: 0 auto;
        padding-top: 25px;
        padding-bottom: 15px;
        animation: loginSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    @keyframes loginSlideUp {
        from { opacity: 0; transform: translateY(15px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .login-brand-two-line {
        font-size: 3.2rem;
        font-weight: 800;
        line-height: 1.05;
        text-align: center;
        margin-bottom: 8px;
        letter-spacing: -1px;
    }
    .title-smart {
        color: #ffffff;
        text-shadow: 0 2px 20px rgba(0, 0, 0, 0.8);
    }
    .title-agri {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 2px 10px rgba(16, 185, 129, 0.4));
    }

    .login-tagline-text {
        color: #e5e7eb;
        font-size: 1.02rem;
        font-weight: 500;
        text-align: center;
        margin-bottom: 22px;
        text-shadow: 0 1px 10px rgba(0, 0, 0, 0.7);
    }

    /* 1. Page Load Form Card Animation & Glassmorphism */
    form[data-testid="stForm"] {
        width: 100% !important;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(17, 24, 39, 0.88) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 24px !important;
        padding: 32px 28px 24px 28px !important;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.75), 0 0 40px rgba(16, 185, 129, 0.2) !important;
        margin-bottom: 12px !important;
        animation: cardEntrance 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
    }

    @keyframes cardEntrance {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* 2. Staggered Title & Subtitle Fade-in */
    .login-card-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #ffffff;
        text-align: center;
        margin-bottom: 6px;
        animation: titleFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both;
    }

    .login-card-sub {
        font-size: 0.9rem;
        color: #9ca3af;
        text-align: center;
        margin-bottom: 20px;
        line-height: 1.4;
        animation: subFadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both;
    }

    @keyframes titleFadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes subFadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* 3. Input Fields Focus Transition */
    div[data-baseweb="input"] {
        transition: border-color 0.18s ease-in-out, box-shadow 0.18s ease-in-out, background-color 0.18s ease-in-out !important;
        border-radius: 12px !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #10b981 !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25) !important;
    }

    /* 4. Sign In Button Hover & Click Active Transitions */
    div[data-testid="stFormSubmitButton"] > button {
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
        border-radius: 12px !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4) !important;
        filter: brightness(1.08) !important;
    }
    div[data-testid="stFormSubmitButton"] > button:active {
        transform: translateY(0px) scale(0.98) !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2) !important;
    }

    /* 5. Remember Me Checkbox Transition */
    div[data-testid="stCheckbox"] label span {
        transition: color 0.18s ease, transform 0.18s ease !important;
    }
    div[data-testid="stCheckbox"]:hover label span {
        color: #10b981 !important;
    }

    /* Auth Section Divider */
    .auth-divider {
        display: flex;
        align-items: center;
        text-align: center;
        color: #9ca3af;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 18px 0 16px 0;
    }
    .auth-divider::before,
    .auth-divider::after {
        content: '';
        flex: 1;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15);
    }
    .auth-divider span {
        padding: 0 10px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* 6. Google Button Hover & Click Active Transitions with Official 4-Color G SVG Icon */
    div.stButton > button:has(p:contains("Google")),
    div.google-btn-wrapper > button,
    button[key="google_oauth_signin_btn"] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #ffffff !important;
        color: #3c4043 !important;
        font-weight: 600 !important;
        font-size: 0.96rem !important;
        border-radius: 12px !important;
        border: 1px solid #dadce0 !important;
        padding: 12px 18px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    div.stButton > button:has(p:contains("Google"))::before,
    div.google-btn-wrapper > button::before,
    button[key="google_oauth_signin_btn"]::before {
        content: '' !important;
        display: inline-block !important;
        width: 20px !important;
        height: 20px !important;
        margin-right: 10px !important;
        background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2048%2048%22%3E%3Cpath%20fill%3D%22%23EA4335%22%20d%3D%22M24%209.5c3.54%200%206.71%201.22%209.21%203.6l6.85-6.85C35.9%202.38%2030.47%200%2024%200%2014.66%200%206.51%205.38%202.56%2013.22l7.98%206.19C12.43%2013.72%2017.74%209.5%2024%209.5z%22%2F%3E%3Cpath%20fill%3D%22%234285F4%22%20d%3D%22M46.98%2024.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58%202.96-2.26%205.48-4.78%207.18l7.73%206c4.51-4.18%207.09-10.36%207.09-17.65z%22%2F%3E%3Cpath%20fill%3D%22%23FBBC05%22%20d%3D%22M10.53%2028.59c-.48-1.45-.76-2.99-.76-4.59s.28-3.14.76-4.59l-7.98-6.19C.92%2016.46%200%2020.12%200%2024s.92%207.54%202.56%2010.78l7.97-6.19z%22%2F%3E%3Cpath%20fill%3D%22%2334A853%22%20d%3D%22M24%2048c6.48%200%2011.93-2.13%2015.89-5.81l-7.73-6c-2.15%201.45-4.92%202.3-8.16%202.3-6.26%200-11.57-4.22-13.47-9.91l-7.98%206.19C6.51%2042.62%2014.66%2048%2024%2048z%22%2F%3E%3C%2Fsvg%3E") !important;
        background-size: contain !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        flex-shrink: 0 !important;
    }
    div.stButton > button:has(p:contains("Google")):hover,
    div.google-btn-wrapper > button:hover,
    button[key="google_oauth_signin_btn"]:hover {
        background-color: #ffffff !important;
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35) !important;
    }
    div.stButton > button:has(p:contains("Google")):active,
    div.google-btn-wrapper > button:active,
    button[key="google_oauth_signin_btn"]:active {
        transform: translateY(0px) scale(0.98) !important;
    }

    /* WhatsApp Support Link Styling */
    .login-whatsapp-support {
        margin-top: 14px;
        margin-bottom: 6px;
        text-align: center;
    }
    .whatsapp-help-link {
        color: #9ca3af !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-decoration: none !important;
        transition: color 0.18s ease, transform 0.18s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
    }
    .whatsapp-help-link:hover {
        color: #25D366 !important;
        text-decoration: underline !important;
    }
    .whatsapp-icon-svg {
        vertical-align: middle;
        flex-shrink: 0;
    }

    .login-footer-security {
        margin-top: 16px;
        text-align: center;
        color: #9ca3af;
        font-size: 0.8rem;
    }
    </style>
    """
    render_html(css)


# -------------------------------------------------------------------
# PAGE: 🔑 AUTHENTICATION (EMAIL/PASSWORD + GOOGLE OAUTH)
# -------------------------------------------------------------------
def page_login():
    """Render a modern dark-mode AI agriculture login page supporting Email/Password and Google OAuth."""
    inject_login_css()

    curr_user = get_current_user()
    if curr_user["is_logged_in"]:
        st.success(f"✅ You are logged in as **{curr_user['name']}** (`{curr_user['email']}`).")
        st.info("Use the sidebar menu to navigate to Dashboard or Crop Recommendation.")
        return

    auth_mode = st.session_state.get("auth_mode", "login")

    render_html("""
        <div class="login-hero-container">
            <div style="font-size: 3rem; margin-bottom: 4px;">🌱</div>
            <div class="login-brand-two-line">
                <span class="title-smart">Smart</span><br/>
                <span class="title-agri">Agriculture</span>
            </div>
            <div class="login-tagline-text">AI-powered intelligence for smarter farming.</div>
        </div>
    """)

    c1, c2, c3 = st.columns([0.15, 0.7, 0.15])
    with c2:
        if auth_mode == "login":
            with st.form("local_login_form", clear_on_submit=False):
                render_html("""
                    <div class="login-card-title">Welcome Back 👋</div>
                    <div class="login-card-sub">Sign in with your email or Google account to access decision intelligence.</div>
                """)

                email = st.text_input("📧 Email Address", placeholder="e.g. farmer@example.com")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                remember_me = st.checkbox("Remember me", value=True, help="Keeps session active during current browser tab session.")

                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submitted:
                    ok, msg, user_dict = verify_user(email, password)
                    if ok:
                        st.session_state["local_user"] = user_dict
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msg}")

            render_html("""
                <div class="auth-divider">
                    <span>Or continue with</span>
                </div>
            """)

            render_html('<div class="google-btn-wrapper">')
            if st.button("Continue with Google", use_container_width=True, key="google_oauth_signin_btn"):
                is_conf, msg = is_google_oauth_configured()
                if is_conf:
                    try:
                        st.login("google")
                    except Exception as err:
                        st.error(f"⚠️ Google OAuth Error: {err}")
                else:
                    st.warning(f"⚠️ **Google OAuth Setup Required**: {msg}")
            render_html('</div>')

            st.markdown("---")
            if st.button("Don't have an account? **Register**", use_container_width=True, key="switch_to_register_btn"):
                st.session_state["auth_mode"] = "register"
                st.rerun()

        else:  # Registration View
            with st.form("local_register_form", clear_on_submit=False):
                render_html("""
                    <div class="login-card-title">Create Account 🌱</div>
                    <div class="login-card-sub">Register to save crop recommendations and farm analytics.</div>
                """)

                reg_name = st.text_input("👤 Full Name", placeholder="e.g. Ramesh Kumar")
                reg_email = st.text_input("📧 Email Address", placeholder="e.g. ramesh@farm.com")
                reg_pass1 = st.text_input("🔒 Password", type="password", placeholder="At least 8 characters")
                reg_pass2 = st.text_input("🔒 Confirm Password", type="password", placeholder="Re-enter password")

                reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if reg_submitted:
                    if reg_pass1 != reg_pass2:
                        st.error("⚠️ Passwords do not match.")
                    else:
                        ok, res = register_user(reg_name, reg_email, reg_pass1)
                        if ok:
                            st.session_state["local_user"] = res
                            st.success("🎉 Account created successfully! Logging you in...")
                            st.rerun()
                        else:
                            st.error(f"⚠️ {res}")

            st.markdown("---")
            if st.button("Already have an account? **Sign In**", use_container_width=True, key="switch_to_login_btn"):
                st.session_state["auth_mode"] = "login"
                st.rerun()

        # WhatsApp Support Contact Link (Placeholder phone number: Replace <YOUR_WHATSAPP_NUMBER_HERE> with your number in international format e.g. 91XXXXXXXXXX)
        render_html("""
            <div class="login-whatsapp-support">
                <a href="https://wa.me/<YOUR_WHATSAPP_NUMBER_HERE>?text=Hi%2C%20I%20need%20help%20signing%20into%20Smart%20Agriculture%20DSS" target="_blank" rel="noopener noreferrer" class="whatsapp-help-link">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="#25D366" class="whatsapp-icon-svg">
                      <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.572-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
                    </svg>
                    Need help signing in? Chat with us on WhatsApp
                </a>
            </div>
        """)

        render_html("""
            <div class="login-footer-security">
                🔒 Protected by SQLite Bcrypt Encryption & Google OAuth 2.0.
            </div>
        """)


# -------------------------------------------------------------------
# PAGE: 🌾 CROP RECOMMENDATION
# -------------------------------------------------------------------
def page_crop_recommendation():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("🌾 Crop Recommendation Engine")
    st.markdown("Enter location, weather preferences, and soil parameters to compute optimized crop recommendations.")

    if not MODEL_LOADED:
        st.error(f"⚠️ ML Model Not Loaded: {model_error_msg}. Run `python train_model.py` to generate `crop_model.pkl`.")

    # STEP 1: LOCATION
    st.subheader("1. Location Setup")
    st.caption("Search for an Indian city, or use your browser GPS location.")

    def searchbox_location_provider(searchterm: str):
        if not searchterm or len(str(searchterm).strip()) < 2:
            return []
        results = search_locations(searchterm)
        if not results:
            return [("No matching places found", None)]
        return [(item["label"], item) for item in results]

    loc_col1, loc_col2 = st.columns([3, 1])

    with loc_col1:
        selected_location_data = st_searchbox(
            searchbox_location_provider,
            key="location_searchbox",
            placeholder="Type Indian city, district, or place (e.g. Nagapattinam, Pune, Thanjavur)...",
            clear_on_submit=False,
            debounce=300,
        )

    with loc_col2:
        st.markdown("<div style='padding-top: 4px;'></div>", unsafe_allow_html=True)
        # Note: Browser Geolocation API requires localhost or HTTPS protocol in public deployment.
        if st.button("📍 Use My Location", use_container_width=True, help="Detect browser GPS coordinates (requires localhost or HTTPS)."):
            try:
                loc_gps = get_geolocation()
                if loc_gps and isinstance(loc_gps, dict) and "coords" in loc_gps:
                    coords = loc_gps["coords"]
                    lat_v = float(coords["latitude"])
                    lon_v = float(coords["longitude"])
                    meta = reverse_geocode(lat_v, lon_v)
                    st.session_state['location_meta'] = meta
                    st.success(f"📍 Location Detected: {meta.get('display_name')}")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("⚠️ Location permission denied or browser location unavailable. Please use the search box or manual coordinates below.")
            except Exception as e:
                st.warning("⚠️ Geolocation API error. Please use search box or enter coordinates manually.")

    if selected_location_data and isinstance(selected_location_data, dict):
        st.session_state['location_meta'] = selected_location_data

    st.caption("📶 Note: Browser location on desktop computers can be IP-based and approximate.")

    # Manual Coordinate Fallback Expander
    with st.expander("🛠️ Or Enter Manual Latitude / Longitude"):
        man_col1, man_col2, man_col3 = st.columns([2, 2, 1])
        with man_col1:
            man_lat_in = st.text_input("Latitude", value="")
        with man_col2:
            man_lon_in = st.text_input("Longitude", value="")
        with man_col3:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("Set Coordinates"):
                try:
                    lat_v = float(man_lat_in)
                    lon_v = float(man_lon_in)
                    st.session_state['location_meta'] = {
                        'lat': lat_v,
                        'lon': lon_v,
                        'display_name': f"Manual ({lat_v:.4f}, {lon_v:.4f})",
                        'city': 'Manual Location',
                        'state': 'N/A',
                        'country': 'N/A',
                        'is_manual': True,
                    }
                    st.success(f"Location set to ({lat_v:.4f}, {lon_v:.4f})")
                    st.rerun()
                except ValueError:
                    st.error("Please enter valid numeric latitude and longitude.")

    # Display Current Location State
    current_loc = st.session_state.get('location_meta')
    if current_loc and current_loc.get('lat') is not None:
        st.info(
            f"📍 **Active Location:** {current_loc.get('display_name')} | "
            f"**Lat:** {current_loc.get('lat'):.4f} | **Lon:** {current_loc.get('lon'):.4f}"
        )

    st.markdown("---")

    # STEP 2: WEATHER DATA & PLANNING HORIZON
    st.subheader("2. Weather Inputs & Planning Horizon")

    # Planning Season Selector
    planning_season = st.selectbox(
        "🗓️ Planning for which season?",
        [
            "Current conditions (today)",
            "Kharif (Jun-Oct)",
            "Rabi (Oct-Mar)",
            "Zaid (Mar-Jun)",
        ],
        index=0,
        help="Select 'Current conditions (today)' for live weather, or a specific season for 3-year historical climate averages.",
    )

    is_seasonal = (planning_season != "Current conditions (today)")
    seasonal_climate_data = None
    seasonal_data_failed = False

    if is_seasonal:
        if current_loc and current_loc.get('lat') is not None:
            try:
                seasonal_climate_data = cached_get_seasonal_climate_average(
                    current_loc['lat'], current_loc['lon'], planning_season
                )
            except Exception:
                seasonal_climate_data = None

            if not seasonal_climate_data:
                seasonal_data_failed = True
        else:
            seasonal_data_failed = True

    fetched_live_weather = None
    if (not is_seasonal) and current_loc and current_loc.get('lat') is not None:
        try:
            fetched_live_weather = cached_get_current_weather(current_loc['lat'], current_loc['lon'])
        except Exception:
            fetched_live_weather = None

    if is_seasonal and seasonal_climate_data:
        # Use Historical Seasonal Climate Averages from Open-Meteo Archive API
        w_temp = float(seasonal_climate_data.get('temperature', 25.0))
        w_hum = float(seasonal_climate_data.get('humidity', 70.0)) if seasonal_climate_data.get('humidity') is not None else 70.0
        w_rain = float(seasonal_climate_data.get('rainfall', 100.0))
        w_wind = 2.0
        w_cond = f"Historical Climate ({planning_season})"
        is_live_weather = False
        weather_basis_label = f"Seasonal Historical ({planning_season})"

        loc_label = current_loc.get('display_name') if current_loc else 'Selected Area'
        st.info(
            f"📊 Using historical average conditions for **{planning_season}** at **{loc_label}** "
            f"(based on the last 3 years of weather data) — not live weather"
        )

        if not seasonal_climate_data.get('humidity_available'):
            st.warning("⚠️ Relative humidity data unavailable in historical archive for this location — using standard reference default (70%).")

        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("3-Yr Avg Temp", f"{w_temp:.1f} °C")
        s_col2.metric("3-Yr Avg Humidity", f"{w_hum:.0f} %")
        s_col3.metric("3-Yr Avg Seasonal Rainfall", f"{w_rain:.1f} mm")
        years_str = ", ".join(str(y) for y in seasonal_climate_data.get('years_analyzed', []))
        s_col4.metric("Years Analyzed", years_str if years_str else "3-Year Archive")

    elif is_seasonal and seasonal_data_failed:
        st.warning("⚠️ Historical climate data unavailable for this location — please select 'Current conditions' or enter weather manually")
        is_live_weather = False
        weather_basis_label = "Manual Input (Seasonal Fallback)"

        w_col1, w_col2, w_col3, w_col4 = st.columns(4)
        with w_col1:
            w_temp = st.number_input("Temperature (°C)", min_value=-10.0, max_value=60.0, value=25.0, step=0.5)
        with w_col2:
            w_hum = st.number_input("Relative Humidity (%)", min_value=0.0, max_value=100.0, value=70.0, step=1.0)
        with w_col3:
            w_rain = st.number_input("Annual/Season Rainfall (mm)", min_value=0.0, max_value=3000.0, value=100.0, step=5.0)
        with w_col4:
            w_wind = st.number_input("Wind Speed (m/s)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

    else:
        # Weather Mode Toggle for Current Conditions
        w_mode = st.radio(
            "Weather Source Mode",
            ["🟢 Live Weather (Open-Meteo API)" if fetched_live_weather else "🔴 Live Weather (Select Location Above)", "🔵 Manual Weather Input"],
            index=0 if fetched_live_weather else 1,
            horizontal=True,
        )

        is_live_weather = ("🟢 Live Weather" in w_mode) and (fetched_live_weather is not None)
        weather_basis_label = "Live Weather" if is_live_weather else "Manual Weather Input"

        if is_live_weather:
            w_temp = float(fetched_live_weather.get('temperature', 25.0))
            w_feels = float(fetched_live_weather.get('feels_like', w_temp))
            w_hum = float(fetched_live_weather.get('humidity', 70.0))
            w_rain = float(fetched_live_weather.get('rainfall', 0.0))
            w_wind = float(fetched_live_weather.get('wind_speed', 0.0))
            w_cond = str(fetched_live_weather.get('condition', 'Clear'))
            w_emoji = get_weather_emoji(w_cond)

            st.success(f"🟢 **LIVE WEATHER ACTIVE (Open-Meteo)** — Last Updated: {fetched_live_weather.get('timestamp')}")

            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            m_col1.metric("Temperature", f"{w_temp:.1f} °C", delta=f"Feels like {w_feels:.1f} °C")
            m_col2.metric("Humidity", f"{w_hum:.0f} %")
            m_col3.metric("Rainfall", f"{w_rain:.1f} mm")
            m_col4.metric("Wind Speed", f"{w_wind:.1f} m/s")
            m_col5.metric("Condition", f"{w_emoji} {w_cond}")

            # Forecast Display
            try:
                forecast_data = cached_get_weather_forecast(current_loc['lat'], current_loc['lon'])
                if forecast_data:
                    with st.expander("📅 View 3-Day Forecast (Open-Meteo)"):
                        f_df = pd.DataFrame(forecast_data)
                        st.dataframe(f_df, use_container_width=True)
            except Exception:
                pass
        else:
            st.info("🔵 **MANUAL WEATHER MODE ACTIVE** (Select location above to load automatic live weather).")

            w_col1, w_col2, w_col3, w_col4 = st.columns(4)
            with w_col1:
                w_temp = st.number_input("Temperature (°C)", min_value=-10.0, max_value=60.0, value=25.0, step=0.5)
            with w_col2:
                w_hum = st.number_input("Relative Humidity (%)", min_value=0.0, max_value=100.0, value=70.0, step=1.0)
            with w_col3:
                w_rain = st.number_input("Annual/Season Rainfall (mm)", min_value=0.0, max_value=3000.0, value=100.0, step=5.0)
            with w_col4:
                w_wind = st.number_input("Wind Speed (m/s)", min_value=0.0, max_value=50.0, value=2.0, step=0.5)

    st.markdown("---")

    # STEP 3: SOIL INPUTS
    st.subheader("3. Soil Parameters & Screening")
    st.caption("Enter measured soil nutrient levels (N, P, K in kg/ha) and soil pH.")

    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        N = st.number_input("Nitrogen (N) - kg/ha", min_value=0.0, max_value=500.0, value=90.0, step=1.0)
    with s_col2:
        P = st.number_input("Phosphorus (P) - kg/ha", min_value=0.0, max_value=500.0, value=42.0, step=1.0)
    with s_col3:
        K = st.number_input("Potassium (K) - kg/ha", min_value=0.0, max_value=500.0, value=43.0, step=1.0)
    with s_col4:
        ph = st.number_input("Soil pH (0 - 14)", min_value=0.0, max_value=14.0, value=6.5, step=0.1)

    s_ext1, s_ext2, s_ext3, s_ext4 = st.columns(4)
    with s_ext1:
        soil_type = st.selectbox("Soil Type", INDIAN_SOIL_TYPES)
    with s_ext2:
        irrigation_type = st.selectbox(
            "Irrigation Availability",
            ["Unknown", "Rain-fed only", "Canal", "Borewell", "Drip/Sprinkler"],
            index=0,
            help="Select available irrigation facility. Reliable irrigation boosts effective water availability when rainfall is low.",
        )
    with s_ext3:
        land_size = st.number_input("Land Area (Acres)", min_value=0.1, max_value=1000.0, value=1.0, step=0.5)
    with s_ext4:
        current_top_count = int(st.session_state.get("top_candidates_count", 5))
        if current_top_count < 3 or current_top_count > 20:
            current_top_count = 5
        top_n = st.slider(
            "Top Candidates Count",
            min_value=3,
            max_value=20,
            value=current_top_count,
            step=1,
            key="top_candidates_count_slider",
            help="Select between 3 and 20 top recommended crop candidates to evaluate."
        )
        st.session_state["top_candidates_count"] = top_n

    # Input Validation Warnings
    if N > 250 or P > 150 or K > 250:
        st.warning("⚠️ High nutrient value detected. Please verify your soil lab report entries.")
    if ph < 4.0 or ph > 9.5:
        st.warning("⚠️ Extreme soil pH detected. Highly acidic or alkaline soil severely impacts nutrient availability.")

    # Soil Screening Analysis
    soil_report = analyze_soil(N=N, P=P, K=K, ph=ph, soil_type=soil_type)

    with st.expander("🧪 Immediate Soil Health Screening Preview", expanded=True):
        sc_col1, sc_col2 = st.columns([1, 3])
        with sc_col1:
            st.metric("Soil Health Score", f"{soil_report['score']}/100")
            st.progress(float(soil_report['score']) / 100.0)
        with sc_col2:
            st.markdown(f"**Status Overview:** {', '.join(soil_report['details'])}")
            if soil_report['deficiencies']:
                st.markdown(f"**Deficiencies:** {', '.join(soil_report['deficiencies'])}")
            if soil_report['recommendations']:
                st.markdown(f"**Fertilizer Guidance:** {', '.join(soil_report['recommendations'])}")
        st.caption(f"ℹ️ {soil_report['disclaimer']}")

    st.markdown("---")

    # STEP 4: GENERATE DECISION SUPPORT RECOMMENDATIONS
    st.subheader("4. Execute Decision Support Analysis")

    if st.button(f"🚀 Generate Top-{top_n} Crop Recommendations", type="primary", use_container_width=True):
        if not MODEL_LOADED:
            st.error("Cannot proceed: ML model is missing or failed to load.")
            st.stop()

        with st.spinner("Analyzing soil nutrients, live weather, market pricing, crop suitability & risk factors..."):
            actual_rainfall = float(w_rain)
            weights = get_normalized_weights()
            classes = model.classes_
            classes_list = list(classes)

            # 1. Batch Feature Vector Construction for All Crop Candidates
            feature_matrix = []
            crop_meta_list = []

            for crop_raw in classes:
                crop_name = str(crop_raw).strip().title()
                crop_min_water = float(get_crop_min_water_requirement(crop_name))

                # Crop-specific effective rainfall calculation based on irrigation availability
                if irrigation_type in ["Canal", "Borewell", "Drip/Sprinkler"]:
                    crop_effective_rainfall = max(actual_rainfall, crop_min_water)
                    crop_irrigation_adjusted = (crop_effective_rainfall > actual_rainfall)
                else:
                    crop_effective_rainfall = actual_rainfall
                    crop_irrigation_adjusted = False

                feature_matrix.append([N, P, K, float(w_temp), float(w_hum), float(ph), float(crop_effective_rainfall)])
                crop_meta_list.append({
                    'raw': crop_raw,
                    'name': crop_name,
                    'min_water': crop_min_water,
                    'effective_rainfall': crop_effective_rainfall,
                    'irrigation_adjusted': crop_irrigation_adjusted,
                })

            # Single Batch Scikit-Learn Random Forest Prediction for All 22 Crops
            batch_df = pd.DataFrame(
                feature_matrix,
                columns=["N", "P", "K", "temperature", "humidity", "ph", "rainfall"],
            )
            probs_matrix = model.predict_proba(batch_df)

            # Pre-fetch bulk state market prices in ONE single API request (or 0 requests if cached)
            state_name = current_loc.get('state') if (current_loc and isinstance(current_loc, dict)) else None
            bulk_market_map = cached_get_bulk_market_prices(state_name=state_name)

            recommendation_rows = []

            for idx, meta in enumerate(crop_meta_list):
                crop_raw = meta['raw']
                crop_name = meta['name']
                crop_min_water = meta['min_water']
                crop_effective_rainfall = meta['effective_rainfall']
                crop_irrigation_adjusted = meta['irrigation_adjusted']

                crop_idx = classes_list.index(crop_raw)
                conf = float(probs_matrix[idx, crop_idx])

                # Fast Cached Economic Data Lookup
                econ_raw, econ_status = get_crop_profit_data(crop_name)
                econ_data = dict(econ_raw)

                # Fast Cached Market Price Lookup
                market_price, market_status = get_market_price_for_crop(crop_name, current_loc, preloaded_map=bulk_market_map)
                if market_status == MarketDataStatus.LIVE and market_price is not None:
                    econ_data['market_price'] = market_price
                    econ_data['revenue'] = market_price * econ_data['yield']
                    econ_data['income'] = econ_data['revenue']
                    econ_data['profit'] = econ_data['revenue'] - econ_data['cost']
                    econ_data['roi'] = (econ_data['profit'] / econ_data['cost'] * 100.0) if econ_data['cost'] > 0 else 0.0
                    econ_data['profit_margin'] = (econ_data['profit'] / econ_data['revenue'] * 100.0) if econ_data['revenue'] > 0 else 0.0
                    econ_data['breakeven_yield'] = round(econ_data['cost'] / market_price, 1) if market_price > 0 else None

                # Risk Computation using Crop-Specific Effective Rainfall
                weather_dict = {
                    'temperature': w_temp,
                    'humidity': w_hum,
                    'rainfall': crop_effective_rainfall,
                    'actual_rainfall': actual_rainfall,
                    'effective_rainfall': crop_effective_rainfall,
                    'irrigation_type': irrigation_type,
                    'crop_min_water': crop_min_water,
                }
                risk_level, risk_reasons = compute_risk(
                    crop_name=crop_name,
                    soil_report=soil_report,
                    weather=weather_dict,
                    econ=econ_data,
                    market_status_str=market_status.name,
                )

                # Calibrated 6-Factor Decision Support Score Calculation
                m_score = float(conf)
                s_score = float(soil_report['score']) / 100.0
                w_t_score = 1.0 if 18 <= w_temp <= 35 else (0.6 if 10 <= w_temp <= 42 else 0.2)
                w_r_score = 1.0 if 20 <= crop_effective_rainfall <= 300 else (0.6 if crop_effective_rainfall <= 500 else 0.3)
                w_score = (w_t_score + w_r_score) / 2.0
                season_score = 1.0 if econ_data['season_valid'] else 0.5
                profit_score = min(1.0, max(0.0, (econ_data['roi'] + 20) / 120.0))
                risk_score = 1.0 if risk_level == 'LOW' else (0.6 if risk_level == 'MEDIUM' else 0.2)

                raw_decision_score = (
                    weights['model'] * m_score
                    + weights['soil'] * s_score
                    + weights['weather'] * w_score
                    + weights['season'] * season_score
                    + weights['profit'] * profit_score
                    + weights['risk'] * risk_score
                ) * 100.0

                decision_score = round(max(0.0, min(100.0, raw_decision_score)), 1)

                recommendation_rows.append({
                    'rank': '',
                    'crop': crop_name,
                    'ai_confidence': round(conf * 100.0, 1),
                    'decision_score': decision_score,
                    'market_price': round(econ_data['market_price'], 2),
                    'market_status': market_status.name,
                    'yield_kg': round(econ_data['yield'], 1),
                    'revenue': round(econ_data['revenue'] * land_size, 2),
                    'cost': round(econ_data['cost'] * land_size, 2),
                    'profit': round(econ_data['profit'] * land_size, 2),
                    'roi': round(econ_data['roi'], 1),
                    'breakeven_yield': econ_data['breakeven_yield'],
                    'season': econ_data['season'],
                    'season_valid': econ_data['season_valid'],
                    'risk': risk_level,
                    'risk_reasons': risk_reasons,
                    'crop_min_water': crop_min_water,
                    'crop_effective_rainfall': crop_effective_rainfall,
                    'crop_irrigation_adjusted': crop_irrigation_adjusted,
                })

            df_all = pd.DataFrame(recommendation_rows)
            df_all = df_all.sort_values(by='decision_score', ascending=False).reset_index(drop=True)

            # Geographic & Altitude Suitability Filtering based on District metadata
            eligible_rows = []
            excluded_crops = []

            for _, row in df_all.iterrows():
                crop_name = row['crop']
                is_eligible, ineligible_reason = check_crop_geographic_eligibility(crop_name, current_loc)
                if is_eligible:
                    eligible_rows.append(row.to_dict())
                    if len(eligible_rows) == top_n:
                        break
                else:
                    excluded_crops.append({
                        'crop': crop_name,
                        'reason': ineligible_reason,
                        'score': row['decision_score'],
                    })
                    loc_name = current_loc.get('display_name') if current_loc else 'Selected District'
                    print(f"[GEO-FILTER] Excluded '{crop_name}' (Score: {row['decision_score']}) for location '{loc_name}': {ineligible_reason}")

            if eligible_rows:
                df_recs = pd.DataFrame(eligible_rows)
            else:
                df_recs = df_all.head(top_n)

            for new_idx in range(len(df_recs)):
                rank_badge = f"🥇 #{new_idx + 1} Recommended" if new_idx == 0 else f"#{new_idx + 1}"
                df_recs.at[new_idx, 'rank'] = rank_badge

            best_crop = df_recs.iloc[0].to_dict()

            st.session_state['last_results'] = {
                'df_recs': df_recs,
                'best_crop': best_crop,
                'excluded_crops': excluded_crops,
                'soil_report': soil_report,
                'weather_data': {
                    'temperature': w_temp,
                    'humidity': w_hum,
                    'rainfall': best_crop['crop_effective_rainfall'],
                    'actual_rainfall': actual_rainfall,
                    'effective_rainfall': best_crop['crop_effective_rainfall'],
                    'irrigation_type': irrigation_type,
                    'irrigation_adjusted': best_crop['crop_irrigation_adjusted'],
                    'crop_min_water': best_crop['crop_min_water'],
                    'wind_speed': w_wind,
                    'is_live': is_live_weather,
                },
                'inputs': {
                    'N': N,
                    'P': P,
                    'K': K,
                    'ph': ph,
                    'soil_type': soil_type,
                    'irrigation_type': irrigation_type,
                    'land_size': land_size,
                },
                'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            }

            hist_entry = {
                'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                'user_email': get_current_user()['email'] or 'guest@local',
                'location': current_loc.get('display_name') if current_loc else 'Manual Input',
                'latitude': current_loc.get('lat') if current_loc else None,
                'longitude': current_loc.get('lon') if current_loc else None,
                'N': N,
                'P': P,
                'K': K,
                'ph': ph,
                'temperature': w_temp,
                'humidity': w_hum,
                'rainfall': best_crop['crop_effective_rainfall'],
                'actual_rainfall': actual_rainfall,
                'effective_rainfall': best_crop['crop_effective_rainfall'],
                'irrigation_type': irrigation_type,
                'best_crop': best_crop['crop'],
                'confidence': best_crop['ai_confidence'],
                'decision_score': best_crop['decision_score'],
                'market_price': best_crop['market_price'],
                'market_status': best_crop['market_status'],
                'estimated_yield': best_crop['yield_kg'],
                'revenue': best_crop['revenue'],
                'cost': best_crop['cost'],
                'profit': best_crop['profit'],
                'roi': best_crop['roi'],
                'risk': best_crop['risk'],
                'soil_health_score': soil_report['score'],
            }
            try:
                append_prediction_history(hist_entry)
            except Exception as hist_err:
                st.error(f"⚠️ Failed to save prediction history record: {hist_err}")

    # RENDER RESULTS IF AVAILABLE
    res = st.session_state.get('last_results')
    if res:
        past_in = res.get('inputs', {})
        inputs_changed = (
            past_in.get('N') != N or
            past_in.get('P') != P or
            past_in.get('K') != K or
            past_in.get('ph') != ph or
            past_in.get('soil_type') != soil_type or
            past_in.get('irrigation_type') != irrigation_type or
            past_in.get('land_size') != land_size
        )

        st.markdown("---")
        if inputs_changed:
            st.warning("⚠️ **Parameters Modified**: Soil/farm parameters have been changed. Click **'🚀 Generate Top-5 Crop Recommendations'** above to update recommendation results.")

        # Show Transparent Crop-Specific Irrigation Adjustment Note if Applied
        w_res = res.get('weather_data', {})
        best = res['best_crop']
        if best.get('crop_irrigation_adjusted'):
            c_name = best.get('crop')
            c_req = best.get('crop_min_water', 150.0)
            act_r = w_res.get('actual_rainfall', w_res.get('rainfall'))
            irr_t = w_res.get('irrigation_type', 'Irrigation')
            st.info(f"💧 **{c_name}** minimum water requirement (~{c_req:.0f}mm) assumed met via **{irr_t}** irrigation (actual rainfall: {act_r:.1f}mm)")

        # Show Geographic Filter Exclusions Notice if Applied
        excluded_crops_list = res.get('excluded_crops', [])
        if excluded_crops_list:
            for ex in excluded_crops_list:
                st.caption(f"🚫 **Geographic Filter Excluded**: **{ex['crop']}** (Score: {ex['score']}/100) — {ex['reason']}")

        best = res['best_crop']
        df_recs = res['df_recs']

        # Premium Highlight Card for Best Crop
        best_html = f"""
        <div class="best-crop-card">
            <div class="best-crop-header">
                <span class="best-crop-badge">🏆 #1 BEST RECOMMENDED CROP</span>
                <span class="best-crop-score">Decision Score: <b>{best['decision_score']}/100</b></span>
            </div>
            <h2 class="best-crop-name">🌱 {best['crop']}</h2>
            <div class="best-crop-grid">
                <div class="best-crop-item">
                    <div class="bc-label">AI Confidence</div>
                    <div class="bc-val">{best['ai_confidence']}%</div>
                </div>
                <div class="best-crop-item">
                    <div class="bc-label">Estimated Net Profit</div>
                    <div class="bc-val">₹{best['profit']:,.0f}</div>
                </div>
                <div class="best-crop-item">
                    <div class="bc-label">Calculated ROI</div>
                    <div class="bc-val">{best['roi']}%</div>
                </div>
                <div class="best-crop-item">
                    <div class="bc-label">Risk Level</div>
                    <div class="bc-val risk-{best['risk'].lower()}">{best['risk']} RISK</div>
                </div>
            </div>
        </div>
        """
        st.markdown(best_html, unsafe_allow_html=True)

        is_ref_crop = any(ref in str(best['crop']).lower() for ref in ["sugarcane", "groundnut", "cumbu", "ragi", "turmeric", "cashew", "pearl millet", "finger millet"])
        if is_ref_crop:
            st.warning(
                "🟡 **AGRONOMIC REFERENCE RANGE ESTIMATE**: "
                f"**{best['crop']}** is recommendation-enabled using ICAR/TNAU general agronomic reference ranges, "
                "not measured field trial datasets like the baseline 22 crops. Treat as a generalized reference estimate."
            )

        # Explainable AI Card
        with st.expander("💡 Explainable AI Recommendation Breakdown", expanded=True):
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.markdown("#### ✅ Supporting Factors")
                st.markdown(f"- **Strong ML Classifier Confidence:** {best['ai_confidence']}%")
                st.markdown(f"- **Soil Health Score:** {res['soil_report']['score']}/100 ({', '.join(res['soil_report']['details'])})")
                st.markdown(f"- **Seasonal Alignment:** {best['season']} Season ({'Suitable' if best['season_valid'] else 'Check local calendar'})")
                st.markdown(f"- **Expected Revenue:** ₹{best['revenue']:,.0f} for {res['inputs']['land_size']} Acre(s)")
                st.markdown(f"- **Calculated ROI:** {best['roi']}%")

            with ex_col2:
                st.markdown("#### ⚠️ Risk & Attention Factors")
                if best['risk_reasons']:
                    for r_reason in best['risk_reasons']:
                        st.markdown(f"- ⚠️ {r_reason}")
                else:
                    st.markdown("- No significant risk flags identified.")

                if best['breakeven_yield']:
                    st.markdown(f"- **Break-even Yield Required:** {best['breakeven_yield']} kg/acre")

        # Visual Plotly Charts
        st.subheader("📊 Recommendation Analytics & Visualizations")
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            fig_conf = format_plotly_figure(
                px.bar(
                    df_recs,
                    x='crop',
                    y='ai_confidence',
                    color='crop',
                    title="AI Model Confidence by Candidate Crop (%)",
                    labels={'ai_confidence': 'Confidence (%)', 'crop': 'Crop'},
                )
            )
            st.plotly_chart(fig_conf, use_container_width=True)

            fig_prof = format_plotly_figure(
                px.bar(
                    df_recs,
                    x='crop',
                    y='profit',
                    color='risk',
                    title="Estimated Net Profit by Candidate Crop (₹)",
                    labels={'profit': 'Net Profit (₹)', 'crop': 'Crop'},
                )
            )
            st.plotly_chart(fig_prof, use_container_width=True)

        with p_col2:
            fig_score = format_plotly_figure(
                px.bar(
                    df_recs,
                    x='crop',
                    y='decision_score',
                    color='crop',
                    title="Decision Support Score by Candidate Crop (/100)",
                    labels={'decision_score': 'Decision Score', 'crop': 'Crop'},
                )
            )
            st.plotly_chart(fig_score, use_container_width=True)

            fig_rev_cost = format_plotly_figure(
                px.bar(
                    df_recs,
                    x='crop',
                    y=['revenue', 'cost'],
                    barmode='group',
                    title="Revenue vs Production Cost Comparison (₹)",
                    labels={'value': 'Amount (₹)', 'crop': 'Crop', 'variable': 'Metric'},
                )
            )
            st.plotly_chart(fig_rev_cost, use_container_width=True)

        # Download Report
        st.markdown("---")
        rpt_bytes = build_report(
            location=st.session_state.get('location_meta'),
            weather=res['weather_data'],
            soil=res['soil_report'],
            best=best,
            alternatives=df_recs.to_dict(orient='records'),
            data_status={
                'Location': '🟢 LIVE' if (st.session_state.get('location_meta') and not st.session_state.get('location_meta', {}).get('is_manual')) else '🔵 USER INPUT',
                'Weather': '🟢 LIVE' if res['weather_data']['is_live'] else '🔵 USER INPUT',
                'Soil': '🔵 USER INPUT',
                'Model': '🟢 READY' if MODEL_LOADED else '🔴 MISSING',
                'Market': '🟡 DEMO',
            },
        )
        st.download_button(
            "📄 Download Official Decision Support Report (CSV)",
            data=rpt_bytes,
            file_name=f"crop_decision_report_{int(time.time())}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 🏠 DASHBOARD
# -------------------------------------------------------------------
def page_dashboard():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("🏠 Decision Support Overview Dashboard")

    res = st.session_state.get('last_results')
    if not res:
        render_empty_state(
            title="No Active Decision Run Found",
            subtitle="Execute your first AI multi-factor analysis to populate recommendations, soil screening metrics, and financial breakdown on this overview dashboard.",
            icon="🏠",
            button_label="🌾 Generate First Recommendation",
            target_page="🌾 Crop Recommendation",
        )
        render_app_footer()
        return

    best = res['best_crop']
    soil = res['soil_report']
    w_data = res['weather_data']

    st.subheader("Key Decision Summary")
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    d_col1.metric("Recommended Crop", best['crop'])
    d_col2.metric("Decision Score", f"{best['decision_score']}/100")
    d_col3.metric("Soil Health Score", f"{soil['score']}/100")
    d_col4.metric("Risk Level", best['risk'])

    st.markdown("---")
    d_m1, d_m2, d_m3, d_m4 = st.columns(4)
    d_m1.metric("Temperature", f"{w_data['temperature']} °C")
    d_m2.metric("Humidity", f"{w_data['humidity']} %")
    d_m3.metric("Rainfall", f"{w_data['rainfall']} mm")
    d_m4.metric("Market Data Source", best['market_status'])

    st.markdown("---")
    st.subheader("Top Recommended Candidate Summary")
    st.dataframe(res['df_recs'][['rank', 'crop', 'ai_confidence', 'decision_score', 'profit', 'roi', 'risk']], use_container_width=True)

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 🧪 SOIL ANALYSIS
# -------------------------------------------------------------------
def page_soil_analysis():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("🧪 Soil Screening & Nutrients Analysis")

    res = st.session_state.get('last_results')
    if not res:
        render_empty_state(
            title="No Soil Analysis Data Found",
            subtitle="Execute a crop recommendation analysis to view personalized soil screening, health scores, deficiency alerts, and tailored fertilizer advice.",
            icon="🧪",
            button_label="🌾 Run Crop & Soil Analysis",
            target_page="🌾 Crop Recommendation",
        )
    else:
        soil = res['soil_report']
        sc_c1, sc_c2 = st.columns([1, 3])
        with sc_c1:
            st.metric("Soil Health Screening Score", f"{soil['score']}/100")
            st.progress(float(soil['score']) / 100.0)
        with sc_c2:
            st.markdown(f"**Nutrient Breakdown:** {', '.join(soil['details'])}")
            st.markdown(f"**Identified Strengths:** {', '.join(soil['strengths']) if soil['strengths'] else 'None'}")
            st.markdown(f"**Deficiencies:** {', '.join(soil['deficiencies']) if soil['deficiencies'] else 'None'}")
            st.markdown(f"**Fertilizer Recommendations:** {', '.join(soil['recommendations'])}")
            st.caption(soil['disclaimer'])

    st.markdown("---")
    st.subheader("Standard NPK & pH Optimal Ranges Reference")
    ref_df = pd.DataFrame([
        {"Nutrient / Property": "Nitrogen (N)", "Low": "< 60 kg/ha", "Optimal": "90 - 140 kg/ha", "High": "> 200 kg/ha"},
        {"Nutrient / Property": "Phosphorus (P)", "Low": "< 30 kg/ha", "Optimal": "40 - 80 kg/ha", "High": "> 120 kg/ha"},
        {"Nutrient / Property": "Potassium (K)", "Low": "< 30 kg/ha", "Optimal": "40 - 80 kg/ha", "High": "> 120 kg/ha"},
        {"Nutrient / Property": "Soil pH", "Low": "< 5.5 (Acidic)", "Optimal": "6.0 - 7.5 (Balanced)", "High": "> 8.0 (Alkaline)"},
    ])
    st.dataframe(ref_df, use_container_width=True)

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 💰 PROFIT ANALYSIS
# -------------------------------------------------------------------
def page_profit_analysis():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("💰 Crop Economics & Profitability Analysis")

    res = st.session_state.get('last_results')
    if not res:
        render_empty_state(
            title="No Financial Data Available",
            subtitle="Execute a crop recommendation to analyze revenue, production costs, net profit, return on investment (ROI), and break-even yields.",
            icon="💰",
            button_label="🌾 Compute Crop Profitability",
            target_page="🌾 Crop Recommendation",
        )
        render_app_footer()
        return

    df_recs = res['df_recs']
    st.dataframe(
        df_recs[['rank', 'crop', 'market_price', 'market_status', 'yield_kg', 'revenue', 'cost', 'profit', 'roi', 'breakeven_yield']],
        use_container_width=True,
    )

    st.subheader("Profitability & ROI Comparison")
    fig_roi = format_plotly_figure(px.bar(df_recs, x='crop', y='roi', color='crop', title="Return on Investment (ROI %) by Crop"))
    st.plotly_chart(fig_roi, use_container_width=True)

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 📊 CROP COMPARISON
# -------------------------------------------------------------------
def page_crop_comparison():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("📊 Top Candidate Crops Comprehensive Matrix")

    res = st.session_state.get('last_results')
    if not res:
        render_empty_state(
            title="No Crop Comparison Data",
            subtitle="Execute a recommendation run to compare candidate crops across AI confidence, decision score, profitability, and risk factors.",
            icon="📊",
            button_label="🌾 Compare Candidate Crops",
            target_page="🌾 Crop Recommendation",
        )
        render_app_footer()
        return

    df_recs = res['df_recs']
    st.dataframe(df_recs, use_container_width=True)

    fig_matrix = format_plotly_figure(
        px.scatter(
            df_recs,
            x='ai_confidence',
            y='profit',
            size='decision_score',
            color='risk',
            hover_name='crop',
            title="AI Confidence vs Net Profit (Bubble size = Decision Score)",
            labels={'ai_confidence': 'AI Model Confidence (%)', 'profit': 'Net Profit (₹)'},
        )
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 📜 PREDICTION HISTORY
# -------------------------------------------------------------------
def page_prediction_history():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("📜 Saved Prediction History")

    curr_user = get_current_user()
    if not curr_user["is_logged_in"]:
        st.warning("⚠️ **Authentication Required**: Please sign in to view your prediction history.")
        render_empty_state(
            title="Please sign in to view your prediction history.",
            subtitle="Historical crop recommendations are securely stored per user account. Sign in with your email or Google account to access your saved records.",
            icon="🔒",
            button_label="🔑 Sign In Now",
            target_page="🔑 Sign In",
        )
        render_app_footer()
        return

    user_email = curr_user["email"]
    hist_df = load_user_history(user_email)

    if hist_df is None or hist_df.empty:
        render_empty_state(
            title="No prediction history available yet.",
            subtitle="Your historical crop recommendation runs will be automatically logged here for easy tracking, CSV export, and record keeping.",
            icon="📜",
            button_label="🌾 Generate First Recommendation",
            target_page="🌾 Crop Recommendation",
        )
        render_app_footer()
        return

    # Hide 'user_email' column from the visible display table
    display_df = hist_df.drop(columns=['user_email'], errors='ignore')

    st.dataframe(display_df, use_container_width=True)

    h_col1, h_col2 = st.columns(2)
    with h_col1:
        csv_hist = hist_df.to_csv(index=False).encode('utf-8')
        sanitized_name = (curr_user.get('name') or 'user').lower().replace(' ', '_')
        st.download_button(
            "📥 Download Complete History (CSV)",
            data=csv_hist,
            file_name=f"prediction_history_{sanitized_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with h_col2:
        if st.button("🗑️ Clear History Records", use_container_width=True):
            clear_user_history(user_email)
            st.success("Your prediction history has been cleared.")
            time.sleep(0.5)
            st.rerun()

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: 📄 REPORTS
# -------------------------------------------------------------------
def page_reports():
    if not require_authentication():
        return
    render_hero_banner()

    st.header("📄 Agricultural Decision Support Reports")

    res = st.session_state.get('last_results')
    if not res:
        render_empty_state(
            title="No Report Generated",
            subtitle="Generate a crop recommendation to view, export, and download comprehensive decision support reports in PDF and CSV formats.",
            icon="📄",
            button_label="🌾 Create Decision Report",
            target_page="🌾 Crop Recommendation",
        )
        render_app_footer()
        return

    st.success("Decision report ready for export & sharing!")
    st.json({
        "Timestamp": res['timestamp'],
        "Recommended Crop": res['best_crop']['crop'],
        "Decision Score": f"{res['best_crop']['decision_score']}/100",
        "AI Confidence": f"{res['best_crop']['ai_confidence']}%",
        "Soil Score": f"{res['soil_report']['score']}/100",
        "Est. Profit": f"₹{res['best_crop']['profit']:,.0f}",
    })

    # Prepare Export & Share Data
    loc = st.session_state.get('location_meta')
    weather = res['weather_data']
    soil = res['soil_report']
    inputs = res.get('inputs', {})
    best = res['best_crop']
    alts = res['df_recs'].to_dict(orient='records')
    ts = res.get('timestamp')

    csv_bytes = build_report(location=loc, weather=weather, soil=soil, best=best, alternatives=alts)

    if 'pdf_bytes' not in res:
        res['pdf_bytes'] = build_pdf_report(location=loc, weather=weather, soil=soil, inputs=inputs, best=best, alternatives=alts, timestamp=ts)
    pdf_bytes = res['pdf_bytes']
    wa_url = build_whatsapp_share_url(location=loc, weather=weather, soil=soil, best=best)

    st.markdown("### 📥 Export & Share Options")
    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        st.download_button(
            "📊 Export CSV Report",
            data=csv_bytes,
            file_name=f"crop_decision_report_{int(time.time())}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with exp_col2:
        st.download_button(
            "📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"crop_decision_report_{int(time.time())}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with exp_col3:
        st.markdown(
            f"""
            <a href="{wa_url}" target="_blank" rel="noopener noreferrer" class="whatsapp-share-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#25D366" class="whatsapp-btn-svg">
                  <path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.572-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/>
                </svg>
                <span>Share via WhatsApp</span>
            </a>
            """,
            unsafe_allow_html=True,
        )

    render_app_footer()


# -------------------------------------------------------------------
# PAGE: ℹ️ ABOUT
# -------------------------------------------------------------------
def page_about():
    render_hero_banner()

    st.header("ℹ️ About the Decision Support System")

    # Load dynamic model metrics if available
    metrics = None
    if os.path.exists("model_metrics.json"):
        try:
            with open("model_metrics.json", "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            metrics = None

    acc_str = metrics.get("accuracy_pct", "99.82%") if metrics else "99.82%"
    total_crops = metrics.get("num_crops", 28) if metrics else 28
    total_rows = metrics.get("total_rows", 2800) if metrics else 2800

    st.markdown(f"""
    ### System Architecture & Technical Specification

    The **Real-Time Smart Agriculture Decision Support System** combines machine learning, geocoded live weather, historical seasonal climate archives, rule-based soil health screening, economics, and risk analysis into a unified decision framework.

    #### Key System Components:
    1. **Machine Learning Model:**
       - **Algorithm:** Scikit-Learn `RandomForestClassifier` (200 estimators).
       - **Dataset:** **{total_rows:,}** samples across **{total_crops}** crops (N, P, K, Temperature, Humidity, pH, Rainfall).
       - **Validated Test Accuracy:** **{acc_str}** across held-out test split.
       - **Model File:** `crop_model.pkl`.
    2. **Real-Time Location & Live Weather:**
       - Geocoding powered by OpenStreetMap Nominatim API.
       - Live Weather & 3-Day Forecast powered by Open-Meteo API (requires NO API key).
       - Historical 3-Year Seasonal Climate Averages powered by Open-Meteo Archive API.
       - Automatic fallback to manual weather parameters if live API is unreachable.
    3. **6-Factor Decision Support Engine:**
       - Transparent score (/100) combining **ML Confidence (35%)**, **Soil Screening (20%)**, **Weather Suitability (15%)**, **Season Validity (5%)**, **Profitability ROI (15%)**, and **Risk Level (10%)**.
    4. **Data Transparency System:**
       - Clear status labeling for **🟢 LIVE**, **🟡 DEMO**, **🔵 USER INPUT**, and **🔴 UNAVAILABLE** data sources.

    #### ⚠️ Data Origin & Model Accuracy Disclosures:
    - **Measured Field Data (22 Baseline Crops):** Rice, Maize, Chickpea, Kidneybeans, Pigeonpeas, Mothbeans, Mungbean, Blackgram, Lentil, Pomegranate, Banana, Mango, Grapes, Watermelon, Muskmelon, Apple, Orange, Papaya, Coconut, Cotton, Jute, Coffee — trained on empirical measured field trial dataset.
    - **General Agronomic Reference Ranges (6 Tamil Nadu Crops):** **Sugarcane, Groundnut, Pearl Millet (Cumbu), Finger Millet (Ragi), Turmeric, and Cashew** are included using published ICAR/TNAU general agronomic reference ranges, not measured field data. Recommendations for these 6 crops should be treated as generalized reference-range estimates and are inherently less precise than the baseline 22 crops.

    #### Governance & Disclaimers:
    - *Soil Health Screening:* Soil health scores and fertilizer suggestions are AI-assisted screening tools based on entered values, not laboratory soil tests.
    - *Decision Support Notice:* This tool provides decision support recommendations only. Always consult local agricultural extension officers before commercial planting.
    """)

    render_app_footer()


PROTECTED_PAGES = {
    "🏠 Dashboard",
    "🌾 Crop Recommendation",
    "🧪 Soil Analysis",
    "💰 Profit Analysis",
    "📊 Crop Comparison",
    "📜 Prediction History",
    "📄 Reports",
}

# --- Route Selection ---
if nav_choice in PROTECTED_PAGES:
    require_authentication()

if nav_choice == "🔑 Sign In":
    page_login()
elif nav_choice == "🏠 Dashboard":
    page_dashboard()
elif nav_choice == "🌾 Crop Recommendation":
    page_crop_recommendation()
elif nav_choice == "🧪 Soil Analysis":
    page_soil_analysis()
elif nav_choice == "💰 Profit Analysis":
    page_profit_analysis()
elif nav_choice == "📊 Crop Comparison":
    page_crop_comparison()
elif nav_choice == "📜 Prediction History":
    page_prediction_history()
elif nav_choice == "📄 Reports":
    page_reports()
elif nav_choice == "ℹ️ About":
    page_about()
