"""
ui_engine/page_aqi.py
Air Quality Index page – shows PM2.5/PM10 trend, pollutant bars, and
a half-circle AQI gauge for last 1 / 7 / 30 days.
"""
import threading
import customtkinter as ctk
from . import theme
from . import data_bridge as db
from . import charts

# ── metric card helper ─────────────────────────────────────────────────────────

def _metric(parent, icon, value, label, color):
    c = theme.get()
    card = ctk.CTkFrame(parent, fg_color=c["card"],
                        corner_radius=12, border_width=1,
                        border_color=c["border"])
    ctk.CTkLabel(card, text=icon, font=theme.font(20)).pack(pady=(10, 0))
    ctk.CTkLabel(card, text=str(value),
                 font=theme.font(18, "bold"),
                 text_color=color).pack()
    ctk.CTkLabel(card, text=label,
                 font=theme.font(10),
                 text_color=c["text_muted"]).pack(pady=(2, 10))
    return card


class AQIPage(ctk.CTkFrame):
    TIMELINES = {"Last Day": 1, "Last Week": 7, "Last Month": 30}

    def __init__(self, parent, *, app):
        c = theme.get()
        super().__init__(parent, fg_color=c["bg"], corner_radius=0)
        self._app  = app
        self._city = ""
        self._days = 7

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        theme.on_change(self._retheme)

    # ── public API ─────────────────────────────────────────────────────────────

    def set_city(self, city: str):
        self._city = city
        if hasattr(self, "_city_lbl"):
            self._city_lbl.configure(text=f"📍  {city}")
        self._fetch()

    def set_days(self, days: int):
        self._days = days
        # Highlight the matching button
        for lbl, d in self.TIMELINES.items():
            btn = self._tl_btns.get(lbl)
            if btn:
                c = theme.get()
                if d == days:
                    btn.configure(fg_color=c["accent2"],
                                   text_color="#FFFFFF")
                else:
                    btn.configure(fg_color=c["card"],
                                   text_color=c["text_muted"])
        if self._city:
            self._fetch()

    def on_show(self):
        pass

    # ── build ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        c = theme.get()
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=c["bg"],
            scrollbar_button_color=c["border"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        # ── header card ────────────────────────────────────────────────────────
        head = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=14, border_width=1,
                            border_color=c["border"])
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 0))
        head.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(head, text="🌫  Air Quality Report",
                     font=theme.font(16, "bold"),
                     text_color=c["text"]).grid(
            row=0, column=0, columnspan=2, sticky="w",
            padx=18, pady=(14, 6))

        self._city_lbl = ctk.CTkLabel(head, text="📍  —",
                                       font=theme.font(11),
                                       text_color=c["text_muted"])
        self._city_lbl.grid(row=1, column=0, sticky="w", padx=18)

        # Timeline buttons
        tl_frame = ctk.CTkFrame(head, fg_color="transparent")
        tl_frame.grid(row=1, column=1, sticky="e", padx=18)
        self._tl_btns = {}
        for lbl, d in self.TIMELINES.items():
            btn = ctk.CTkButton(
                tl_frame, text=lbl, width=100, height=32,
                font=theme.font(11),
                fg_color=c["accent2"] if d == 7 else c["card"],
                text_color="#fff" if d == 7 else c["text_muted"],
                border_width=1, border_color=c["border"],
                hover_color=c["btn_hover"],
                command=lambda days=d: self.set_days(days),
            )
            btn.pack(side="left", padx=4)
            self._tl_btns[lbl] = btn

        # Metric row
        self._metrics_row = ctk.CTkFrame(head, fg_color="transparent")
        self._metrics_row.grid(row=2, column=0, columnspan=2,
                                sticky="ew", padx=14, pady=(6, 14))

        # Status
        self._status = ctk.CTkLabel(
            self._scroll, text="Enter a city via the search bar to load AQI data.",
            font=theme.font(11), text_color=c["text_muted"],
        )
        self._status.grid(row=1, column=0, pady=8)

        # Chart containers
        self._gauge_row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._gauge_row.grid(row=2, column=0, sticky="ew",
                              padx=20, pady=(4, 0))
        self._gauge_row.grid_columnconfigure(0, weight=2)
        self._gauge_row.grid_columnconfigure(1, weight=3)

        self._gauge_frame = ctk.CTkFrame(self._gauge_row,
                                          fg_color="transparent")
        self._gauge_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._bar_frame = ctk.CTkFrame(self._gauge_row,
                                        fg_color="transparent")
        self._bar_frame.grid(row=0, column=1, sticky="nsew")

        self._trend_frame = ctk.CTkFrame(self._scroll,
                                          fg_color="transparent")
        self._trend_frame.grid(row=3, column=0, sticky="ew",
                                padx=20, pady=(8, 20))
        self._trend_frame.grid_columnconfigure(0, weight=1)

        # AQI legend
        self._build_legend()

    def _build_legend(self):
        c = theme.get()
        leg = ctk.CTkFrame(self._scroll, fg_color=c["surface"],
                            corner_radius=12, border_width=1,
                            border_color=c["border"])
        leg.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))

        ctk.CTkLabel(leg, text="AQI Scale (PM2.5  μg/m³)",
                     font=theme.font(11, "bold"),
                     text_color=c["text"]).pack(anchor="w", padx=14, pady=(10, 6))

        row = ctk.CTkFrame(leg, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))

        for lo, hi, color, label in db.AQI_BANDS:
            band = ctk.CTkFrame(row, fg_color=color, corner_radius=6, height=22)
            band.pack(side="left", expand=True, fill="x", padx=2)
            band.pack_propagate(False)
            ctk.CTkLabel(band, text=label,
                          font=theme.font(8),
                          text_color="#000000").pack(expand=True)

    # ── fetch & callbacks ──────────────────────────────────────────────────────

    def _fetch(self):
        if not self._city:
            return
        self._set_status("⏳  Loading AQI data…")

        city = self._city
        days = self._days

        def worker():
            data = db.fetch_historic_aqi(city, days)
            self.after(0, lambda: self._on_data_ready(data))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data_ready(self, df):
        self._set_status("")
        if df is None or df.empty:
            self._set_status("⚠️  No AQI data returned.")
            return

        self._clear_metrics()
        self._clear_charts()

        # ── metrics ────────────────────────────────────────────────────────────
        c = theme.get()
        for i in range(5):
            self._metrics_row.grid_columnconfigure(i, weight=1)

        pm25_avg = df["pm2_5"].mean() if "pm2_5" in df.columns else 0
        pm10_avg = df["pm10"].mean()  if "pm10"  in df.columns else 0
        pm25_max = df["pm2_5"].max()  if "pm2_5" in df.columns else 0
        o3_avg   = df["ozone"].mean() if "ozone" in df.columns else 0
        no2_avg  = df["nitrogen_dioxide"].mean() if "nitrogen_dioxide" in df.columns else 0

        lvl, col = db.aqi_level(pm25_avg)

        for i, (ico, val, lbl, color) in enumerate([
            ("🔴", f"{pm25_avg:.1f}", "Avg PM2.5", col),
            ("🟠", f"{pm10_avg:.1f}", "Avg PM10",  c["warning"]),
            ("🔺", f"{pm25_max:.1f}", "Peak PM2.5", c["danger"]),
            ("🌀", f"{o3_avg:.1f}",   "Avg O₃",    c["accent2"]),
            ("🟡", f"{no2_avg:.1f}",  "Avg NO₂",   c["accent3"]),
        ]):
            card = _metric(self._metrics_row, ico, val, lbl, color)
            card.grid(row=0, column=i, padx=4, sticky="nsew")

        # AQI level badge
        badge = ctk.CTkFrame(
            self._metrics_row, fg_color=col, corner_radius=8, height=32,
        )
        badge.grid(row=1, column=0, columnspan=5,
                   sticky="ew", padx=4, pady=(6, 0))
        ctk.CTkLabel(badge, text=f"Air Quality: {lvl}",
                     font=theme.font(12, "bold"),
                     text_color="#000000").pack(pady=4)

        # ── charts ─────────────────────────────────────────────────────────────
        dark = theme.is_dark()
        days = self._days

        gauge_fig = charts.aqi_gauge(pm25_avg, dark=dark)
        charts.embed(gauge_fig, self._gauge_frame)

        bar_fig = charts.pollutant_bars(df, dark=dark)
        if bar_fig:
            charts.embed(bar_fig, self._bar_frame)

        trend_fig = charts.aqi_trend_chart(df, days=days, dark=dark)
        charts.embed(trend_fig, self._trend_frame)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _clear_metrics(self):
        for w in self._metrics_row.winfo_children():
            w.destroy()

    def _clear_charts(self):
        for frame in (self._gauge_frame, self._bar_frame, self._trend_frame):
            for w in frame.winfo_children():
                w.destroy()

    def _set_status(self, msg: str):
        self._status.configure(text=msg)

    def _retheme(self):
        c = theme.get()
        self.configure(fg_color=c["bg"])
        if hasattr(self, "_scroll"):
            self._scroll.configure(fg_color=c["bg"])