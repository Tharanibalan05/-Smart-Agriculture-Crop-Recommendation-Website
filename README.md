# Smart Agriculture – AI Crop Recommendation System

Smart Agriculture is an advanced, production-grade agricultural decision support system that leverages machine learning, live geocoded weather forecasts, rule-based 100-point soil health screening, APMC market pricing analysis, crop suitability evaluation, and multi-variable agricultural risk assessment to recommend optimal crops for sustainable and profitable farming.

---

## 📌 Overview

Agricultural decision-making involves evaluating complex, multi-variable factors: soil nutrient levels (N, P, K, pH), localized weather patterns, seasonal windows, market pricing trends, production costs, expected crop yields, and environmental risks.

This application provides farmers, agricultural extension officers, and agronomists with an integrated **Agriculture Decision Support System (DSS)** that delivers transparent, explainable crop recommendations backed by data science and agricultural domain logic.

---

## 🎯 Key Features

- **AI Crop Recommendation Engine:** Evaluates candidate crops using a Random Forest machine learning classifier trained on agricultural dataset samples.
- **100-Point Weighted Soil Health Analysis:** Continuous piecewise-linear scoring model evaluating Nitrogen (20%), Phosphorus (20%), Potassium (20%), pH (25%), and Soil Type (15%) to eliminate score cliffs.
- **Live Geocoded Weather Analysis:** Integrates Open-Meteo API for real-time location weather forecasts and historical climate averages.
- **APMC Market Price Analysis:** Pre-fetches state mandi prices via Government Data API (data.gov.in / Agmarknet) with local fallback datasets.
- **Crop Suitability & Water Requirements:** Evaluates crop-specific minimum water requirements and seasonal validity windows (Kharif, Rabi, Zaid).
- **Agricultural Risk Analysis:** 3-tier risk engine evaluating ROI profitability, climate risks, and data verification status.
- **6-Factor Calibrated Decision Support Score:** Synthesizes ML confidence, soil health, weather suitability, season validity, ROI, and risk into a 0–100 decision index.
- **Interactive Visual Analytics:** Interactive Plotly bar and bubble charts for confidence, profitability, and decision scores.
- **Downloadable Reports & Sharing:** CSV decision report exports and instant WhatsApp recommendation sharing.

---

## ⚙️ How It Works

```text
User Input / Location Search (Nominatim / GPS)
        ↓
Live Weather Integration (Open-Meteo API / Seasonal Averages)
        ↓
Soil Nutrient Input (N, P, K, pH) + 100-Point Soil Health Screening
        ↓
Random Forest Machine Learning Classifier (22 Crop Candidates)
        ↓
Bulk APMC Market Pricing Fetch (Agmarknet / Fallback Dataset)
        ↓
Crop Profitability & ROI Calculation (Yield x Price - Cost)
        ↓
Multi-Factor Agricultural Risk Engine (LOW / MEDIUM / HIGH Risk)
        ↓
Calibrated 6-Factor Decision Support Score (/100)
        ↓
Top-N Recommended Crops + Explainable AI Breakdown
```

---

## 🧪 Soil Health Analysis

The soil screening engine evaluates user-entered soil parameters against agronomically established ranges using a transparent 100-point weighted scoring model:

- **Nitrogen (N) [20 Points]:** Evaluates soil nitrogen content with continuous interpolation toward the optimal range (90–120 mg/kg).
- **Phosphorus (P) [20 Points]:** Assesses available phosphorus content with smooth scoring (optimal: 50–80 mg/kg).
- **Potassium (K) [20 Points]:** Evaluates available potassium levels (optimal: 50–80 mg/kg).
- **Soil pH [25 Points]:** Smooth suitability curve with maximum score in the neutral agricultural window (pH 6.0–7.5).
- **Soil Type [15 Points]:** Agronomic capability scoring across major soil types (Alluvial, Black Regur, Red & Yellow, Laterite, Arid/Desert, Saline, Peaty, Forest/Mountain).

---

## 🌾 Crop Recommendation

