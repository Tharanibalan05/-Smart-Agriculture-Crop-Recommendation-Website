"""soil_analysis.py
Rule-based 100-point Soil Health Screening Model.
Uses a weighted component structure (N: 20, P: 20, K: 20, pH: 25, Soil Type: 15)
with continuous piecewise-linear nutrient scoring to eliminate score cliffs.
Returns transparent breakdown, health category, deficiencies, and recommendations.
This is explicitly an "AI-assisted soil screening based on entered values" and not a lab report.
"""

INDIAN_SOIL_TYPES = [
    "Unknown",
    "Alluvial Soil",
    "Black Soil (Regur)",
    "Red & Yellow Soil",
    "Laterite Soil",
    "Arid / Desert Soil",
    "Saline & Alkaline Soil",
    "Peaty & Marshy Soil",
    "Forest & Mountain Soil",
]

# Configurable Weights
SOIL_HEALTH_WEIGHTS = {
    "nitrogen": 20,
    "phosphorus": 20,
    "potassium": 20,
    "ph": 25,
    "soil_type": 15,
}

# Configurable Threshold Structures
NITROGEN_SCORING_CONFIG = {
    "bands": [
        {"max": 30, "y_start": 0.0, "y_end": 6.0},
        {"max": 60, "y_start": 6.0, "y_end": 14.0},
        {"max": 90, "y_start": 14.0, "y_end": 19.0},
        {"max": 120, "score": 20.0},
    ],
    "max_score": 20.0,
}

PHOSPHORUS_SCORING_CONFIG = {
    "bands": [
        {"max": 15, "y_start": 0.0, "y_end": 6.0},
        {"max": 30, "y_start": 6.0, "y_end": 13.0},
        {"max": 50, "y_start": 13.0, "y_end": 18.0},
        {"max": 80, "score": 20.0},
    ],
    "max_score": 20.0,
}

POTASSIUM_SCORING_CONFIG = {
    "bands": [
        {"max": 15, "y_start": 0.0, "y_end": 6.0},
        {"max": 30, "y_start": 6.0, "y_end": 13.0},
        {"max": 50, "y_start": 13.0, "y_end": 18.0},
        {"max": 80, "score": 20.0},
    ],
    "max_score": 20.0,
}

PH_SCORING_CONFIG = {
    "optimal_min": 6.0,
    "optimal_max": 7.5,
    "max_score": 25.0,
}

SOIL_TYPE_SCORES = {
    "Alluvial Soil": 15.0,
    "Black Soil (Regur)": 15.0,
    "Red & Yellow Soil": 14.0,
    "Forest & Mountain Soil": 13.0,
    "Laterite Soil": 11.0,
    "Peaty & Marshy Soil": 11.0,
    "Arid / Desert Soil": 9.0,
    "Saline & Alkaline Soil": 7.0,
    "Unknown": 12.0,
}


def _interpolate(val, x1, y1, x2, y2):
    if x2 == x1:
        return float(y1)
    ratio = (val - x1) / (x2 - x1)
    return float(y1 + ratio * (y2 - y1))


def _score_nitrogen(n):
    n = max(0.0, float(n))
    if n < 30.0:
        return _interpolate(n, 0.0, 0.0, 30.0, 6.0)
    elif n < 60.0:
        return _interpolate(n, 30.0, 6.0, 60.0, 14.0)
    elif n < 90.0:
        return _interpolate(n, 60.0, 14.0, 90.0, 19.0)
    elif n <= 120.0:
        return 20.0
    else:
        # Gradually taper down for high nitrogen excess
        score = 20.0 - (n - 120.0) * (4.0 / 80.0)
        return max(10.0, score)


def _score_phosphorus(p):
    p = max(0.0, float(p))
    if p < 15.0:
        return _interpolate(p, 0.0, 0.0, 15.0, 6.0)
    elif p < 30.0:
        return _interpolate(p, 15.0, 6.0, 30.0, 13.0)
    elif p < 50.0:
        return _interpolate(p, 30.0, 13.0, 50.0, 18.0)
    elif p <= 80.0:
        return 20.0
    else:
        # Gradually taper down for excess phosphorus
        score = 20.0 - (p - 80.0) * (4.0 / 70.0)
        return max(10.0, score)


