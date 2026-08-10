"""risk_engine.py
Compute a simple, transparent risk level (LOW/MEDIUM/HIGH) given soil,
weather, season and economics. Returns (risk_str, reasons_list).
"""

def compute_risk(crop_name: str, soil_report: dict, weather: dict, econ: dict, market_status_str: str = "DEMO"):
    reasons = []
    score = 0.0

    # Soil-based penalties
    soil_score = soil_report.get('score', 100)
    if soil_score < 40:
        reasons.append('Low overall soil health score (<40/100)')
        score += 2.0
    elif soil_score < 60:
        reasons.append('Moderate overall soil health score (40-60/100)')
        score += 1.0
    else:
        score -= 0.5

    # pH concerns
    for d in soil_report.get('details', []):
        if 'Acidic' in d or 'Alkaline' in d:
            reasons.append('Soil pH is outside ideal range (5.5 - 8.0)')
            score += 1.0

    # Weather penalties
    temp = weather.get('temperature')
    rain = weather.get('rainfall')
    if temp is not None:
        if temp < 5 or temp > 45:
            reasons.append('Extreme temperature conditions')
            score += 2.0
        elif temp < 15 or temp > 40:
            reasons.append('Sub-optimal temperature for peak crop growth')
            score += 1.0

    if rain is not None:
        if rain > 200:
            reasons.append('Very high recent rainfall — elevated waterlogging risk')
            score += 1.5
        elif rain < 5:
            reasons.append('Very low recent rainfall — drought / irrigation dependency risk')
            score += 1.0

    # Economic: low profit increases risk
    profit = econ.get('profit', 0)
    cost = econ.get('cost', 0)
    if cost > 0 and profit / (cost + 1) < 0.05:
        reasons.append('Low estimated profitability (< 5% ROI)')
        score += 1.0

    # Season
    if not econ.get('season_valid', False):
        reasons.append('Off-season planting window for this crop')
        score += 1.0

    # Market status check
    if str(market_status_str).upper() in ("DEMO", "ESTIMATED"):
        reasons.append('Market price is based on local demo dataset (unverified live APMC price)')
        score += 0.5

    # Map score to risk
    if score >= 4.0:
        risk = 'HIGH'
    elif score >= 2.0:
        risk = 'MEDIUM'
    else:
        risk = 'LOW'

    if not reasons and risk == 'LOW':
        reasons.append('Favorable soil, weather, seasonal, and economic conditions')

    return risk, reasons

