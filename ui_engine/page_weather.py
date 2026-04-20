"""
ui_engine/page_weather.py
Weather section – handles three view modes:
  • "historic"  – hourly data for last 1 / 7 / 30 days
  • "today"     – live 24-hour forecast
  • "tomorrow"  – XGBoost ML prediction (trained districts only)
"""
import threading
import customtkinter as ctk
from . import theme
from . import data_bridge as db
from . import charts
import pandas as pd

# ── small reusable metric card ─────────────────────────────────────────────────

def _metric(parent, icon, value, label, color):
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


# ── main page class ────────────────────────────────────────────────────────────

class WeatherPage(ctk.CTkFrame):
    MODES = ("historic", "today", "tomorrow")

    def __init__(self, parent, *, app, mode: str = "historic"):
        assert mode in self.MODES
        c = theme.get()
        super().__init__(parent, fg_color=c["bg"], corner_radius=0)
        self._app  = app
        self.mode  = mode
        self._city = ""
        self._days = 7           # used in historic mode
        self._last_canvas = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        theme.on_change(self._retheme)

    # ── public API ────────────────────────────────────────────────────────────

    def set_city(self, city: str):
        self._city = city
        if hasattr(self, "_city_lbl"):
            self._city_lbl.configure(text=f"📍  {city}")
        if self.mode != "tomorrow":
            self._fetch()

    def on_show(self):
        pass

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        c = theme.get()
        # Outer scroll container
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=c["bg"],
            scrollbar_button_color=c["border"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        if self.mode == "historic":
            self._build_historic_header()
        elif self.mode == "today":
            self._build_today_header()
        else:
            self._build_tomorrow_header()

        # Status label
        self._status = ctk.CTkLabel(
            self._scroll, text="",
            font=theme.font(11), text_color=c["text_muted"],
        )
        self._status.grid(row=2, column=0, pady=4)

        # Chart container
        self._chart_zone = ctk.CTkFrame(
            self._scroll, fg_color="transparent",
        )
        self._chart_zone.grid(row=3, column=0, sticky="nsew",
                               padx=20, pady=(0, 20))
        self._chart_zone.grid_columnconfigure(0, weight=1)

    # ── Historic header ────────────────────────────────────────────────────────

    def _build_historic_header(self):
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(1, weight=1)

        # Page title
        ctk.CTkLabel(head, text="📊  Historic Weather Data",
                     font=theme.font(16, "bold"),
                     text_color=c["text"]).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=18, pady=(14, 6))

        # City display
        self._city_lbl = ctk.CTkLabel(head, text="📍  —",
                                       font=theme.font(11),
                                       text_color=c["text_muted"])
        self._city_lbl.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        # Timeline buttons
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

        # Metric card row (filled after fetch)
        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=2, column=0, columnspan=3,
                                sticky="ew", padx=14, pady=(0, 14))

    def _set_days(self, days: int):
        self._days = days
        if self._city:
            self._fetch()

    # ── Today header ──────────────────────────────────────────────────────────

    def _build_today_header(self):
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(head, text="☀️  Today's Forecast",
                     font=theme.font(16, "bold"),
                     text_color=c["text"]).grid(
            row=0, column=0, sticky="w", padx=18, pady=(14, 4))

        self._city_lbl = ctk.CTkLabel(head, text="📍  —",
                                       font=theme.font(11),
                                       text_color=c["text_muted"])
        self._city_lbl.grid(row=1, column=0, sticky="w", padx=18)

        # Condition label (filled after fetch)
        self._condition_lbl = ctk.CTkLabel(head, text="",
                                            font=theme.font(13),
                                            text_color=c["accent"])
        self._condition_lbl.grid(row=2, column=0, sticky="w", padx=18)

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=3, column=0, sticky="ew",
                                padx=14, pady=(6, 14))

    # ── Tomorrow header ────────────────────────────────────────────────────────

    def _build_tomorrow_header(self):
        c = theme.get()
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(head, text="🔮  Tomorrow's ML Prediction",
                     font=theme.font(16, "bold"),
                     text_color=c["text"]).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=18, pady=(14, 8))

        ctk.CTkLabel(head, text="State:", font=theme.font(12),
                     text_color=c["text_muted"]).grid(
            row=1, column=0, padx=(18, 4), pady=(0, 12))

        states = db.get_states()
        self._state_var = ctk.StringVar(value=states[0])
        self._state_menu = ctk.CTkOptionMenu(
            head, values=states, variable=self._state_var,
            width=160, height=34, font=theme.font(12),
            fg_color=c["card"], text_color=c["text"],
            button_color=c["accent"],
            command=self._on_state_change,
        )
        self._state_menu.grid(row=1, column=1, padx=(0, 12), pady=(0, 12))

        ctk.CTkLabel(head, text="District:", font=theme.font(12),
                     text_color=c["text_muted"]).grid(
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

        self._predict_btn = ctk.CTkButton(
            head, text="🔮  Predict Tomorrow",
            width=180, height=36, font=theme.font(12, "bold"),
            fg_color=c["accent"], hover_color=c["accent"],
            command=self._run_prediction,
        )
        self._predict_btn.grid(row=2, column=0, columnspan=4,
                                padx=18, pady=(0, 14))

        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=3, column=0, columnspan=4,
                                sticky="ew", padx=14, pady=(0, 14))

        # Notice about models
        notice = ctk.CTkFrame(self._scroll, fg_color=c["tag_bg"],
                               corner_radius=10, border_width=1,
                               border_color=c["border"])
        notice.grid(row=1, column=0, sticky="ew", padx=20, pady=(8, 0))
        ctk.CTkLabel(
            notice,
            text="ℹ️  Only trained districts (from geography.py) are available here.\n"
                 "If models are missing, run  python run_ml_pipeline.py  first.",
            font=theme.font(10),
            text_color=c["text_muted"],
            justify="left",
        ).pack(padx=14, pady=8, anchor="w")

    def _on_state_change(self, state: str):
        districts = db.get_districts(state)
        self._district_var.set(districts[0])
        self._district_menu.configure(values=districts)

    # ── Data fetching ─────────────────────────────────────────────────────────

    def _fetch(self):
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
            self.after(0, lambda: self._on_weather_ready(data))

        threading.Thread(target=worker, daemon=True).start()

    def _run_prediction(self):
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
            self.after(0, lambda: self._on_prediction_ready(result))

        threading.Thread(target=worker, daemon=True).start()

    # ── Callbacks ─────────────────────────────────────────────────────────────

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
        self._set_status("")
        self._predict_btn.configure(state="normal")
        if result is None:
            self._set_status("⚠️  Prediction failed. Ensure models are trained.")
            return

        pred_dict, hourly_df = result

        self._clear_metrics()
        self._clear_charts()
        
        # 1. Show the single value metrics
        self._populate_tomorrow_results(pred_dict)
        
        # 2. Draw the 24-hour graph exactly like the "Today" tab!
        dark = theme.is_dark()
        frame = ctk.CTkFrame(self._chart_zone, fg_color="transparent")
        frame.grid(row=1, column=0, sticky="ew", pady=(10, 0)) # Put below the gauge
        frame.grid_columnconfigure(0, weight=1)
        
        # Reuse your existing chart builder!
        fig = charts.hourly_forecast_chart(hourly_df, dark=dark)
        charts.embed(fig, frame)

    # ── Metric population ─────────────────────────────────────────────────────

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
        for i in range(5):
            row.grid_columnconfigure(i, weight=1)

        # Use the most recent reading
        latest = df.iloc[-1] if len(df) > 0 else df.iloc[0]
        code   = int(latest.get("weather_code", 0))
        icon   = db.WEATHER_ICONS.get(code, "🌡")
        cond   = db.WEATHER_LABELS.get(code, "—")
        if hasattr(self, "_condition_lbl"):
            self._condition_lbl.configure(
                text=f"{icon}  {cond}"
            )

        t_cur = f"{latest['temperature_2m']:.1f}°C"
        t_fl  = (f"{latest['apparent_temperature']:.1f}°C"
                 if "apparent_temperature" in df.columns else "—")
        h_cur = f"{latest['relative_humidity_2m']:.0f}%"
        w_cur = f"{latest['wind_speed_10m']:.1f} km/h"
        r_cur = f"{df['rain'].sum():.1f} mm"

        for i, (ico, val, lbl, col) in enumerate([
            ("🌡", t_cur, "Temperature",  c["accent3"]),
            ("🤔", t_fl,  "Feels Like",   c["warning"]),
            ("💧", h_cur, "Humidity",     c["rain"]),
            ("💨", w_cur, "Wind Speed",   c["accent2"]),
            ("🌧", r_cur, "Rain Total",   c["accent"]),
        ]):
            card = _metric(row, ico, val, lbl, col)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

    def _populate_tomorrow_results(self, result: dict):
        c   = theme.get()
        row = self._metrics_row
        for i in range(4):
            row.grid_columnconfigure(i, weight=1)

        temp = result.get("temperature_2m",    "—")
        feel = result.get("feels_like",         "—")
        humd = result.get("relative_humidity_2m", "—")
        rain = result.get("rain_probability",   "—")
        fdate = result.get("future_date", "Tomorrow")

        temp_s = f"{temp:.1f}°C" if isinstance(temp, float) else str(temp)
        feel_s = f"{feel:.1f}°C" if isinstance(feel, float) else str(feel)
        humd_s = f"{humd:.0f}%" if isinstance(humd, float) else str(humd)
        rain_s = f"{rain:.1f}%" if isinstance(rain, float) else str(rain)

        self._set_status(f"🗓  Forecast for: {fdate}")

        for i, (ico, val, lbl, col) in enumerate([
            ("🌡", temp_s, "Temperature",  c["accent3"]),
            ("🤔", feel_s, "Feels Like",   c["warning"]),
            ("💧", humd_s, "Humidity",     c["rain"]),
            ("🌧", rain_s, "Rain Chance",  c["accent"]),
        ]):
            card = _metric(row, ico, val, lbl, col)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

        # Rain probability gauge
        if isinstance(rain, float):
            gauge_frame = ctk.CTkFrame(
                self._chart_zone, fg_color="transparent",
            )
            gauge_frame.grid(row=0, column=0, pady=(10, 0), sticky="nsew")
            fig = charts.rain_probability_gauge(rain, dark=theme.is_dark())
            charts.embed(fig, gauge_frame)

    # ── Chart drawing ─────────────────────────────────────────────────────────

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
            frame = ctk.CTkFrame(
                self._chart_zone, fg_color="transparent",
            )
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

    # ── Helpers ───────────────────────────────────────────────────────────────

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