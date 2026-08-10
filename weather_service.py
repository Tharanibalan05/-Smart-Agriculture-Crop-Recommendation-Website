"""weather_service.py

Live geocoding, current weather, and daily forecast using Open-Meteo API:
- Geocoding API: https://geocoding-api.open-meteo.com/v1/search
- Forecast & Weather API: https://api.open-meteo.com/v1/forecast
- Reverse Geocoding: https://nominatim.openstreetmap.org/reverse

This module requires NO API keys. It returns real-time data or None/empty list on failure.
"""

from datetime import datetime
import requests

OPENMETEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPENMETEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {"User-Agent": "SmartCropDecisionSupport/1.0 (local)"}

# WMO Weather interpretation codes (WW) from Open-Meteo
WMO_WEATHER_MAP = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Freezing Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    66: "Light Freezing Rain",
    67: "Heavy Freezing Rain",
    71: "Slight Snow",
    73: "Moderate Snow",
    75: "Heavy Snow",
    77: "Snow Grains",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    85: "Slight Snow Showers",
    86: "Heavy Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm With Slight Hail",
    99: "Thunderstorm With Heavy Hail",
}


def wmo_code_to_condition(code: int) -> str:
    """Convert WMO numerical weather code to readable string description."""
    try:
        return WMO_WEATHER_MAP.get(int(code), "Clear Sky")
    except Exception:
        return "Clear Sky"


