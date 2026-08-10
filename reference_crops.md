# Tamil Nadu Agronomic Reference Ranges for Extended Crop Dataset

> **Transparency Disclosure**: The 6 crops below (Sugarcane, Groundnut, Pearl Millet / Cumbu, Finger Millet / Ragi, Turmeric, and Cashew) are parameterized using general published agronomic reference guidelines from the **Indian Council of Agricultural Research (ICAR)** and **Tamil Nadu Agricultural University (TNAU) Agritech Portal**. They are **not derived from measured empirical field datasets** like the baseline 22 crops. Recommendations for these 6 crops should be treated as generalized reference-range estimates.

---

## 1. Crop Reference Ranges (ICAR / TNAU Guidelines)

| Crop | N (kg/ha) | P (kg/ha) | K (kg/ha) | Temperature (°C) | Humidity (%) | pH | Rainfall (mm) | Season |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Sugarcane** (*Saccharum officinarum*) | 150 – 250 | 50 – 90 | 110 – 190 | 26.0 – 38.0 | 60.0 – 85.0 | 6.0 – 8.0 | 1100 – 2200 | Kharif / Annual |
| **Groundnut** (*Arachis hypogaea*) | 15 – 30 | 35 – 60 | 40 – 75 | 22.0 – 34.0 | 50.0 – 75.0 | 5.8 – 7.5 | 450 – 850 | Kharif / Rabi |
| **Pearl Millet (Cumbu)** (*Pennisetum glaucum*) | 45 – 85 | 25 – 45 | 25 – 45 | 27.0 – 40.0 | 35.0 – 65.0 | 6.5 – 8.2 | 300 – 650 | Kharif / Zaid |
| **Finger Millet (Ragi)** (*Eleusine coracana*) | 40 – 75 | 25 – 45 | 25 – 45 | 22.0 – 33.0 | 50.0 – 75.0 | 5.5 – 7.8 | 500 – 900 | Kharif / Rabi |
| **Turmeric** (*Curcuma longa*) | 90 – 150 | 40 – 70 | 90 – 140 | 20.0 – 35.0 | 65.0 – 88.0 | 5.8 – 7.5 | 1000 – 1800 | Annual / Kharif |
| **Cashew** (*Anacardium occidentale*) | 25 – 65 | 15 – 40 | 25 – 60 | 24.0 – 36.0 | 55.0 – 85.0 | 5.5 – 7.2 | 800 – 1600 | Annual |

---

## 2. Excluded Crops & Justification

- **Tea** (*Camellia sinensis*): Excluded. Tea requires a specialized high-altitude microclimate (Nilgiris / Valparai hills, 1000–2500m elevation, acidic soil pH 4.5–5.5, high rainfall 1500–3000mm). Including tea in a general lowland model would create false positives for general farmers.

---

## 3. Data Generation Methodology

Synthetic samples (100 per crop) were generated using Gaussian distributions centered at the midpoint of each agronomic range, with standard deviation $\sigma = (\text{max} - \text{min}) / 6$, clipped strictly to $[\text{min}, \text{max}]$. This ensures realistic natural variation matching the distribution variance of the original 22 crops without introducing artificial exact duplicates.
