# 🌱 Real-Time Smart Agriculture Decision Support System

An end-to-end, production-grade agricultural decision support application that combines machine learning, geocoded live weather, soil screening, economics, and multi-factor risk analysis to recommend optimal crops.

---

## 📌 Project Overview

Agriculture decision-making involves complex multi-variable analysis: evaluating soil nutrients, local weather patterns, seasonal windows, market pricing, production costs, expected yields, and environmental risks.

This application provides farmers, agricultural extension officers, and agronomists with an integrated **Decision Support System (DSS)** that delivers transparent, explainable crop recommendations backed by data.

---

## 🎯 System Objectives

1. **Integrated Multi-Factor Analysis:** Combine soil screening, live weather, crop economics, and risk factors with a trained ML classifier.
2. **Real-Time Data Transparency:** Explicitly label data sources as `🟢 LIVE`, `🟡 DEMO`, `🔵 USER INPUT`, or `🔴 UNAVAILABLE`. Never fabricate live data.
3. **Calibrated Decision Scoring:** Calculate a 0–100 score across 6 participating components (Model confidence 35%, Soil 20%, Weather 15%, Season 5%, Profit 15%, Risk 10%).
4. **Explainable Recommendations:** Articulate *why* a specific crop was selected with itemized supporting and attention factors.
5. **Full History & Reporting:** Track all past predictions in `prediction_history.csv` and generate downloadable CSV reports.

---

## 🏗️ System Architecture

```
User Location Query / Manual Input
        ↓
Geocoding (Nominatim / OpenStreetMap)
        ↓
Live Weather & Forecast (Open-Meteo API) / Manual Fallback
        ↓
Soil Parameter Inputs (N, P, K, pH) + Screening Engine
        ↓
Random Forest ML Model (crop_model.pkl — 22 Crops)
        ↓
Top-5 Candidate Crops Selection
        ↓
Soil Suitability + Weather Suitability + Season Validity
        ↓
Market Data (Live API / Local crop_economics.csv Demo Data)
        ↓
Profit Analysis (Revenue, Cost, Profit, ROI %, Break-even Yield)
        ↓
Risk Engine (LOW / MEDIUM / HIGH Risk + Itemized Reasons)
        ↓
6-Factor Calibrated Decision Support Score (/100)
        ↓
Top Recommendation + Explainable AI + Plotly Analytics
        ↓
Prediction History Tracking & CSV Report Generation
```

---

## 🤖 Machine Learning Model

- **Algorithm:** Scikit-Learn `RandomForestClassifier` (200 estimators).
- **Dataset:** 2,200 samples across 22 crops (`crop_recommendation_sample.csv`).
- **Features (7):** Nitrogen (`N`), Phosphorus (`P`), Potassium (`K`), Temperature (`temperature`), Humidity (`humidity`), `ph`, Rainfall (`rainfall`).
- **Model File:** `crop_model.pkl` (preserved core model, used via `predict()` and `predict_proba()`).

> [!NOTE]
> **Model Version Warning (`InconsistentVersionWarning`):**
> The pre-trained model `crop_model.pkl` was saved under an earlier scikit-learn version. When loaded in newer scikit-learn environments, a version warning may appear. The model remains fully functional and verified (`predict()` and `predict_proba()` pass diagnostic tests). It is **not** automatically retrained to maintain consistency.

---

## 📊 Data Status Transparency System

The application features a dedicated **Data Status Panel** in the sidebar to maintain transparency:

| Badge | Status Description |
| :--- | :--- |
| `🟢 LIVE` | Data actively fetched from verified external API (e.g. Open-Meteo API, Live Market API). |
| `🟡 DEMO` | Data retrieved from local fallback datasets (e.g. `crop_economics.csv`). |
| `🔵 USER INPUT` | Data manually entered by the user (e.g. soil NPK, manual weather overrides). |
| `🔴 UNAVAILABLE` | Data source unconfigured or temporarily unreachable. |

---

## 🧮 Decision Support Scoring Model

The Decision Support Score ($0 - 100$) combines 6 normalized factors:

$$\text{Score} = 100 \times \sum (w_i \times s_i)$$

