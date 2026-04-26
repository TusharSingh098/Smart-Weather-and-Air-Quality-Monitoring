# 🌦️ Smart Weather and Air Quality Monitoring System

A comprehensive, data-driven desktop application for **real-time weather monitoring, air quality analysis, and ML-driven forecasting**. Powered by **API ingestion, self-healing XGBoost pipelines, and an interactive CustomTkinter Single-Page Application (SPA) dashboard**.

Built by **Team PyChaoS** from NIT Kurukshetra.

---

## 📌 Overview

This project integrates:
- 🌐 **Weather & AQI Data Ingestion:** Real-time, asynchronous data from the Open-Meteo API.
- 🧠 **Machine Learning Engine:** Multi-target XGBoost pipelines for next-day Max/Min temperature, humidity, and rain probability forecasting.
- 🔬 **Scientific Validation Suite:** Built-in backtesting, Feature Importance extraction (Information Gain), and Gaussian Residual Analysis to mathematically prove model accuracy.
- 📊 **Interactive UI Dashboard:** A threaded SPA with Dark/Light mode, dynamic Matplotlib rendering, and mathematically synthesized diurnal curves.

The system is designed with a strictly decoupled architecture, separating the backend mathematical logic from the frontend UI presentation via a Facade pattern.

---

## 🏗️ Project Architecture

```text
Smart-Weather-and-Air-Quality-Monitoring/
│
├── app.py                   # Main application entry point & UI Router
├── run_ml_pipeline.py       # ML training orchestrator
├── run_backtest.py          # Reality-sync daemon for MAE accuracy tracking
├── requirements.txt         # Project dependencies
│
├── api_engine/              # External data routing & geographic resolution
├── ml_engine/               # XGBoost algorithms, diagnostic tools, & data prep
├── ui_engine/               # CustomTkinter SPA, Matplotlib charts, & view controllers
│
├── weather_data/            # Stored .pkl ML models & processed training CSVs
├── logs/                    # Prediction audit CSVs and generated analysis charts
└── assets/                  # UI icons and team logos
```

---

## ⚙️ Core Components

### 🔌 API Engine (`api_engine/`)
Handles all external data interactions with graceful fallback mechanisms.
* `weather_api.py`: Fetches real-time weather and AQI data. Acts as the primary data source.
* `mass_ingestion.py`: Bulk data collection for training datasets and historical analysis.

### 🧠 ML Engine (`ml_engine/`)
The analytical and diagnostic backbone of the system.
* `multi_target_pipeline.py`: Assembles lag-feature matrices and handles multi-output predictions.
* `master_training.py`: Orchestrates the automated `.pkl` model training workflow.
* `inference_engine.py`: Runs trained models on live T-Zero vectors.
* `performance_monitor.py`: Logs system predictions to calculate real-time Mean Absolute Error (MAE).
* `evaluator.py`: Extracts and visualizes Information Gain to show *how* the AI makes decisions.
* `residual_analyzer.py`: Plots error distributions against a perfect Gaussian Bell Curve.

### 🎨 UI Engine (`ui_engine/`)
A threaded, non-blocking GUI built with CustomTkinter.
* `app.py` & `sidebar.py`: Zero-load SPA routing via memory-cached UI frames.
* `page_*.py`: Modular view controllers (Home, Historic, Today, ML Tomorrow, Diagnostics, AQI).
* `charts.py`: Dynamic Matplotlib and Seaborn integration for 24-hour trends and custom geometric UI gauges.
* `data_bridge.py`: The secure interface connecting the backend ML/API data to the UI, featuring offline data synthesis.
* `theme.py`: Pub/Sub architecture for instantaneous Dark/Light mode toggling.

---

## 🔄 System Workflow

1. **Data Collection:** APIs fetch real-time weather & AQI data.
2. **Data Processing:** Cleaned, cyclical time features extracted, and structured via ingestion scripts.
3. **Model Training:** Multi-target XGBoost models trained on historic regional data.
4. **Inference:** Live data is pushed through models to generate future anchors.
5. **Visualization:** Mathematical phase-shifted curves synthesize hourly data, displayed via the interactive UI.
6. **Scientific Validation:** `run_backtest.py` routinely verifies past predictions against actual API reality to monitor model drift and MAE.

---

## 📦 Installation & Setup

Clone the repository and install the dependencies:
```bash
git clone [https://github.com/TusharSingh098/Smart-Weather-and-Air-Quality-Monitoring.git](https://github.com/TusharSingh098/Smart-Weather-and-Air-Quality-Monitoring.git)
cd Smart-Weather-and-Air-Quality-Monitoring
pip install -r requirements.txt
```

### ▶️ Running the Project

**1. Run the ML Training Pipeline (First Boot):**
*Must be run to generate the local `.pkl` binaries.*
```bash
python run_ml_pipeline.py
```

**2. Generate AI Validation Charts (Optional but Recommended):**
*Generates the Feature Importance and Residual Bell Curves for the UI Diagnostics tab.*
```bash
python ml_engine/evaluator.py
python ml_engine/residual_analyzer.py
```

**3. Launch the Application:**
```bash
python app.py
```

**4. Run System Backtest (Daily Maintenance):**
*Calculates your exact model accuracy (MAE) over time.*
```bash
python run_backtest.py
```

---

## 🧠 Tech Stack

* **Language:** Python 3.12
* **Machine Learning:** XGBoost, Scikit-Learn
* **Mathematics:** NumPy, SciPy (Statistical distributions)
* **Data Processing:** Pandas
* **GUI Framework:** CustomTkinter, PIL
* **Data Visualization:** Matplotlib, Seaborn
* **Data Source:** Open-Meteo API

---

## 👥 Team PyChaoS (NIT Kurukshetra)
* **Tushar Singh** - Backend & ML Engineer (Lead)
* **Abhishek Bhattacharjee** - Machine Learning Engineer
* **Ujjwal Verma** - API Integration Engineer
* **Teena Gautam** - UI/UX & API Developer
* **Balwant Shakya** - UI/UX Designer & Frontend

---

## 📜 License
MIT License. See `LICENSE` for more information.