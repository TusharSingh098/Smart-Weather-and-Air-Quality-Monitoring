# 🌦️ Smart Weather and Air Quality Monitoring System

A comprehensive, data-driven desktop application for **real-time weather monitoring and air quality analysis**, powered by **API ingestion, XGBoost machine learning pipelines, and an interactive CustomTkinter dashboard**.

Built by **Team PyChaoS** from NIT Kurukshetra.

---

## 📌 Overview

This project integrates:
- 🌐 **Weather & AQI Data Ingestion:** Real-time data from the Open-Meteo API.
- 🧠 **Machine Learning Engine:** Self-healing, multi-target XGBoost pipelines for next-day forecasting.
- 📊 **Interactive UI Dashboard:** A threaded, Single-Page Application (SPA) with Dark/Light mode and dynamic Matplotlib rendering.

The system is designed with a modular, decoupled architecture, separating the backend ML logic from the frontend UI presentation.

---

## 🏗️ Project Architecture

```text
Smart-Weather-and-Air-Quality-Monitoring/
│
├── app.py                   # Main application entry point
├── run_ml_pipeline.py       # ML training orchestrator
├── requirements.txt         # Project dependencies
│
├── api_engine/              # External data routing
├── ml_engine/               # XGBoost models & data processing
├── ui_engine/               # CustomTkinter SPA & charts
│
├── weather_data/            # Stored .pkl ML models
└── assets/                  # UI icons and team logos
```

---

## ⚙️ Core Components

### 🔌 API Engine (`api_engine/`)
Handles all external data interactions with graceful fallback mechanisms.
* `weather_api.py`: Fetches real-time weather and AQI data. Acts as the primary data source.
* `mass_ingestion.py`: Bulk data collection for training datasets and historical analysis.

### 🧠 ML Engine (`ml_engine/`)
The analytical backbone of the system.
* `master_training.py`: Orchestrates the automated model training workflow.
* `multi_target_pipeline.py`: Handles multi-output predictions (e.g., AQI + weather metrics).
* `custom_xgboost_educational.py`: Custom implementation of XGBoost to demonstrate the inner workings of boosting algorithms.
* `inference_engine.py`: Runs trained `.pkl` models on new live data.
* `geography.py`: Handles state/district location boundaries for targeted predictions.

### 🎨 UI Engine (`ui_engine/`)
A threaded, non-blocking GUI built with CustomTkinter.
* `page_*.py`: Modular view files (Home, Weather, AQI) swapped dynamically via `tkraise()`.
* `charts.py`: Matplotlib and Seaborn integration for dynamic 24-hour and historic trend visualizations.
* `data_bridge.py`: The secure firewall connecting the backend ML/API data to the UI.
* `theme.py`: Pub/Sub architecture for real-time Dark/Light mode toggling.

---

## 🔄 Workflow

1. **Data Collection:** APIs fetch real-time weather & AQI data.
2. **Data Processing:** Cleaned and structured via ingestion scripts.
3. **Model Training:** Multi-target XGBoost models trained on historic district data.
4. **Inference:** Live data is pushed through `.pkl` models to generate future anchors.
5. **Visualization:** Mathematical curves synthesize hourly data, displayed via an interactive SPA.

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
```bash
python run_ml_pipeline.py
```
**2. Launch the Application:**
```bash
python app.py
```

---

## 🧠 Tech Stack

* **Language:** Python 3.12
* **Machine Learning:** XGBoost, Scikit-Learn
* **Data Processing:** Pandas, NumPy
* **GUI Framework:** CustomTkinter, Tkinter
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