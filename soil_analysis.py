"""soil_analysis.py
Simple rule-based soil screening. Returns a transparent score (0-100)
and a details dict explaining deficiencies. This is explicitly an
"AI-assisted soil screening based on entered values" and not a lab report.
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


def analyze_soil(N, P, K, ph, soil_type=None):
    details = []
    deficiencies = []
    strengths = []
    recommendations = []
    score = 100

    # Nitrogen
    if N < 60:
        n_status = "Low"
        deficiencies.append("Low Nitrogen (N)")
        recommendations.append("Apply Nitrogen-rich fertilizer such as Urea (46% N).")
        score -= 25
    elif N < 90:
        n_status = "Moderate"
        strengths.append("Moderate Nitrogen (N) levels")
        score -= 10
    else:
        n_status = "Optimal"
        strengths.append("Adequate Nitrogen (N)")

    # Phosphorus
    if P < 30:
        p_status = "Low"
        deficiencies.append("Low Phosphorus (P)")
        recommendations.append("Apply Phosphorus fertilizer such as DAP (Di-ammonium Phosphate) or SSP.")
        score -= 20
    elif P < 50:
        p_status = "Moderate"
        strengths.append("Moderate Phosphorus (P) levels")
        score -= 8
    else:
        p_status = "Optimal"
        strengths.append("Adequate Phosphorus (P)")

    # Potassium
    if K < 30:
        k_status = "Low"
        deficiencies.append("Low Potassium (K)")
        recommendations.append("Apply Potassium fertilizer such as MOP (Muriate of Potash).")
        score -= 20
    elif K < 50:
        k_status = "Moderate"
        strengths.append("Moderate Potassium (K) levels")
        score -= 8
    else:
        k_status = "Optimal"
        strengths.append("Adequate Potassium (K)")

    # pH
    if ph < 5.5:
        ph_status = "Acidic"
        deficiencies.append("Acidic Soil pH (< 5.5)")
        recommendations.append("Apply Agricultural Lime / Calcium Carbonate to increase soil pH.")
        score -= 15
    elif ph > 8.0:
        ph_status = "Alkaline"
        deficiencies.append("Alkaline Soil pH (> 8.0)")
        recommendations.append("Apply Gypsum or Agricultural Sulfur to lower soil pH.")
        score -= 15
    else:
        ph_status = "Optimal"
        strengths.append("Soil pH is within typical agricultural range (5.5 - 8.0)")

    # Soil type specific agronomic screening adjustments
    if soil_type and str(soil_type).strip() != "Unknown":
        st_clean = str(soil_type).strip()

        if "alluvial" in st_clean.lower():
            strengths.append("Alluvial soil — high native fertility and good drainage")
        elif "black" in st_clean.lower() or "regur" in st_clean.lower():
            strengths.append("Black Regur soil — excellent moisture retention & clay mineral content")
        elif "red" in st_clean.lower():
            deficiencies.append("Red & Yellow soil — porous structure; prone to low organic humus")
            recommendations.append("Incorporate farmyard manure or green compost to enhance humus.")
        elif "laterite" in st_clean.lower():
            deficiencies.append("Laterite soil — highly leached with low organic nutrient holding capacity")
            recommendations.append("Apply slow-release fertilizers and organic compost to prevent leaching.")
            score -= 5
        elif "arid" in st_clean.lower() or "desert" in st_clean.lower() or "sandy" in st_clean.lower():
            deficiencies.append("Arid / Desert soil — coarse sandy texture with low water holding capacity")
            recommendations.append("Incorporate organic compost/biochar and practice drip irrigation.")
            score -= 5
        elif "saline" in st_clean.lower() or "alkaline" in st_clean.lower():
            deficiencies.append("Saline & Alkaline soil — high soluble salt concentration")
            recommendations.append("Apply Gypsum and ensure leaching with clean irrigation water.")
            score -= 10
        elif "peaty" in st_clean.lower() or "marshy" in st_clean.lower():
            deficiencies.append("Peaty & Marshy soil — high organic matter but prone to waterlogging")
            recommendations.append("Construct field drainage channels to prevent root asphyxiation.")
            score -= 5
        elif "forest" in st_clean.lower() or "mountain" in st_clean.lower():
            strengths.append("Forest & Mountain soil — rich in organic topsoil humus")
            recommendations.append("Implement terrace bunding to protect topsoil from slope erosion.")

    details.extend([f"Nitrogen: {n_status}", f"Phosphorus: {p_status}", f"Potassium: {k_status}", f"pH: {ph_status}"])

    if not recommendations:
        recommendations.append("Nutrient balance is optimal. Maintain current organic soil management practices.")

    score = max(0, min(100, score))
    return {
        "score": score,
        "n_status": n_status,
        "p_status": p_status,
        "k_status": k_status,
        "ph_status": ph_status,
        "details": details,
        "deficiencies": deficiencies,
        "strengths": strengths,
        "recommendations": recommendations,
        "disclaimer": "AI-assisted soil screening based on entered values. This is not a laboratory soil test."
    }