def search_locations(query: str) -> list[dict]:
    """Search Indian locations using Open-Meteo geocoding API for live autocomplete.

    Returns a list of dicts:
    [{'label': 'Nagapattinam, Tamil Nadu, India', 'name': 'Nagapattinam', 'lat': 10.7667, 'lon': 79.8333, 'admin1': 'Tamil Nadu', 'country': 'India', 'display_name': '...'}, ...]
    """
    if not query or len(str(query).strip()) < 2:
        return []

    q_clean = str(query).strip()
    params = {
        "name": q_clean,
        "count": 10,
        "language": "en",
        "format": "json"
    }

    try:
        resp = requests.get(OPENMETEO_GEOCODE_URL, params=params, headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return []

        out = []
        for r in results:
            country = r.get("country", "")
            country_code = r.get("country_code", "")
            if country_code.upper() == "IN" or country.lower() == "india":
                name = r.get("name", "")
                admin1 = r.get("admin1") or r.get("admin2") or "India"
                lat = float(r.get("latitude"))
                lon = float(r.get("longitude"))
                
                label = f"{name}, {admin1}, India" if admin1 and admin1 != name else f"{name}, India"
                out.append({
                    "label": label,
                    "name": name,
                    "lat": lat,
                    "lon": lon,
                    "admin1": admin1,
                    "city": name,
                    "state": admin1,
                    "country": "India",
                    "display_name": label,
                    "is_manual": False
                })
        return out
    except Exception:
        return []


def get_coordinates(query: str):
    """Geocode free-text query using Open-Meteo with fallback to Nominatim (OpenStreetMap).

    Returns a dict: {lat, lon, display_name, city, state, country, postcode}
    or None if not found.
    """
    if not query or not str(query).strip():
        return None

    # First try Open-Meteo search
    open_meteo_res = search_locations(query)
    if open_meteo_res:
        return open_meteo_res[0]

    # Fallback to Nominatim OSM
    try:
        params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
        resp = requests.get(NOMINATIM_SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None

        item = data[0]
        addr = item.get("address", {})
        return {
            "lat": float(item["lat"]),
            "lon": float(item["lon"]),
            "display_name": item.get("display_name"),
            "city": addr.get("city") or addr.get("town") or addr.get("village"),
            "district": addr.get("county") or addr.get("region"),
            "state": addr.get("state"),
            "country": addr.get("country"),
            "postcode": addr.get("postcode"),
            "is_manual": False,
        }
    except Exception:
        return None


def reverse_geocode(lat: float, lon: float) -> dict:
    """Reverse geocode (lat, lon) coordinates to place name metadata."""
    try:
        params = {"lat": lat, "lon": lon, "format": "json", "addressdetails": 1}
        resp = requests.get(NOMINATIM_REVERSE_URL, params=params, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            item = resp.json()
            addr = item.get("address", {})
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or "Detected Location"
            state = addr.get("state", "N/A")
            country = addr.get("country", "India")
            display_name = item.get("display_name") or f"{city}, {state}, {country}"
            return {
                "lat": float(lat),
                "lon": float(lon),
                "display_name": display_name,
                "city": city,
                "state": state,
                "country": country,
                "is_manual": False,
                "is_gps": True,
            }
    except Exception:
        pass

    return {
        "lat": float(lat),
        "lon": float(lon),
        "display_name": f"Detected GPS ({float(lat):.4f}, {float(lon):.4f})",
        "city": "GPS Location",
        "state": "N/A",
        "country": "India",
        "is_manual": False,
        "is_gps": True,
    }


def get_current_weather(lat: float, lon: float) -> dict:
    """Fetch current live weather from Open-Meteo API (requires NO API key).

    Returns a dictionary with keys:
    temperature, feels_like, humidity, rainfall (mm), wind_speed, pressure, clouds, condition, timestamp
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,surface_pressure,cloud_cover",
        "wind_speed_unit": "ms",
    }
    try:
        resp = requests.get(OPENMETEO_FORECAST_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        curr = data.get("current", {})
        if not curr:
            return None

        temp = float(curr.get("temperature_2m", 25.0))
        hum = float(curr.get("relative_humidity_2m", 70.0))
        precip = float(curr.get("precipitation", 0.0))
        wind_ms = float(curr.get("wind_speed_10m", 0.0))
        press = float(curr.get("surface_pressure", 1013.0))
        clouds = int(curr.get("cloud_cover", 0))
        w_code = int(curr.get("weather_code", 0))

        return {
            "temperature": round(temp, 1),
            "feels_like": round(temp, 1),
            "humidity": round(hum, 1),
            "pressure": round(press, 1),
            "wind_speed": round(wind_ms, 1),
            "rainfall": round(precip, 1),
            "clouds": clouds,
            "condition": wmo_code_to_condition(w_code),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
    except Exception:
        return None


def get_weather_forecast(lat: float, lon: float, days: int = 3) -> list:
    """Return a 3-day daily forecast from Open-Meteo API (requires NO API key).

    Returns a list of dicts:
    [{'date': '2026-08-09', 'temp_min': 22.0, 'temp_max': 32.0, 'pop': None, 'rain': 1.5, 'condition': 'Partly Cloudy'}, ...]
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
        "forecast_days": days,
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPENMETEO_FORECAST_URL, params=params, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precips = daily.get("precipitation_sum", [])
        w_codes = daily.get("weather_code", [])

        out = []
        for i in range(min(len(dates), days)):
            out.append({
                "date": dates[i],
                "temp_min": min_temps[i] if i < len(min_temps) else None,
                "temp_max": max_temps[i] if i < len(max_temps) else None,
                "pop": None,
                "rain": precips[i] if i < len(precips) else 0.0,
                "condition": wmo_code_to_condition(w_codes[i]) if i < len(w_codes) else "Clear Sky",
            })
        return out
    except Exception:
        return []


def get_seasonal_climate_average(lat: float, lon: float, season_name: str) -> dict:
    """Fetch real historical weather from Open-Meteo Archive API across the last 3 available years
    (2023, 2024, 2025) for the selected agricultural season.

    Supported seasons:
    - Kharif (Jun-Oct): June 1 to October 31
    - Rabi (Oct-Mar): October 1 to March 31
    - Zaid (Mar-Jun): March 1 to June 30

    Returns a dict with average temperature (°C), average relative humidity (%),
    and average total seasonal rainfall (mm), or None if fetching fails.
    """
    if not lat or not lon or not season_name or "Current" in season_name:
        return None

    years = [2023, 2024, 2025]
    seasonal_precip_sums = []
    daily_temps = []
    daily_hums = []
    humidity_available = True

    try:
        for y in years:
            if "Kharif" in season_name:
                s_date, e_date = f"{y}-06-01", f"{y}-10-31"
            elif "Rabi" in season_name:
                s_date, e_date = f"{y-1}-10-01", f"{y}-03-31"
            elif "Zaid" in season_name:
                s_date, e_date = f"{y}-03-01", f"{y}-06-30"
            else:
                return None

            params = {
                "latitude": float(lat),
                "longitude": float(lon),
                "start_date": s_date,
                "end_date": e_date,
                "daily": "temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean",
                "timezone": "auto",
            }
            resp = requests.get(OPENMETEO_ARCHIVE_URL, params=params, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            daily = data.get("daily", {})
            if not daily:
                return None

            t_arr = [float(v) for v in daily.get("temperature_2m_mean", []) if v is not None]
            h_arr = [float(v) for v in daily.get("relative_humidity_2m_mean", []) if v is not None]
            p_arr = [float(v) for v in daily.get("precipitation_sum", []) if v is not None]

            if t_arr:
                daily_temps.extend(t_arr)
            if h_arr:
                daily_hums.extend(h_arr)
            else:
                humidity_available = False
            if p_arr:
                seasonal_precip_sums.append(sum(p_arr))

        if not daily_temps or not seasonal_precip_sums:
            return None

        avg_temp = round(float(sum(daily_temps) / len(daily_temps)), 1)
        avg_hum = round(float(sum(daily_hums) / len(daily_hums)), 1) if daily_hums else None
        avg_rain = round(float(sum(seasonal_precip_sums) / len(seasonal_precip_sums)), 1)

        return {
            "season_name": season_name,
            "temperature": avg_temp,
            "humidity": avg_hum,
            "humidity_available": humidity_available and (avg_hum is not None),
            "rainfall": avg_rain,
            "years_analyzed": years,
            "year_rainfall_breakdown": [round(x, 1) for x in seasonal_precip_sums],
            "is_seasonal_historical": True,
        }
    except Exception:
        return None

