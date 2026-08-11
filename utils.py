import pandas as pd
from datetime import datetime

# Load crop economics data once
econ_df = pd.read_csv("crop_economics.csv")
# Normalize column names so we don't break if headers change case
econ_df.columns = [c.strip().lower() for c in econ_df.columns]
econ_df["crop"] = econ_df["crop"].str.strip().str.title()

# Indian cropping seasons -> the calendar months they're normally sown in
SEASON_MONTHS = {
    "kharif": [6, 7, 8, 9, 10],      # Jun - Oct (monsoon)
    "rabi": [10, 11, 12, 1, 2, 3],   # Oct - Mar (winter)
    "zaid": [3, 4, 5, 6],            # Mar - Jun (summer)
    "annual": list(range(1, 13)),    # grown/harvested year-round
}


def recommend_fertilizer(N, P, K, ph):
    """Return simple, rule-based fertilizer guidance from NPK + pH."""
    suggestions = []
    if N < 90:
        suggestions.append("Add Nitrogen fertilizer (e.g., Urea)")
    if P < 40:
        suggestions.append("Add Phosphorus fertilizer (e.g., DAP)")
    if K < 40:
        suggestions.append("Add Potassium fertilizer (e.g., MOP)")
    if ph < 6.0:
        suggestions.append("Add Lime to raise pH")
    elif ph > 7.5:
        suggestions.append("Add Sulfur / Gypsum to lower pH")

    if not suggestions:
        return "Soil nutrients look balanced — no extra fertilizer needed"
    return ", ".join(suggestions)


def is_season_valid(season_name, month=None):
    """Check whether the current (or given) month falls in the crop's season."""
    if month is None:
        month = datetime.now().month
    months = SEASON_MONTHS.get(str(season_name).strip().lower())
    if months is None:
        return False
    return month in months


def get_crop_profit_data(crop_name, prefer_live=False):
    """Look up economics for a predicted crop.

    Returns a tuple (econ_dict, status_str) where status_str is one of
    'LOCAL' (from local crop_economics.csv) or 'NO_DATA'.
    """
    crop_name = str(crop_name).strip().title()
    row = econ_df[econ_df["crop"] == crop_name]

    if row.empty:
        return ({
            "crop": crop_name,
            "season": "Unknown",
            "season_valid": False,
            "market_price": 0.0,
            "cost": 0.0,
            "yield": 0.0,
            "revenue": 0.0,
            "income": 0.0,
            "profit": 0.0,
            "roi": 0.0,
            "profit_margin": 0.0,
            "breakeven_yield": None,
            "profit_status": "No data",
        }, "NO_DATA")

    season = row["season"].values[0]
    mp_col = next((c for c in econ_df.columns if "market_price" in c), "market_price_per_kg")
    cost_col = next((c for c in econ_df.columns if "cost" in c), "cost_per_acre")
    yield_col = next((c for c in econ_df.columns if "yield" in c), "yield_per_acre_kg")

    market_price = float(row[mp_col].values[0]) if not pd.isna(row[mp_col].values[0]) else 0.0
    cost = float(row[cost_col].values[0]) if not pd.isna(row[cost_col].values[0]) else 0.0
    yield_kg = float(row[yield_col].values[0]) if not pd.isna(row[yield_col].values[0]) else 0.0

    revenue = market_price * yield_kg
    profit = revenue - cost
    roi = (profit / cost * 100.0) if cost > 0 else (100.0 if profit > 0 else 0.0)
    profit_margin = (profit / revenue * 100.0) if revenue > 0 else 0.0
    breakeven = round(cost / market_price, 1) if market_price > 0 else None

    econ = {
        "crop": crop_name,
        "season": season,
        "season_valid": is_season_valid(season),
        "market_price": market_price,
        "cost": cost,
        "yield": yield_kg,
        "revenue": revenue,
        "income": revenue,
        "profit": profit,
        "roi": round(roi, 1),
        "profit_margin": round(profit_margin, 1),
        "breakeven_yield": breakeven,
        "profit_status": "Profit" if profit > 0 else ("Break-even" if profit == 0 else "Loss"),
    }
    return (econ, "LOCAL")


def get_breakeven_yield(crop_name):
    """Minimum yield (kg/acre) needed at current market price to cover cost."""
    econ, status = get_crop_profit_data(crop_name)
    if econ["market_price"] <= 0:
        return None
    return round(econ["cost"] / econ["market_price"], 1)


# === Prediction history utilities ===
HISTORY_PATH = "prediction_history.csv"

