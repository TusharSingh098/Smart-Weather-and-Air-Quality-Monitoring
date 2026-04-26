"""
ui_engine/page_weather.py
Multi-Mode Weather Dashboard & Dynamic View Controller.

A polymorphic UI component that handles three distinct operational modes:
  • "historic"  – Hourly data rendering for the last 1, 7, or 30 days.
  • "today"     – Live 24-hour T-Zero forecasting.
  • "tomorrow"  – XGBoost Machine Learning prediction and diurnal curve synthesis.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import threading
import customtkinter as ctk
from . import theme
from . import data_bridge as db
from . import charts
import pandas as pd

# ─── Metric Component Factory ──────────────────────────────────────────────────

def _metric(parent, icon, value, label, color):
    """Generates uniform, stylized statistical UI cards for weather metrics."""
    c = theme.get()
    card = ctk.CTkFrame(parent, fg_color=c["card"],
                        corner_radius=12, border_width=1,
                        border_color=c["border"])
    ctk.CTkLabel(card, text=icon, font=theme.font(22)).pack(pady=(12, 0))
    ctk.CTkLabel(card, text=str(value),
                 font=theme.font(20, "bold"),
                 text_color=color).pack()
    ctk.CTkLabel(card, text=label,
                 font=theme.font(10),
                 text_color=c["text_muted"]).pack(pady=(2, 12))
    return card

# ─── Main Page Class ───────────────────────────────────────────────────────────

class WeatherPage(ctk.CTkFrame):
    """
    Polymorphic view controller for rendering meteorological data and AI predictions.
    """
    MODES = ("historic", "today", "tomorrow", "diagnostics")

    def __init__(self, parent, *, app, mode: str = "historic"):
        assert mode in self.MODES
        c = theme.get()
        super().__init__(parent, fg_color=c["bg"], corner_radius=0)
        self._app  = app
        self.mode  = mode
        self._city = ""
        self._days = 7           # Default temporal window for historic mode
        self._last_canvas = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        theme.on_change(self._retheme)

    # ─── Public API (Controlled by app.py) ────────────────────────────────────

    def set_city(self, city: str):
        """Updates the active geographic anchor and triggers asynchronous data fetching."""
        self._city = city
        if hasattr(self, "_city_lbl"):
            self._city_lbl.configure(text=f"📍  {city}")
            
        # Tomorrow mode requires explicit user execution via the Predict button
        if self.mode != "tomorrow":
            self._fetch()

    def on_show(self):
        """Lifecycle hook executed when the page is brought to the front."""
        pass

    # ─── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Scaffolds the universal scrolling layout and delegates header construction."""
        c = theme.get()
        
        # Outer scroll container
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=c["bg"],
            scrollbar_button_color=c["border"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        # Polymorphic Header Routing
        if self.mode == "historic":
            self._build_historic_header()
        elif self.mode == "today":
            self._build_today_header()
        elif self.mode == "tomorrow":
            self._build_tomorrow_header()
        elif self.mode == "diagnostics":
            self._build_diagnostics_header()

        # Universal Status Indicator
        self._status = ctk.CTkLabel(
            self._scroll, text="",
            font=theme.font(11), text_color=c["text_muted"],
        )
        self._status.grid(row=2, column=0, pady=4)

        # Universal Chart Container
        self._chart_zone = ctk.CTkFrame(
            self._scroll, fg_color="transparent",
        )
        self._chart_zone.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._chart_zone.grid_columnconfigure(0, weight=1)

    # ─── Historic Mode Header ──────────────────────────────────────────────────

    def _build_historic_header(self):
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(head, text="📊  Historic Weather Data",
                     font=theme.font(16, "bold"), text_color=c["text"]).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(14, 6))

        self._city_lbl = ctk.CTkLabel(head, text="📍  —", font=theme.font(11), text_color=c["text_muted"])
        self._city_lbl.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        tl = ctk.CTkFrame(head, fg_color="transparent")
        tl.grid(row=1, column=1, sticky="e", padx=18, pady=(0, 10))

        for lbl, days in [("Last Day", 1), ("Last Week", 7), ("Last Month", 30)]:
            btn = ctk.CTkButton(
                tl, text=lbl, width=100, height=32,
                font=theme.font(11),
                fg_color=c["accent"] if days == 7 else c["card"],
                text_color="#fff" if days == 7 else c["text_muted"],
                border_width=1, border_color=c["border"],
                hover_color=c["btn_hover"],
                command=lambda d=days, b=None: self._set_days(d),
            )
            btn.pack(side="left", padx=4)
            if days == 7:
                self._days_active_btn = btn

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=2, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 14))

    def _set_days(self, days: int):
        self._days = days
        if self._city:
            self._fetch()

    # ─── Today Mode Header ─────────────────────────────────────────────────────

    def _build_today_header(self):
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(head, text="☀️  Today's Forecast",
                     font=theme.font(16, "bold"), text_color=c["text"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(14, 4))

        self._city_lbl = ctk.CTkLabel(head, text="📍  —", font=theme.font(11), text_color=c["text_muted"])
        self._city_lbl.grid(row=1, column=0, sticky="w", padx=18)

        self._condition_lbl = ctk.CTkLabel(head, text="", font=theme.font(13), text_color=c["accent"])
        self._condition_lbl.grid(row=2, column=0, sticky="w", padx=18)

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(6, 14))

    # ─── Tomorrow (Machine Learning) Mode Header ───────────────────────────────

    def _build_tomorrow_header(self):
        """Constructs the UI for XGBoost Model selection and Execution."""
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(head, text="🔮  Tomorrow's ML Prediction",
                     font=theme.font(16, "bold"), text_color=c["text"]).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(14, 8))

        # ── State / District Cascading Dropdowns ──
        ctk.CTkLabel(head, text="State:", font=theme.font(12), text_color=c["text_muted"]).grid(
            row=1, column=0, padx=(18, 4), pady=(0, 12))

        states = db.get_states()
        self._state_var = ctk.StringVar(value=states[0])
        self._state_menu = ctk.CTkOptionMenu(
            head, values=states, variable=self._state_var,
            width=160, height=34, font=theme.font(12),
            fg_color=c["card"], text_color=c["text"],
            button_color=c["accent"],
            command=self._on_state_change, # Triggers district cascade
        )
        self._state_menu.grid(row=1, column=1, padx=(0, 12), pady=(0, 12))

        ctk.CTkLabel(head, text="District:", font=theme.font(12), text_color=c["text_muted"]).grid(
            row=1, column=2, padx=(0, 4), sticky="e", pady=(0, 12))

        initial_districts = db.get_districts(states[0])
        self._district_var = ctk.StringVar(value=initial_districts[0])
        self._district_menu = ctk.CTkOptionMenu(
            head, values=initial_districts,
            variable=self._district_var,
            width=160, height=34, font=theme.font(12),
            fg_color=c["card"], text_color=c["text"],
            button_color=c["accent"],
        )
        self._district_menu.grid(row=1, column=3, padx=(0, 18), pady=(0, 12))

        # ── Execution Trigger ──
        self._predict_btn = ctk.CTkButton(
            head, text="🔮  Predict Tomorrow",
            width=180, height=36, font=theme.font(12, "bold"),
            fg_color=c["accent"], hover_color=c["accent"],
            command=self._run_prediction,
        )
        self._predict_btn.grid(row=2, column=0, columnspan=4, padx=18, pady=(0, 14))

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=3, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 14))

        # System Notice
        notice = ctk.CTkFrame(self._scroll, fg_color=c["tag_bg"],
                               corner_radius=10, border_width=1, border_color=c["border"])
        notice.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))
        ctk.CTkLabel(
            notice,
            text="ℹ️  Only trained districts (from geography.py) are available here.\n"
                 "If models are missing, run  python run_ml_pipeline.py  first.",
            font=theme.font(10), text_color=c["text_muted"], justify="left",
        ).pack(padx=14, pady=8, anchor="w")

    # ─── Diagnostics (Validation) Mode Header ──────────────────────────────────

    def _build_diagnostics_header(self):
        """Constructs the UI for viewing AI Model Accuracy and Feature Importance."""
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1, border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(head, text="🔬  AI Model Diagnostics & Validation",
                     font=theme.font(16, "bold"), text_color=c["text"]).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(14, 8))

        # ── State / District Dropdowns (Reused logic from Tomorrow mode) ──
        ctk.CTkLabel(head, text="State:", font=theme.font(12), text_color=c["text_muted"]).grid(
            row=1, column=0, padx=(18, 4), pady=(0, 12))

        states = db.get_states()
        self._state_var = ctk.StringVar(value=states[0])
        self._state_menu = ctk.CTkOptionMenu(
            head, values=states, variable=self._state_var, width=160, height=34,
            font=theme.font(12), fg_color=c["card"], text_color=c["text"],
            button_color=c["accent"], command=self._on_state_change
        )
        self._state_menu.grid(row=1, column=1, padx=(0, 12), pady=(0, 12))

        ctk.CTkLabel(head, text="District:", font=theme.font(12), text_color=c["text_muted"]).grid(
            row=1, column=2, padx=(0, 4), sticky="e", pady=(0, 12))

        initial_districts = db.get_districts(states[0])
        self._district_var = ctk.StringVar(value=initial_districts[0])
        self._district_menu = ctk.CTkOptionMenu(
            head, values=initial_districts, variable=self._district_var, width=160, height=34,
            font=theme.font(12), fg_color=c["card"], text_color=c["text"], button_color=c["accent"]
        )
        self._district_menu.grid(row=1, column=3, padx=(0, 18), pady=(0, 12))

        # ── Execution Trigger ──
        self._predict_btn = ctk.CTkButton(
            head, text="📊  Load Validation Report", width=200, height=36,
            font=theme.font(12, "bold"), fg_color=c["accent3"], hover_color=c["accent"],
            command=self._run_diagnostics
        )
        self._predict_btn.grid(row=2, column=0, columnspan=4, padx=18, pady=(0, 14))

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=3, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 14))

        # System Notice
        notice = ctk.CTkFrame(self._scroll, fg_color=c["tag_bg"],
                               corner_radius=10, border_width=1, border_color=c["border"])
        notice.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))
        ctk.CTkLabel(
            notice,
            text="ℹ️  Only trained districts (from geography.py) are available here.\n"
                 "If models are missing, run  python run_ml_pipeline.py  first.",
            font=theme.font(10), text_color=c["text_muted"], justify="left",
        ).pack(padx=14, pady=8, anchor="w")

    def _on_state_change(self, state: str):
        """Cascading update: Modifies District dropdown values when State changes."""
        districts = db.get_districts(state)
        self._district_var.set(districts[0])
        self._district_menu.configure(values=districts)

    # ─── Asynchronous Execution Engine ─────────────────────────────────────────

    def _fetch(self):
        """Spawns daemon thread for API requests."""
        if not self._city:
            self._set_status("Enter a city name in the search bar above.")
            return
            
        self._set_status("⏳  Fetching data…")
        self._predict_btn_disable_if_exists()

        mode = self.mode
        city = self._city
        days = self._days

        def worker():
            if mode == "historic":
                data = db.fetch_historic_weather(city, days)
            else:
                data = db.fetch_today_weather(city)
            # Safely return to main UI thread
            self.after(0, lambda: self._on_weather_ready(data))

        threading.Thread(target=worker, daemon=True).start()

    def _run_prediction(self):
        """Spawns daemon thread for ML Inference."""
        state    = self._state_var.get()
        district = self._district_var.get()

        if not db.models_exist(state, district):
            self._set_status(
                "⚠️  Models not found for this district. "
                "Run  python run_ml_pipeline.py  to train first."
            )
            return

        self._set_status("⏳  Running ML inference…")
        self._predict_btn.configure(state="disabled")

        def worker():
            result = db.predict_tomorrow(state, district)
            # Safely return to main UI thread
            self.after(0, lambda: self._on_prediction_ready(result))

        threading.Thread(target=worker, daemon=True).start()

    def _run_diagnostics(self):
        """Calculates live MAE and loads static analysis charts into the UI."""
        from PIL import Image
        import os
        
        state = self._state_var.get()
        district = self._district_var.get()
        c = theme.get()
        
        self._set_status("⏳  Loading System Diagnostics...")
        self._clear_metrics()
        self._clear_charts()
        
        # 1. Calculate Real-Time Error (MAE) from logs
        _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_path = os.path.join(_ROOT, "logs", "prediction_audit.csv")
        
        mae_val = "N/A"
        if os.path.exists(log_path):
            try:
                log_df = pd.read_csv(log_path)
                dist_df = log_df[(log_df['district'] == district) & (log_df['status'] == 'Verified')]
                if not dist_df.empty:
                    error = (dist_df['actual_max'] - dist_df['pred_max']).abs().mean()
                    mae_val = f"{error:.2f}°C"
            except Exception as e:
                print(f"Failed to read logs: {e}")

        # Populate the MAE Metric Card
        self._metrics_row.grid_columnconfigure(0, weight=1)
        card = _metric(self._metrics_row, "🎯", mae_val, "Mean Absolute Error (Max Temp)", c["warning"])
        card.grid(row=0, column=0, padx=4, sticky="nsew")
        
        # 2. Load the Analysis PNGs generated by your ML scripts
        target_images = [
            f"{district}_temperature_2m_max_importance.png",
            f"{district}_temperature_2m_max_residuals.png"
        ]
        
        row_idx = 0
        images_found = False
        
        for img_name in target_images:
            img_path = os.path.join(_ROOT, "logs", "analysis", img_name)
            if os.path.exists(img_path):
                images_found = True
                
                frame = ctk.CTkFrame(self._chart_zone, fg_color="transparent")
                frame.grid(row=row_idx, column=0, sticky="ew", pady=(10, 20))
                frame.grid_columnconfigure(0, weight=1)
                
                try:
                    pil_image = Image.open(img_path)
                    aspect_ratio = pil_image.width / pil_image.height
                    new_width = 800
                    new_height = int(new_width / aspect_ratio)
                    
                    ctk_img = ctk.CTkImage(light_image=pil_image, size=(new_width, new_height))
                    lbl = ctk.CTkLabel(frame, image=ctk_img, text="")
                    lbl.pack()
                    
                    row_idx += 1
                except Exception as e:
                     print(f"Failed to load image {img_name}: {e}")
                
        # The crucial "Graceful Degradation" fallback
        if not images_found:
            self._set_status("⚠️  Charts not found. Run evaluator.py and residual_analyzer.py in your terminal first.")
        else:
            self._set_status("✅  Diagnostics loaded successfully.")

    # ─── Thread-Safe Callbacks ─────────────────────────────────────────────────

    def _on_weather_ready(self, df):
        self._set_status("")
        self._predict_btn_disable_if_exists(enable=True)
        if df is None or df.empty:
            self._set_status("⚠️  No data returned. Check city name or API.")
            return

        self._clear_metrics()
        self._clear_charts()

        if self.mode == "historic":
            self._populate_historic_metrics(df)
            self._draw_historic_charts(df)
        else:
            self._populate_today_metrics(df)
            self._draw_today_charts(df)

    def _on_prediction_ready(self, result: tuple[dict, pd.DataFrame] | None):
        """Parses the dual-payload (Single Metric Dict + Hourly Synthesized DF) from the ML Helper."""
        self._set_status("")
        self._predict_btn.configure(state="normal")
        if result is None:
            self._set_status("⚠️  Prediction failed. Ensure models are trained.")
            return

        pred_dict, hourly_df = result

        self._clear_metrics()
        self._clear_charts()
        
        # Render deterministic anchor points
        self._populate_tomorrow_results(pred_dict, hourly_df)
        
        # Render the synthesized 24-hour mathematical diurnal curve
        dark = theme.is_dark()
        frame = ctk.CTkFrame(self._chart_zone, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        frame.grid_columnconfigure(0, weight=1)
        
        fig = charts.hourly_forecast_chart(hourly_df, dark=dark)
        charts.embed(fig, frame)

    # ─── Metric Aggregation & Population ───────────────────────────────────────

    def _populate_historic_metrics(self, df):
        c = theme.get()
        row = self._metrics_row
        for i in range(5):
            row.grid_columnconfigure(i, weight=1)

        t_avg = f"{df['temperature_2m'].mean():.1f}°C"
        t_max = f"{df['temperature_2m'].max():.1f}°C"
        h_avg = f"{df['relative_humidity_2m'].mean():.0f}%"
        w_avg = f"{df['wind_speed_10m'].mean():.1f} km/h"
        r_tot = f"{df['rain'].sum():.1f} mm"

        for i, (icon, val, lbl, col) in enumerate([
            ("🌡", t_avg, "Avg Temp",   c["accent3"]),
            ("🔺", t_max, "Max Temp",   c["danger"]),
            ("💧", h_avg, "Avg Humid.", c["rain"]),
            ("💨", w_avg, "Avg Wind",   c["accent2"]),
            ("🌧", r_tot, "Total Rain", c["accent"]),
        ]):
            card = _metric(row, icon, val, lbl, col)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

    def _populate_today_metrics(self, df):
        c = theme.get()
        row = self._metrics_row
        for i in range(7):
            row.grid_columnconfigure(i, weight=1)

        # ─── REAL-TIME CLOCK MATCHING ───
        # 1. Ensure 'time' is a datetime object
        df['time'] = pd.to_datetime(df['time'])
        
        # 2. Get the current hour from the system clock (e.g., 1 for 1:22 AM)
        current_hour = pd.Timestamp.now().hour
        
        # 3. Filter the DataFrame for the row matching this exact hour
        current_row = df[df['time'].dt.hour == current_hour]
        
        if not current_row.empty:
            latest = current_row.iloc[0]
            print(f" -> Clock Match Success: Displaying data for {current_hour}:00")
        else:
            # Fallback to last available if current hour isn't in the set
            latest = df.iloc[-1]
        code   = int(latest.get("weather_code", 0))
        icon   = db.WEATHER_ICONS.get(code, "🌡")
        cond   = db.WEATHER_LABELS.get(code, "—")
        if hasattr(self, "_condition_lbl"):
            self._condition_lbl.configure(text=f"{icon}  {cond}")

        t_cur = f"{latest['temperature_2m']:.1f}°C"
        t_avg = f"{df['temperature_2m'].mean():.1f}°C"
        t_max = f"{df['temperature_2m'].max():.1f}°C"

        t_fl  = (f"{latest['apparent_temperature']:.1f}°C"
                 if "apparent_temperature" in df.columns else "—")
        h_cur = f"{latest['relative_humidity_2m']:.0f}%"
        w_cur = f"{latest['wind_speed_10m']:.1f} km/h"
        r_cur = f"{df['rain'].sum():.1f} mm"

        for i, (ico, val, lbl, col) in enumerate([
            ("🌡", t_cur, "Temperature",  c["accent3"]),
            ("📊", t_avg, "Avg Temp",     c["accent3"]),
            ("🔺", t_max, "Max Temp",     c["danger"]),
            ("🤔", t_fl,  "Feels Like",   c["warning"]),
            ("💧", h_cur, "Humidity",     c["rain"]),
            ("💨", w_cur, "Wind Speed",   c["accent2"]),
            ("🌧", r_cur, "Rain Total",   c["accent"]),
        ]):
            card = _metric(row, ico, val, lbl, col)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

    def _populate_tomorrow_results(self, result: dict, hourly_df: pd.DataFrame):
        c   = theme.get()
        row = self._metrics_row
        
        for i in range(6):
            row.grid_columnconfigure(i, weight=1)

        # 1. Extraction: Pull new keys from the ML prediction dictionary
        max_t = result.get("temperature_2m_max", "—")
        min_t = result.get("temperature_2m_min", "—")
        feel  = result.get("feels_like",        "—")
        humd  = result.get("relative_humidity_2m", "—")
        rain  = result.get("rain_probability",   "—")
        fdate = result.get("future_date", "Tomorrow")

        # 2. Formatting: Prepare strings for the UI cards
        max_s  = f"{max_t:.1f}°C" if isinstance(max_t, float) else str(max_t)
        min_s  = f"{min_t:.1f}°C" if isinstance(min_t, float) else str(min_t)
        feel_s = f"{feel:.1f}°C"  if isinstance(feel, float)  else str(feel)
        humd_s = f"{humd:.0f}%"   if isinstance(humd, float)  else str(humd)
        rain_s = f"{rain:.1f}%"   if isinstance(rain, float)  else str(rain)

        self._set_status(f"🗓  Forecast for: {fdate}")

        # 3. Deployment: Inject the 6-card array into the dashboard
        for i, (ico, val, lbl, col) in enumerate([
            ("🔺", max_s,  "Max Temp",    c["danger"]),
            ("❄️", min_s,  "Min Temp",    c["accent2"]),
            ("📊", feel_s, "Avg Prediction", c["accent3"]),
            ("🤔", feel_s, "Feels Like",  c["warning"]),
            ("💧", humd_s, "Avg Humidity", c["rain"]),
            ("🌧", rain_s, "Rain Chance", c["accent"]),
        ]):
            card = _metric(row, ico, val, lbl, col)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

        # Custom Geometry Rain Probability Gauge Integration
        if isinstance(rain, float):
            gauge_frame = ctk.CTkFrame(
                self._chart_zone, fg_color="transparent",
            )
            gauge_frame.grid(row=0, column=0, pady=(10, 0), sticky="nsew")
            fig = charts.rain_probability_gauge(rain, dark=theme.is_dark())
            charts.embed(fig, gauge_frame)

    # ─── Matplotlib Chart Integration ─────────────────────────────────────────

    def _draw_historic_charts(self, df):
        days = self._days
        dark = theme.is_dark()
        row  = 0

        for fig_fn, label in [
            (lambda: charts.temperature_chart(df, days, dark), "Temperature"),
            (lambda: charts.humidity_chart(df, days, dark),    "Humidity"),
            (lambda: charts.wind_chart(df, days, dark),        "Wind Speed"),
            (lambda: charts.rain_chart(df, days, dark),        "Rainfall"),
        ]:
            frame = ctk.CTkFrame(self._chart_zone, fg_color="transparent")
            frame.grid(row=row, column=0, sticky="ew", pady=(8, 0))
            frame.grid_columnconfigure(0, weight=1)
            fig = fig_fn()
            charts.embed(fig, frame)
            row += 1

    def _draw_today_charts(self, df):
        dark = theme.is_dark()
        frame = ctk.CTkFrame(self._chart_zone, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", pady=(10, 0))
        frame.grid_columnconfigure(0, weight=1)
        fig = charts.hourly_forecast_chart(df, dark=dark)
        charts.embed(fig, frame)

    # ─── View Controller Utility Methods ──────────────────────────────────────

    def _clear_metrics(self):
        for w in self._metrics_row.winfo_children():
            w.destroy()

    def _clear_charts(self):
        for w in self._chart_zone.winfo_children():
            w.destroy()

    def _set_status(self, msg: str):
        if hasattr(self, "_status"):
            self._status.configure(text=msg)

    def _predict_btn_disable_if_exists(self, enable: bool = False):
        if hasattr(self, "_predict_btn"):
            self._predict_btn.configure(
                state="normal" if enable else "disabled"
            )

    def _retheme(self):
        c = theme.get()
        self.configure(fg_color=c["bg"])
        if hasattr(self, "_scroll"):
            self._scroll.configure(fg_color=c["bg"])