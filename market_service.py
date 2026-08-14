"""market_service.py

Provides live mandi crop market price lookups via data.gov.in (Agmarknet) API:
- Resource ID: 9ef74e5c-7a48-4f1d-a616-0ab9761dfd1e
- Endpoint: https://api.data.gov.in/resource/9ef74e5c-7a48-4f1d-a616-0ab9761dfd1e
- Query Params: api-key, format=json, limit, filters[commodity], filters[state]
- Parses 'modal_price' (₹/quintal) and converts to ₹/kg (/ 100).
- Caches live calls using st.cache_data(ttl=3600).
- Gracefully falls back to crop_economics.csv when key is missing or API call returns no matching records,
  returning MarketDataStatus.DEMO (never blending fake data as LIVE).
"""

from enum import Enum
import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Official Agmarknet Resource on data.gov.in: "Current Daily Price of Various Commodities for Various Markets (Mandi)"
DEFAULT_RESOURCE_ID = "9ef74e5c-7a48-4f1d-a616-0ab9761dfd1e"
AGMARKNET_API_BASE = "https://api.data.gov.in/resource/" + DEFAULT_RESOURCE_ID
CROP_ECONOMICS_CSV = "crop_economics.csv"


class MarketDataStatus(Enum):
    LIVE = 1
    DEMO = 2
    UNAVAILABLE = 3


# Commodity name mapping for Agmarknet
CROP_COMMODITY_MAP = {
    "Rice": "Rice",
    "Maize": "Maize",
    "Jute": "Jute",
    "Cotton": "Cotton",
    "Coconut": "Coconut",
    "Papaya": "Papaya",
    "Orange": "Orange",
    "Apple": "Apple",
    "Muskmelon": "Muskmelon",
    "Watermelon": "Watermelon",
    "Grapes": "Grapes",
    "Mango": "Mango",
    "Banana": "Banana",
    "Pomegranate": "Pomegranate",
    "Lentil": "Lentil (Masur)",
    "Blackgram": "Black Gram (Urd Beans)",
    "Mungbean": "Green Gram (Moong)",
    "Mothbeans": "Moth Dal",
    "Pigeonpeas": "Arhar (Tur/Red Gram)",
    "Kidneybeans": "Rajmah",
    "Chickpea": "Bengal Gram(Gram)(Whole)",
    "Coffee": "Coffee",
}


def get_market_api_key() -> str:
    """Retrieve API key dynamically from environment."""
    load_dotenv()
    return os.getenv("MARKET_API_KEY") or os.getenv("DATA_GOV_IN_API_KEY") or os.getenv("AGMARKNET_API_KEY") or ""


def get_market_price(crop_name: str, state_name: str = None) -> dict:
    """Fetch live mandi market price from data.gov.in Agmarknet API.

    Returns dict on success:
    {
        'price_per_kg': float,
        'modal_price_quintal': float,
        'market': str,
        'state': str,
        'district': str,
        'arrival_date': str,
        'commodity': str,
        'source': 'data.gov.in Agmarknet'
    }
    Returns None if key missing, API call fails, or 0 records found.
    """
    api_key = get_market_api_key()
    if not api_key:
        return None

    api_url = os.getenv("MARKET_API_URL") or AGMARKNET_API_BASE
    commodity = CROP_COMMODITY_MAP.get(crop_name.title(), crop_name.title())

    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 10,
        "filters[commodity]": commodity,
    }
    if state_name:
        params["filters[state]"] = state_name

    try:
        resp = requests.get(api_url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        records = data.get("records", [])
        if not records:
            # Fallback search with raw crop name
            if commodity != crop_name.title():
                params["filters[commodity]"] = crop_name.title()
                resp2 = requests.get(api_url, params=params, timeout=10)
                if resp2.status_code == 200:
                    records = resp2.json().get("records", [])

        if not records:
            return None

        for rec in records:
            raw_modal = rec.get("modal_price")
            if raw_modal:
                try:
                    modal_p = float(raw_modal)
                    if modal_p > 0:
                        price_kg = round(modal_p / 100.0, 2)
                        return {
                            "price_per_kg": price_kg,
                            "modal_price_quintal": modal_p,
                            "market": rec.get("market", "APMC Market"),
                            "state": rec.get("state", state_name or "India"),
                            "district": rec.get("district", "N/A"),
                            "arrival_date": rec.get("arrival_date", "Today"),
                            "commodity": rec.get("commodity", commodity),
                            "source": "data.gov.in Agmarknet",
                        }
                except ValueError:
                    continue

        return None
    except Exception:
        return None


def get_bulk_market_prices(state_name: str = None) -> dict:
    """Fetch all mandi market prices for a state (or national) in ONE single API request.

    Returns dict mapping crop_name (Title case) -> dict of market info, or {} if failed/no key.
    """
    api_key = get_market_api_key()
    if not api_key:
        return {}

    api_url = os.getenv("MARKET_API_URL") or AGMARKNET_API_BASE
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 500,
    }
    if state_name:
        params["filters[state]"] = state_name

    try:
        resp = requests.get(api_url, params=params, timeout=3)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        records = data.get("records", [])
        if not records:
            return {}

        commodity_to_crop = {v.lower(): k for k, v in CROP_COMMODITY_MAP.items()}

        price_map = {}
        for rec in records:
            comm = str(rec.get("commodity", "")).strip().lower()
            crop_name = commodity_to_crop.get(comm)
            if not crop_name:
                for c_name in CROP_COMMODITY_MAP:
                    if c_name.lower() in comm or comm in c_name.lower():
                        crop_name = c_name
                        break
            if not crop_name or crop_name in price_map:
                continue

            raw_modal = rec.get("modal_price")
            if raw_modal:
                try:
                    modal_p = float(raw_modal)
                    if modal_p > 0:
                        price_kg = round(modal_p / 100.0, 2)
                        price_map[crop_name.title()] = {
                            "price_per_kg": price_kg,
                            "modal_price_quintal": modal_p,
                            "market": rec.get("market", "APMC Market"),
                            "state": rec.get("state", state_name or "India"),
                            "district": rec.get("district", "N/A"),
                            "arrival_date": rec.get("arrival_date", "Today"),
                            "commodity": rec.get("commodity", comm),
                            "source": "data.gov.in Agmarknet",
                        }
                except ValueError:
                    continue
        return price_map
    except Exception:
        return {}


