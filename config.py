"""config.py
Central configuration for decision-support weights and feature toggles.
Do not store API keys here; use environment variables instead.
"""
import os

MODEL_PATH = os.getenv('MODEL_PATH', 'crop_model.pkl')

# Weather cache TTL in seconds (used in Streamlit caching in app where appropriate)
WEATHER_CACHE_TTL = int(os.getenv('WEATHER_CACHE_TTL', '600'))  # 10 minutes
# Forecast cache TTL (longer than current weather)
FORECAST_CACHE_TTL = int(os.getenv('FORECAST_CACHE_TTL', '1800'))  # 30 minutes

# Whether UI should allow manual weather fallback when live weather fails
WEATHER_FALLBACK_ALLOWED = True

# Effective rainfall floor (mm) when reliable irrigation (Canal, Borewell, Drip/Sprinkler) is present.
# Note: This is an illustrative heuristic floor to adjust model inputs when natural rainfall is low,
# not a scientifically derived agronomic figure, and can be configured as needed.
IRRIGATION_EFFECTIVE_RAINFALL_MM = float(os.getenv('IRRIGATION_EFFECTIVE_RAINFALL_MM', '150.0'))

# Decision weights (explainable and configurable)
# Default weights sum to exactly 1.0 (0.35 + 0.20 + 0.15 + 0.05 + 0.15 + 0.10 = 1.00)
DECISION_WEIGHTS = {
    'model': float(os.getenv('WEIGHT_MODEL', 0.35)),
    'soil': float(os.getenv('WEIGHT_SOIL', 0.20)),
    'weather': float(os.getenv('WEIGHT_WEATHER', 0.15)),
    'season': float(os.getenv('WEIGHT_SEASON', 0.05)),
    'profit': float(os.getenv('WEIGHT_PROFIT', 0.15)),
    'risk': float(os.getenv('WEIGHT_RISK', 0.10)),
}


def get_normalized_weights(raw_weights: dict = None) -> dict:
    """Return decision weights normalized so their sum equals exactly 1.0.

    This ensures that even if user overrides weights via environment variables,
    the decision scoring engine maintains a calibrated 0-100 scale.
    """
    weights = raw_weights.copy() if raw_weights else DECISION_WEIGHTS.copy()
    total = sum(weights.values())
    if total <= 0:
        # Fallback to balanced default
        return {
            'model': 0.35,
            'soil': 0.20,
            'weather': 0.15,
            'season': 0.05,
            'profit': 0.15,
            'risk': 0.10,
        }
    return {k: v / total for k, v in weights.items()}


# 6 Tamil Nadu crops integrated using ICAR/TNAU agronomic reference ranges
REFERENCE_RANGE_CROPS = [
    "sugarcane", "groundnut", "cumbu", "ragi", "turmeric", "cashew",
    "pearl millet", "finger millet"
]

REFERENCE_RANGE_DISCLAIMER = (
    "Sugarcane, Groundnut, Pearl Millet (Cumbu), Finger Millet (Ragi), Turmeric, and Cashew "
    "are included using general agronomic reference ranges (ICAR/TNAU), not measured field data "
    "like the original 22 crops. Recommendations for these 6 crops should be treated as less precise reference-range estimates."
)


# Published agronomic minimum water/rainfall requirements (mm) across full crop cycle (ICAR / TNAU / FAO reference data)
CROP_MIN_WATER_REQUIREMENTS = {
    "sugarcane": 1500.0,
    "rice": 1000.0,
    "banana": 1200.0,
    "coconut": 1000.0,
    "papaya": 1000.0,
    "jute": 1000.0,
    "turmeric": 1000.0,
    "coffee": 1000.0,
    "apple": 1000.0,
    "grapes": 600.0,
    "pomegranate": 500.0,
    "mango": 750.0,
    "orange": 750.0,
    "cotton": 600.0,
    "maize": 500.0,
    "cashew": 800.0,
    "groundnut": 450.0,
    "ragi": 500.0,
    "finger millet": 500.0,
    "chickpea": 400.0,
    "lentil": 350.0,
    "blackgram": 400.0,
    "pigeonpeas": 600.0,
    "kidneybeans": 450.0,
    "mungbean": 350.0,
    "cumbu": 300.0,
    "pearl millet": 300.0,
    "mothbeans": 250.0,
    "watermelon": 400.0,
    "muskmelon": 350.0,
}


def get_crop_min_water_requirement(crop_name: str) -> float:
    """Return the published ICAR/TNAU minimum water requirement threshold (mm) for a crop."""
    c_lower = str(crop_name).strip().lower()
    return CROP_MIN_WATER_REQUIREMENTS.get(c_lower, 150.0)


# Geographic & altitude suitability restrictions dictionary.
# Note: This list is a reasonable starting point based on known growing regions (hill/coastal climate requirements),
# not an exhaustive or officially verified government list — it can be refined if additional districts are identified.
CROP_GEOGRAPHIC_RESTRICTIONS = {
    "coffee": {
        "allowed_districts": [
            "Nilgiris", "Kodaikanal", "Dindigul", "Coimbatore",
            "Theni", "Anamalai"
        ],
        "reason": "Coffee requires high-altitude hill climate (typically 600-1500m+ elevation) found mainly in Tamil Nadu's Western Ghats hill tracts."
    },
    "cashew": {
        "allowed_districts": [
            "Kanyakumari", "Cuddalore", "Villupuram", "Pudukkottai",
            "Ramanathapuram", "Thoothukudi"
        ],
        "reason": "Cashew grows best in coastal/sandy soil regions."
    }
}


def check_crop_geographic_eligibility(crop_name: str, location_meta: dict | None) -> tuple[bool, str | None]:
    """Check if a crop is geographically eligible for the given location metadata.

    Returns:
    - (True, None) if crop is eligible or unrestricted, or if location/district is not resolved.
    - (False, reason_str) if crop is restricted and location district does NOT match allowed_districts.
    """
    c_lower = str(crop_name).strip().lower()
    if c_lower not in CROP_GEOGRAPHIC_RESTRICTIONS:
        return True, None

    # If location is not set, manual mode without place info, or no display_name/district resolved
    if not location_meta or not isinstance(location_meta, dict):
        return True, None

    # Gather all location text representation fields for partial matching
    loc_fields = [
        str(location_meta.get("display_name", "")),
        str(location_meta.get("district", "")),
        str(location_meta.get("city", "")),
        str(location_meta.get("name", "")),
        str(location_meta.get("admin1", "")),
        str(location_meta.get("admin2", "")),
        str(location_meta.get("state", "")),
    ]

    loc_text_combined = " ".join(f for f in loc_fields if f and f != "None" and f != "N/A").lower()

    # If location text is empty or generic manual placeholder without district info
    if not loc_text_combined or loc_text_combined.startswith("manual ("):
        return True, None

    restriction_info = CROP_GEOGRAPHIC_RESTRICTIONS[c_lower]
    allowed_districts = restriction_info["allowed_districts"]
    reason = restriction_info["reason"]

    # Check case-insensitive partial match for any allowed district
    for dist in allowed_districts:
        if dist.lower() in loc_text_combined:
            return True, None

    return False, reason