def _score_potassium(k):
    k = max(0.0, float(k))
    if k < 15.0:
        return _interpolate(k, 0.0, 0.0, 15.0, 6.0)
    elif k < 30.0:
        return _interpolate(k, 15.0, 6.0, 30.0, 13.0)
    elif k < 50.0:
        return _interpolate(k, 30.0, 13.0, 50.0, 18.0)
    elif k <= 80.0:
        return 20.0
    else:
        # Gradually taper down for excess potassium
        score = 20.0 - (k - 80.0) * (4.0 / 70.0)
        return max(10.0, score)


def _score_ph(ph):
    ph = float(ph)
    if ph < 3.0:
        return 2.0
    elif ph < 4.5:
        return _interpolate(ph, 3.0, 2.0, 4.5, 10.0)
    elif ph < 5.5:
        return _interpolate(ph, 4.5, 10.0, 5.5, 20.0)
    elif ph < 6.0:
        return _interpolate(ph, 5.5, 20.0, 6.0, 25.0)
    elif ph <= 7.5:
        return 25.0
    elif ph <= 8.0:
        return _interpolate(ph, 7.5, 25.0, 8.0, 21.0)
    elif ph <= 9.0:
        return _interpolate(ph, 8.0, 21.0, 9.0, 10.0)
    elif ph <= 11.0:
        return _interpolate(ph, 9.0, 10.0, 11.0, 2.0)
    else:
        return 2.0


def _score_soil_type(soil_type):
    if not soil_type or str(soil_type).strip() == "" or str(soil_type).strip() == "Unknown":
        return 12.0
    st_clean = str(soil_type).strip().lower()
    if "alluvial" in st_clean:
        return 15.0
    elif "black" in st_clean or "regur" in st_clean:
        return 15.0
    elif "red" in st_clean:
        return 14.0
    elif "forest" in st_clean or "mountain" in st_clean:
        return 13.0
    elif "laterite" in st_clean:
        return 11.0
    elif "peaty" in st_clean or "marshy" in st_clean:
        return 11.0
    elif "arid" in st_clean or "desert" in st_clean or "sandy" in st_clean:
        return 9.0
    elif "saline" in st_clean or "alkaline" in st_clean:
        return 7.0
    return 12.0


def get_health_category(score):
    score = float(score)
    if score >= 90.0:
        return "Excellent"
    elif score >= 75.0:
        return "Good"
    elif score >= 60.0:
        return "Moderate"
    elif score >= 40.0:
        return "Needs Improvement"
    else:
        return "Poor"


