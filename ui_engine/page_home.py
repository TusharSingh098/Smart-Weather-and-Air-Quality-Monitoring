"""
ui_engine/page_home.py
Welcome / home screen shown when the app first opens.
"""
import datetime
import customtkinter as ctk
from . import theme

_FEATURES = [
    {
        "icon":  "📊",
        "title": "Historic Analysis",
        "desc":  "Explore weather trends\nover last day, week or month",
        "page":  "weather_historic",
        "color": "#FF8C42",
    },
    {
        "icon":  "☀️",
        "title": "Today's Forecast",
        "desc":  "Live 24-hour weather\nforecast for any city",
        "page":  "weather_today",
        "color": "#FFD166",
    },
    {
        "icon":  "🔮",
        "title": "AI Prediction",
        "desc":  "XGBoost ML model predicts\ntomorrow's weather",
        "page":  "weather_tomorrow",
        "color": "#2F81F7",
    },
    {
        "icon":  "🌫",
        "title": "AQI Monitor",
        "desc":  "Air quality report with\nPM2.5, PM10 & more",
        "page":  "aqi",
        "color": "#00C9A7",
    },
]

_COVERAGE = [
    "Haryana (6 districts)",
    "West Bengal (3 districts)",
    "Uttar Pradesh (11 districts)",
]


class HomePage(ctk.CTkFrame):
    def __init__(self, parent, *, app):
        c = theme.get()
        super().__init__(parent, fg_color=c["bg"], corner_radius=0)
        self._app = app
        self._build(c)
        theme.on_change(self._retheme)

    def _build(self, c):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── outer scroll frame ────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=c["bg"],
            scrollbar_button_color=c["border"],
        )
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        # ── hero banner ───────────────────────────────────────────────────────
        banner = ctk.CTkFrame(
            self._scroll,
            fg_color=c["surface"],
            corner_radius=16,
            border_width=1,
            border_color=c["border"],
        )
        banner.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 16))
        banner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            banner,
            text="🌍",
            font=theme.font(52),
        ).grid(row=0, column=0, pady=(24, 0))

        ctk.CTkLabel(
            banner,
            text="Smart Weather & Air Quality Monitor",
            font=theme.font(24, "bold"),
            text_color=c["text"],
        ).grid(row=1, column=0, pady=(4, 0))

        ctk.CTkLabel(
            banner,
            text="Powered by Open-Meteo API  ·  XGBoost ML  ·  Real-time Data",
            font=theme.font(12),
            text_color=c["text_muted"],
        ).grid(row=2, column=0, pady=(2, 0))

        # Date
        today_str = datetime.date.today().strftime("%A, %B %d, %Y")
        ctk.CTkLabel(
            banner,
            text=f"📅  {today_str}",
            font=theme.font(11),
            text_color=c["accent"],
        ).grid(row=3, column=0, pady=(8, 20))

        # ── feature cards ─────────────────────────────────────────────────────
        ctk.CTkLabel(
            self._scroll,
            text="EXPLORE",
            font=theme.font(10),
            text_color=c["text_dim"],
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(4, 8))

        cards_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        cards_frame.grid(row=2, column=0, sticky="ew", padx=24)
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)

        for i, feat in enumerate(_FEATURES):
            self._feature_card(cards_frame, feat, i)

        # ── quick start hint ──────────────────────────────────────────────────
        hint = ctk.CTkFrame(
            self._scroll,
            fg_color=c["card"],
            corner_radius=12,
            border_width=1,
            border_color=c["border"],
        )
        hint.grid(row=3, column=0, sticky="ew", padx=24, pady=(18, 8))

        ctk.CTkLabel(
            hint,
            text="💡  Quick start",
            font=theme.font(13, "bold"),
            text_color=c["text"],
        ).pack(anchor="w", padx=18, pady=(14, 4))

        steps = [
            "1.  Type a city name in the search bar above and press Enter.",
            "2.  Click  Weather → Today's Forecast  for the live 24-hour outlook.",
            "3.  Use  Weather → Historic Data  to explore trends over time.",
            "4.  Try  Weather → Tomorrow (ML)  for AI-powered next-day predictions.",
            "5.  Switch to  Air Quality  to view PM2.5 / PM10 levels.",
        ]
        for s in steps:
            ctk.CTkLabel(
                hint, text=s,
                font=theme.font(11),
                text_color=c["text_muted"],
                anchor="w",
                justify="left",
            ).pack(anchor="w", padx=18, pady=1)

        # ── coverage badge row ────────────────────────────────────────────────
        cov_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        cov_frame.grid(row=4, column=0, sticky="w", padx=24, pady=(12, 24))

        ctk.CTkLabel(
            cov_frame,
            text="📍 Coverage: ",
            font=theme.font(11),
            text_color=c["text_muted"],
        ).pack(side="left")

        for region in _COVERAGE:
            tag = ctk.CTkFrame(
                cov_frame,
                fg_color=c["tag_bg"],
                corner_radius=8,
                border_width=1,
                border_color=c["border"],
            )
            tag.pack(side="left", padx=4)
            ctk.CTkLabel(
                tag, text=region,
                font=theme.font(10),
                text_color=c["text_muted"],
            ).pack(padx=10, pady=3)

    def _feature_card(self, parent, feat: dict, col: int):
        c = theme.get()
        card = ctk.CTkFrame(
            parent,
            fg_color=c["card"],
            corner_radius=14,
            border_width=1,
            border_color=c["border"],
            cursor="hand2",
        )
        card.grid(row=0, column=col, padx=6, pady=0, sticky="nsew")

        ctk.CTkLabel(card, text=feat["icon"],
                     font=theme.font(32)).pack(pady=(18, 4))

        ctk.CTkLabel(card, text=feat["title"],
                     font=theme.font(13, "bold"),
                     text_color=feat["color"]).pack()

        ctk.CTkLabel(card, text=feat["desc"],
                     font=theme.font(10),
                     text_color=c["text_muted"],
                     justify="center").pack(pady=(4, 14))

        # Clicking card navigates
        page = feat["page"]
        for w in [card] + card.winfo_children():
            w.bind("<Button-1>", lambda _e, p=page: self._app.show_page(p))

    def on_show(self):
        pass

    def _retheme(self):
        # Simplest approach: rebuild the whole frame
        for w in self.winfo_children():
            w.destroy()
        self._build(theme.get())