# Streamlit Caching Wrapper (1 Hour TTL)
try:
    import streamlit as st

    @st.cache_data(ttl=3600)
    def cached_get_market_price(crop_name: str, state_name: str = None):
        return get_market_price(crop_name, state_name=state_name)

    @st.cache_data(ttl=3600)
    def cached_get_bulk_market_prices(state_name: str = None):
        return get_bulk_market_prices(state_name=state_name)
except Exception:
    def cached_get_market_price(crop_name: str, state_name: str = None):
        return get_market_price(crop_name, state_name=state_name)

    def cached_get_bulk_market_prices(state_name: str = None):
        return get_bulk_market_prices(state_name=state_name)


import functools


@functools.lru_cache(maxsize=128)
def _read_local_price(crop_name: str) -> float:
    """Read demo market price per kg from crop_economics.csv."""
    try:
        if not os.path.exists(CROP_ECONOMICS_CSV):
            return None
        df = pd.read_csv(CROP_ECONOMICS_CSV)
        df.columns = [c.strip().lower() for c in df.columns]
        df['crop'] = df['crop'].str.strip().str.title()
        row = df[df['crop'] == crop_name.title()]
        if row.empty:
            return None
        price_col = next((c for c in df.columns if 'market_price' in c), 'market_price_per_kg')
        return float(row[price_col].values[0])
    except Exception:
        return None


def get_market_price_for_crop(crop_name: str, location_meta: dict = None, preloaded_map: dict = None):
    """Retrieve market price for crop.

    Returns tuple: (price_per_kg, MarketDataStatus)
    If live API succeeds -> returns (price, MarketDataStatus.LIVE)
    If live API fails or key missing -> falls back to crop_economics.csv and returns (demo_price, MarketDataStatus.DEMO)
    """
    state_name = None
    if location_meta and isinstance(location_meta, dict):
        state_name = location_meta.get('state')

    # Check preloaded bulk market map first
    if preloaded_map and isinstance(preloaded_map, dict):
        live_info = preloaded_map.get(crop_name.title())
        if live_info and live_info.get("price_per_kg"):
            return (live_info["price_per_kg"], MarketDataStatus.LIVE)

    # Try live price lookup
    live_info = cached_get_market_price(crop_name, state_name=state_name)
    if live_info and live_info.get("price_per_kg"):
        return (live_info["price_per_kg"], MarketDataStatus.LIVE)

    # Fallback: demo CSV
    demo_price = _read_local_price(crop_name)
    if demo_price is not None:
        return (demo_price, MarketDataStatus.DEMO)

    return (None, MarketDataStatus.UNAVAILABLE)


def debug_market_api(crop_name: str = "Rice", state_name: str = None):
    """Debug diagnostic helper function to inspect data.gov.in Agmarknet API response."""
    print("=== MARKET API DIAGNOSTIC CHECK ===")
    key = get_market_api_key()
    print(f"1. MARKET_API_KEY Found: {'YES (' + key[:6] + '...)' if key else 'NO (Key is missing/empty in .env)'}")

    if not key:
        print("   Diagnostic Result: Skipped API call because no key was found.")
        print("   Solution: Add MARKET_API_KEY=your_key_here to .env file.")
        return

    url = os.getenv("MARKET_API_URL") or AGMARKNET_API_BASE
    commodity = CROP_COMMODITY_MAP.get(crop_name.title(), crop_name.title())
    params = {
        "api-key": key,
        "format": "json",
        "limit": 5,
        "filters[commodity]": commodity,
    }
    if state_name:
        params["filters[state]"] = state_name

    print(f"2. Target API Endpoint: {url}")
    print(f"3. Query Commodity Filter: '{commodity}'")

    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"4. HTTP Response Code: {resp.status_code}")
        if resp.status_code == 200:
            payload = resp.json()
            records = payload.get("records", [])
            print(f"5. Total Records Returned: {len(records)}")
            if records:
                sample = records[0]
                print("6. Sample Mandi Record:")
                print(f"   - Market: {sample.get('market')}, State: {sample.get('state')}")
                print(f"   - Modal Price (₹/Quintal): {sample.get('modal_price')}")
                print(f"   - Arrival Date: {sample.get('arrival_date')}")
                res = get_market_price(crop_name, state_name=state_name)
                print(f"7. Parsed Live Price (₹/kg): ₹{res['price_per_kg'] if res else 'N/A'}")
            else:
                print("   Diagnostic Note: API returned 0 matching records for this commodity filter.")
        else:
            print(f"   Error Details: {resp.text[:200]}")
    except Exception as e:
        print(f"   HTTP Request Failed: {e}")
    print("===================================\n")


if __name__ == "__main__":
    debug_market_api("Rice")