def analyze_soil(N, P, K, ph, soil_type=None):
    details = []
    deficiencies = []
    strengths = []
    recommendations = []

    # Calculate component scores
    n_score = _score_nitrogen(N)
    p_score = _score_phosphorus(P)
    k_score = _score_potassium(K)
    ph_score = _score_ph(ph)
    st_score = _score_soil_type(soil_type)

    raw_total = n_score + p_score + k_score + ph_score + st_score
    total_score = max(0.0, min(100.0, raw_total))
    final_score_int = int(round(total_score))

    # Nitrogen qualitative assessment
    if N < 60:
        n_status = "Low"
        deficiencies.append("Low Nitrogen (N)")
        recommendations.append("Apply Nitrogen-rich fertilizer such as Urea (46% N).")
    elif N < 90:
        n_status = "Moderate"
        strengths.append("Moderate Nitrogen (N) levels")
    else:
        n_status = "Optimal"
        strengths.append("Adequate Nitrogen (N)")

    # Phosphorus qualitative assessment
    if P < 30:
        p_status = "Low"
        deficiencies.append("Low Phosphorus (P)")
        recommendations.append("Apply Phosphorus fertilizer such as DAP (Di-ammonium Phosphate) or SSP.")
    elif P < 50:
        p_status = "Moderate"
        strengths.append("Moderate Phosphorus (P) levels")
    else:
        p_status = "Optimal"
        strengths.append("Adequate Phosphorus (P)")

    # Potassium qualitative assessment
    if K < 30:
        k_status = "Low"
        deficiencies.append("Low Potassium (K)")
        recommendations.append("Apply Potassium fertilizer such as MOP (Muriate of Potash).")
    elif K < 50:
        k_status = "Moderate"
        strengths.append("Moderate Potassium (K) levels")
    else:
        k_status = "Optimal"
        strengths.append("Adequate Potassium (K)")

    # pH qualitative assessment
    if ph < 5.5:
        ph_status = "Acidic"
        deficiencies.append("Acidic Soil pH (< 5.5)")
        recommendations.append("Apply Agricultural Lime / Calcium Carbonate to increase soil pH.")
    elif ph > 8.0:
        ph_status = "Alkaline"
        deficiencies.append("Alkaline Soil pH (> 8.0)")
        recommendations.append("Apply Gypsum or Agricultural Sulfur to lower soil pH.")
    else:
        ph_status = "Optimal"
        strengths.append("Soil pH is within typical agricultural range (5.5 - 8.0)")

    # Soil type agronomic qualitative notes
    if soil_type and str(soil_type).strip() != "Unknown":
        st_clean = str(soil_type).strip().lower()
        if "alluvial" in st_clean:
            strengths.append("Alluvial soil — high native fertility and good drainage")
        elif "black" in st_clean or "regur" in st_clean:
            strengths.append("Black Regur soil — excellent moisture retention & clay mineral content")
        elif "red" in st_clean:
            deficiencies.append("Red & Yellow soil — porous structure; prone to low organic humus")
            recommendations.append("Incorporate farmyard manure or green compost to enhance humus.")
        elif "laterite" in st_clean:
            deficiencies.append("Laterite soil — highly leached with low organic nutrient holding capacity")
            recommendations.append("Apply slow-release fertilizers and organic compost to prevent leaching.")
        elif "arid" in st_clean or "desert" in st_clean or "sandy" in st_clean:
            deficiencies.append("Arid / Desert soil — coarse sandy texture with low water holding capacity")
            recommendations.append("Incorporate organic compost/biochar and practice drip irrigation.")
        elif "saline" in st_clean or "alkaline" in st_clean:
            deficiencies.append("Saline & Alkaline soil — high soluble salt concentration")
            recommendations.append("Apply Gypsum and ensure leaching with clean irrigation water.")
        elif "peaty" in st_clean or "marshy" in st_clean:
            deficiencies.append("Peaty & Marshy soil — high organic matter but prone to waterlogging")
            recommendations.append("Construct field drainage channels to prevent root asphyxiation.")
        elif "forest" in st_clean or "mountain" in st_clean:
            strengths.append("Forest & Mountain soil — rich in organic topsoil humus")
            recommendations.append("Implement terrace bunding to protect topsoil from slope erosion.")

    details.extend([f"Nitrogen: {n_status}", f"Phosphorus: {p_status}", f"Potassium: {k_status}", f"pH: {ph_status}"])

    if not recommendations:
        recommendations.append("Nutrient balance is optimal. Maintain current organic soil management practices.")

    category = get_health_category(total_score)

    score_breakdown = {
        "Nitrogen": {"score": round(n_score, 2), "max": 20},
        "Phosphorus": {"score": round(p_score, 2), "max": 20},
        "Potassium": {"score": round(k_score, 2), "max": 20},
        "pH": {"score": round(ph_score, 2), "max": 25},
        "Soil Type": {"score": round(st_score, 2), "max": 15},
    }

    component_scores = {
        "nitrogen": round(n_score, 2),
        "phosphorus": round(p_score, 2),
        "potassium": round(k_score, 2),
        "ph": round(ph_score, 2),
        "soil_type": round(st_score, 2),
    }

    return {
        "score": final_score_int,
        "category": category,
        "score_breakdown": score_breakdown,
        "component_scores": component_scores,
        "n_status": n_status,
        "p_status": p_status,
        "k_status": k_status,
        "ph_status": ph_status,
        "details": details,
        "deficiencies": deficiencies,
        "strengths": strengths,
        "recommendations": recommendations,
        "disclaimer": "AI-assisted soil screening based on entered values. This is not a laboratory soil test.",
    }