The crop recommendation engine runs a batch prediction across all candidate crops using a trained Random Forest model. The system ranks crops based on a 6-factor decision support score:

$$\text{Decision Score} = 100 \times \sum (w_i \times s_i)$$

Where weights account for:
1. **ML Model Confidence (35%)**
2. **Soil Health Screening Score (20%)**
3. **Weather & Climate Suitability (15%)**
4. **Seasonal Alignment (5%)**
5. **Net Profitability & ROI (15%)**
6. **Agricultural Risk Level (10%)**

---

## ☀️ Weather Analysis

- **Real-Time Forecasts:** Automatically retrieves current temperature, humidity, and rainfall from Open-Meteo weather service based on geocoded location.
- **Seasonal Climate Averages:** Calculates 3-year historical climate averages for Kharif (Jun–Oct), Rabi (Oct–Mar), and Zaid (Mar–Jun) planning horizons.
- **Effective Rainfall & Irrigation:** Adjusts effective crop water availability based on farmer-selected irrigation methods (Canal, Borewell, Drip/Sprinkler).

---

## 💰 Market Price Analysis

- **Live APMC Mandi Data:** Pre-fetches state-level mandi pricing from Government Data Portal (Agmarknet / data.gov.in API).
- **Local Economics Fallback:** Instant zero-latency fallback to `crop_economics.csv` data when live market API keys are unconfigured or unavailable.
- **Financial Metrics:** Computes Net Profit ($₹$), Return on Investment ($\text{ROI} \, \%$), and Break-even Yield ($\text{kg/acre}$).

---

## 🌾 Crop Suitability

- Evaluates geographic eligibility and climate boundaries for candidate crops.
- Supports reference agronomic data for additional regional crops (Sugarcane, Groundnut, Cumbu, Ragi, Turmeric, Cashew).

---

## ⚖️ Agricultural Risk Analysis

Computes a transparent risk classification (**LOW**, **MEDIUM**, **HIGH**) by auditing:
- Estimated ROI profitability threshold ($< 5\%$ ROI flag).
- Unverified market pricing data sources.
- Sub-optimal temperature or rainfall deviations.
- Extreme soil pH warnings ($\text{pH} < 5.5$ or $\text{pH} > 8.0$).

---

## 🛠️ Technology Stack

- **Frontend & App Framework:** Python, Streamlit, HTML5, Vanilla CSS3, JavaScript (PWA Service Worker)
- **Machine Learning:** Scikit-Learn (RandomForestClassifier), Joblib, NumPy, Pandas
- **Data Visualization:** Plotly Express
- **APIs & Data Services:** Open-Meteo Weather API, OpenStreetMap / Nominatim Geocoding API, Agmarknet / Data.gov.in APMC Market API
- **Database & Security:** SQLite, Bcrypt Password Encryption (Rounds=12), Google OAuth 2.0
- **Testing & Diagnostics:** Python `unittest`, `compileall`

---

## 🌐 Live Demo

Access the live web application on Render:
👉 **[https://smart-agriculture-dss.onrender.com](https://smart-agriculture-dss.onrender.com)**

---

## 📥 Installation

### 1. Prerequisites
Python 3.9 or higher installed on system.

### 2. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/Tharanibalan05/-Smart-Agriculture-Crop-Recommendation-Website.git
cd -Smart-Agriculture-Crop-Recommendation-Website
python -m venv venv
```

Activate environment:
- **Windows:** `venv\Scripts\activate`
- **Linux/macOS:** `source venv/bin/activate`

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Optionally add your APMC Market API key in `.env`:
```env
MARKET_API_URL=https://api.data.gov.in/resource/9ef4b77d-28c7-43a3-a0e3-7dcb4e613b0e
MARKET_API_KEY=your_api_key_here
```

---

## 🚀 Usage

Launch the web application locally:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

Run system diagnostic tests:
```bash
python -m compileall .
python diagnostics.py
```

---

## 🔒 Security & Privacy

- Passwords stored using bcrypt with work factor (rounds) = 12.
- Individual user prediction history isolation.
- Zero plaintext credential logging.
- PWA offline caching capabilities.
