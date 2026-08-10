"""
train_model.py
===============================================================================
CROP RECOMMENDATION MODEL TRAINING PIPELINE (EXTENDED DATASET)
===============================================================================

PUBLISHED ICAR / TNAU AGRONOMIC REFERENCE RANGES FOR EXTENDED CROPS:
These 6 Tamil Nadu crops are integrated using general published reference ranges
from the Indian Council of Agricultural Research (ICAR) and TNAU Agri-Portal,
NOT measured field trial datasets like the baseline 22 crops:

1. Sugarcane (sugarcane):
   - N: 150-250 kg/ha | P: 50-90 kg/ha | K: 110-190 kg/ha
   - Temp: 26.0-38.0 °C | Humidity: 60.0-85.0 % | pH: 6.0-8.0 | Rainfall: 1100-2200 mm
2. Groundnut (groundnut):
   - N: 15-30 kg/ha | P: 35-60 kg/ha | K: 40-75 kg/ha
   - Temp: 22.0-34.0 °C | Humidity: 50.0-75.0 % | pH: 5.8-7.5 | Rainfall: 450-850 mm
3. Pearl Millet / Cumbu (cumbu):
   - N: 45-85 kg/ha | P: 25-45 kg/ha | K: 25-45 kg/ha
   - Temp: 27.0-40.0 °C | Humidity: 35.0-65.0 % | pH: 6.5-8.2 | Rainfall: 300-650 mm
4. Finger Millet / Ragi (ragi):
   - N: 40-75 kg/ha | P: 25-45 kg/ha | K: 25-45 kg/ha
   - Temp: 22.0-33.0 °C | Humidity: 50.0-75.0 % | pH: 5.5-7.8 | Rainfall: 500-900 mm
5. Turmeric (turmeric):
   - N: 90-150 kg/ha | P: 40-70 kg/ha | K: 90-140 kg/ha
   - Temp: 20.0-35.0 °C | Humidity: 65.0-88.0 % | pH: 5.8-7.5 | Rainfall: 1000-1800 mm
6. Cashew (cashew):
   - N: 25-65 kg/ha | P: 15-40 kg/ha | K: 25-60 kg/ha
   - Temp: 24.0-36.0 °C | Humidity: 55.0-85.0 % | pH: 5.5-7.2 | Rainfall: 800-1600 mm

NOTE ON EXCLUDED CROPS:
- Tea (Camellia sinensis) is excluded due to its narrow Nilgiris highland microclimate
  (1000-2500m elevation, acidic soil pH 4.5-5.5, 1500-3000mm rain) which skews lowland models.
===============================================================================
"""

import os
import json
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Toggleable Dataset Path Selection
DEFAULT_DATASET = "crop_recommendation_extended.csv"
if not os.path.exists(DEFAULT_DATASET):
    DEFAULT_DATASET = os.path.join("data", "crop_recommendation_extended.csv")
if not os.path.exists(DEFAULT_DATASET):
    DEFAULT_DATASET = "crop_recommendation_sample.csv"

DATA_PATH = os.getenv("DATASET_PATH", DEFAULT_DATASET)
MODEL_PATH = "crop_model.pkl"
METRICS_PATH = "model_metrics.json"

REFERENCE_RANGE_CROPS = ["sugarcane", "groundnut", "cumbu", "ragi", "turmeric", "cashew"]
DISCLAIMER_TEXT = (
    "Sugarcane, Groundnut, Pearl Millet (Cumbu), Finger Millet (Ragi), Turmeric, and Cashew "
    "are included using general agronomic reference ranges (ICAR/TNAU), not measured field data "
    "like the other 22 crops. Recommendations for these 6 crops should be treated as less precise reference-range estimates."
)

def train():
    print(f"Loading dataset from: '{DATA_PATH}'")
    df = pd.read_csv(DATA_PATH)
    required = set(["N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"])
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Dataset missing required columns: {missing}")

    X = df.drop("label", axis=1)
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=200, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report_dict = classification_report(y_test, y_pred, output_dict=True)
    report_str = classification_report(y_test, y_pred)

    print("=" * 75)
    print(f"TRAINING COMPLETE Across {y.nunique()} Crops:")
    print(f"  - Dataset Path:  {DATA_PATH}")
    print(f"  - Train Samples: {len(X_train)}")
    print(f"  - Test Samples:  {len(X_test)}")
    print(f"  - Test Accuracy: {acc:.2%}")
    print("=" * 75)
    print(report_str)

    # Save metrics JSON
    metrics_data = {
        "accuracy": round(float(acc), 4),
        "accuracy_pct": f"{acc:.2%}",
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "total_rows": len(df),
        "num_crops": int(y.nunique()),
        "dataset_used": DATA_PATH,
        "reference_range_crops": REFERENCE_RANGE_CROPS,
        "disclaimer": DISCLAIMER_TEXT,
        "classification_report": report_dict,
    }
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    print(f"Saved model metrics to '{METRICS_PATH}'.")

    # Refit on FULL dataset before saving final model artifact
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)
    print(f"Refit final model on all {len(df)} rows and saved to '{MODEL_PATH}'.")

if __name__ == "__main__":
    train()