HISTORY_COLUMNS = [
    'timestamp', 'user_email', 'location', 'latitude', 'longitude', 'N', 'P', 'K', 'ph',
    'temperature', 'humidity', 'rainfall', 'actual_rainfall', 'effective_rainfall', 'irrigation_type',
    'planning_season', 'weather_mode',
    'best_crop', 'confidence',
    'decision_score', 'market_price', 'market_status', 'estimated_yield',
    'revenue', 'cost', 'profit', 'roi', 'risk', 'soil_health_score'
]


def _normalize_history_file():
    """Reads legacy prediction_history.csv rows (which may have fewer columns from earlier versions)
    and rewrites the file with unified HISTORY_COLUMNS schema.
    """
    import os
    import csv
    import pandas as pd

    if not os.path.exists(HISTORY_PATH):
        return

    try:
        # Try clean read first
        df = pd.read_csv(HISTORY_PATH)
        for col in HISTORY_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[HISTORY_COLUMNS]
        df.to_csv(HISTORY_PATH, index=False)
    except Exception:
        # Handle rows with varying column counts due to schema evolution
        normalized_rows = []
        with open(HISTORY_PATH, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            headers = None
            for row in reader:
                if not row:
                    continue
                if headers is None:
                    headers = row
                    continue
                row_dict = {}
                for idx, val in enumerate(row):
                    if idx < len(headers):
                        row_dict[headers[idx]] = val
                normalized_rows.append(row_dict)

        df = pd.DataFrame(normalized_rows)
        for col in HISTORY_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df[HISTORY_COLUMNS]
        df.to_csv(HISTORY_PATH, index=False)


def append_prediction_history(row: dict = None, clear: bool = False, user_email: str = None):
    """Append a single prediction row (dict) to HISTORY_PATH as CSV.

    If clear=True and user_email is provided, clear ONLY that user's history records.
    If clear=True and user_email is None/empty, legacy complete wipe occurs.
    """
    import os
    import pandas as pd

    if clear:
        if user_email and str(user_email).strip():
            clear_user_history(user_email)
        else:
            try:
                if os.path.exists(HISTORY_PATH):
                    os.remove(HISTORY_PATH)
            except Exception:
                pass
        return

    if not row:
        return

    # Normalize existing file if schema evolved
    if os.path.exists(HISTORY_PATH):
        _normalize_history_file()

    df_row = pd.DataFrame([row])
    raw_email = row.get('user_email') or user_email or 'guest@local'
    df_row['user_email'] = str(raw_email).strip().lower()

    # Ensure all columns exist
    for c in HISTORY_COLUMNS:
        if c not in df_row.columns:
            df_row[c] = None

    # Reorder columns explicitly
    df_row = df_row[HISTORY_COLUMNS]

    if os.path.exists(HISTORY_PATH):
        df_row.to_csv(HISTORY_PATH, mode='a', header=False, index=False)
    else:
        df_row.to_csv(HISTORY_PATH, index=False)


def load_history(user_email: str = None):
    """Load history into a pandas DataFrame.

    If user_email is specified, filters records strictly by that user's email address.
    If user_email is None or empty, returns an empty DataFrame for security.
    """
    import os
    import pandas as pd

    if not os.path.exists(HISTORY_PATH):
        return pd.DataFrame(columns=HISTORY_COLUMNS)

    _normalize_history_file()

    try:
        df = pd.read_csv(HISTORY_PATH)
        for c in HISTORY_COLUMNS:
            if c not in df.columns:
                df[c] = None

        if not user_email or not str(user_email).strip():
            # Security requirement: unauthenticated/unspecified users receive no records
            return pd.DataFrame(columns=HISTORY_COLUMNS)

        target_email = str(user_email).strip().lower()
        filtered_df = df[df['user_email'].astype(str).str.strip().str.lower() == target_email].reset_index(drop=True)
        return filtered_df
    except Exception:
        return pd.DataFrame(columns=HISTORY_COLUMNS)


def load_user_history(user_email: str):
    """Dedicated function to load history filtered strictly by user_email."""
    return load_history(user_email=user_email)


def clear_user_history(user_email: str):
    """Remove ONLY the specified user's prediction history records from HISTORY_PATH."""
    import os
    import pandas as pd

    if not user_email or not str(user_email).strip():
        return

    if not os.path.exists(HISTORY_PATH):
        return

    _normalize_history_file()

    try:
        df = pd.read_csv(HISTORY_PATH)
        if 'user_email' not in df.columns:
            return

        target_email = str(user_email).strip().lower()
        remaining_df = df[df['user_email'].astype(str).str.strip().str.lower() != target_email].reset_index(drop=True)

        for c in HISTORY_COLUMNS:
            if c not in remaining_df.columns:
                remaining_df[c] = None
        remaining_df = remaining_df[HISTORY_COLUMNS]

        remaining_df.to_csv(HISTORY_PATH, index=False)
    except Exception:
        pass