Where normalized weights sum to $1.00$:
- **ML Confidence ($w = 0.35$):** Probability output from Random Forest classifier.
- **Soil Health ($w = 0.20$):** Soil health screening score (0–100).
- **Weather Suitability ($w = 0.15$):** Temperature and rainfall appropriateness.
- **Season Validity ($w = 0.05$):** Calendar window check (Kharif, Rabi, Zaid, Annual).
- **Profitability / ROI ($w = 0.15$):** Estimated Return on Investment.
- **Risk Assessment ($w = 0.10$):** Inverted risk score (LOW = 1.0, MEDIUM = 0.6, HIGH = 0.2).

---

## 📈 Profit & Economics Analysis

For every top-5 candidate crop, the system computes:
- **Revenue ($₹$):** $\text{Estimated Yield (kg/acre)} \times \text{Market Price (₹/kg)} \times \text{Land Area}$
- **Net Profit ($₹$):** $\text{Revenue} - \text{Production Cost}$
- **ROI ($\%$):** $(\text{Net Profit} / \text{Production Cost}) \times 100$
- **Break-even Yield ($\text{kg/acre}$):** $\text{Production Cost} / \text{Market Price}$

---

## 🖥️ Streamlit Multi-Section UI

1. **🏠 Dashboard:** Key decision summary, recommended crop metrics, active weather & risk status.
2. **🌾 Crop Recommendation:** Interactive workflow for location search, weather inputs, soil data, top-5 crop generation, explainable breakdown, and Plotly charts.
3. **🧪 Soil Analysis:** Detailed NPK & pH screening breakdown, identified deficiencies, fertilizer recommendations, and optimal range references.
4. **💰 Profit Analysis:** Tabular financial breakdown (revenue, cost, net profit, ROI) with ROI bar charts.
5. **📊 Crop Comparison:** Top-5 candidate comparison matrix and AI confidence vs profit bubble chart.
6. **📜 Prediction History:** Historical record of all past prediction runs with CSV export and clear history controls.
7. **📄 Reports:** Downloadable official CSV decision report generation.
8. **ℹ️ About:** System documentation, model specifications, data status rules, and disclaimers.

---

## ⚙️ Installation & Setup (Windows VS Code)

### 1. Prerequisites
Ensure Python 3.9+ is installed on your system.

### 2. Clone / Open Project
Open terminal and navigate to the project directory:
```powershell
cd "C:\Users\user1\Downloads\crop-recommender-v2\crop-recommender-v2"
```

### 3. Create & Activate Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Edit `.env` if you wish to configure optional APMC Market API keys:
```env
MARKET_API_URL=
MARKET_API_KEY=
```

---

## 🧪 Testing & Verification

Run the project diagnostics script to verify compilation, dependencies, model loading, geocoding, weather services, market fallback, soil screening, and report generation:

```powershell
python -m compileall .
python diagnostics.py
```

---

## 🚀 Running the Application

Launch the Streamlit web application:

```powershell
streamlit run app.py
```

The application will launch in your browser at `http://localhost:8501`.

---

## ☁️ Deployment Preparation (Streamlit Community Cloud)

1. Ensure `.env` is listed in `.gitignore`.
2. Ensure `crop_model.pkl` is committed to repository or supplied via storage.
3. Configure environment secrets in Streamlit Cloud Dashboard:
   - `MARKET_API_URL` (optional)
   - `MARKET_API_KEY` (optional)
4. Set main file path to `app.py`.

---

## ⚠️ Limitations & Disclaimers

- **Soil Screening Disclaimer:** The soil screening engine provides rule-based screening from user-entered values. It is **not** a substitute for certified laboratory soil testing.
- **Market Data:** Unless a live APMC market API is configured via `MARKET_API_URL`, economic prices are drawn from `crop_economics.csv` and labeled as `🟡 DEMO`.
- **Decision Support Only:** This application provides advisory decision support. Commercial farming decisions should be validated with local agricultural extension officers.

---

## 🔒 Password Security

- **Bcrypt Hashing:** Local passwords are stored using bcrypt with a minimum work factor (rounds) of 12.
- **Zero Plaintext Storage:** Passwords are never stored in plaintext or logged in system logs, console output, or exceptions.
- **Automatic Legacy Migration:** Legacy password formats (plaintext, MD5, SHA-1) are automatically upgraded to bcrypt upon successful user authentication.
- **Unmigratable Hashes:** Legacy weak hashes where the original password is unavailable offline are marked to require a secure password reset (`password_needs_reset`).
- **OAuth Isolation:** Google OAuth authentication remains separate from local password authentication.

