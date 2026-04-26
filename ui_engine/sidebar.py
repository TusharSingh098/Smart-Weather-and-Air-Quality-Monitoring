"""
ui_engine/sidebar.py
Accordion Navigation & Deep-Link Routing Controller.

Constructs the left-side navigation panel. Features custom-built expandable 
accordion menus (Weather, AQI) and dynamic active-state highlighting. Uses 
Dependency Injection to pass routing commands back to the main app controller.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import customtkinter as ctk
from . import theme

class SidebarNav(ctk.CTkFrame):
    """
    Vertical navigation controller managing view routing.
    """
    WIDTH = 230

    def __init__(self, parent, *, on_navigate):
        c = theme.get()
        super().__init__(
            parent,
            fg_color=c["surface"],
            corner_radius=0,
            width=self.WIDTH,
            border_width=0,
        )
        self.pack_propagate(False) # Locks the width to exactly 230px
        
        # Injected Callback
        self._on_navigate = on_navigate
        
        # Accordion State Flags
        self._weather_open = False
        self._aqi_open     = False
        
        self._c = c
        self._active = None
        self._build()
        
        theme.on_change(self._retheme)

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build(self):
        """Scaffolds the accordion groups, buttons, and visual separators."""
        c = self._c
        # Cache references to all buttons for rapid re-theming iterations
        self._btn_refs = []

        # ── Top Spacer & Label ──
        ctk.CTkFrame(self, fg_color="transparent", height=12).pack()

        self._nav_lbl = ctk.CTkLabel(
            self, text="NAVIGATION", font=theme.font(9), text_color=c["text_dim"],
        )
        self._nav_lbl.pack(anchor="w", padx=18, pady=(4, 6))

        # ── Weather Accordion Group ──
        self._weather_btn = self._group_btn("🌤  Weather", self._toggle_weather)

        # Container for the nested weather buttons
        self._weather_sub = ctk.CTkFrame(self, fg_color="transparent")
        self._weather_sub.pack(fill="x")

        self._historic_btn = self._sub_btn(
            self._weather_sub, "📊  Historic Data",
            lambda: self._nav("weather_historic"),
        )
        self._today_btn = self._sub_btn(
            self._weather_sub, "☀️  Today's Forecast",
            lambda: self._nav("weather_today"),
        )
        self._tomorrow_btn = self._sub_btn(
            self._weather_sub, "🔮  Tomorrow (ML)",
            lambda: self._nav("weather_tomorrow"),
        )
        self._diagnostics_btn = self._sub_btn(
            self._weather_sub, "🔬  AI Diagnostics",
            lambda: self._nav("diagnostics"), 
        )
        # Initialize collapsed state to save vertical screen real estate
        self._weather_sub.pack_forget()

        # ── Visual Separator ──
        self._sep1 = ctk.CTkFrame(self, fg_color=c["border"], height=1, corner_radius=0)
        self._sep1.pack(fill="x", padx=14, pady=6)

        # ── AQI Accordion Group ──
        self._aqi_btn = self._group_btn("🌫  Air Quality", self._toggle_aqi)

        self._aqi_sub = ctk.CTkFrame(self, fg_color="transparent")
        self._aqi_sub.pack(fill="x")

        self._aqi_day_btn   = self._sub_btn(
            self._aqi_sub, "📅  Last Day", lambda: self._nav("aqi", days=1),
        )
        self._aqi_week_btn  = self._sub_btn(
            self._aqi_sub, "📅  Last Week", lambda: self._nav("aqi", days=7),
        )
        self._aqi_month_btn = self._sub_btn(
            self._aqi_sub, "📅  Last Month", lambda: self._nav("aqi", days=30),
        )
        self._aqi_sub.pack_forget()

        # ── Visual Separator ──
        self._sep2 = ctk.CTkFrame(self, fg_color=c["border"], height=1, corner_radius=0)
        self._sep2.pack(fill="x", padx=14, pady=6)

        # Push everything up using an expanding invisible filler frame
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        # Right-side vertical border separating sidebar from main content
        sep_r = ctk.CTkFrame(self, fg_color=c["border"], width=1, corner_radius=0)
        sep_r.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")

    # ─── UI Component Factories ───────────────────────────────────────────────

    def _group_btn(self, text: str, cmd) -> ctk.CTkButton:
        """Generates top-level accordion toggle buttons."""
        c = self._c
        btn = ctk.CTkButton(
            self, text=text, font=theme.font(13, "bold"),
            fg_color="transparent", text_color=c["text"],
            hover_color=c["btn_hover"], anchor="w",
            height=40, corner_radius=8, command=cmd,
        )
        btn.pack(fill="x", padx=10, pady=1)
        self._btn_refs.append(("group", btn))
        return btn

    def _sub_btn(self, parent, text: str, cmd) -> ctk.CTkButton:
        """Generates indented nested routing buttons."""
        c = self._c
        btn = ctk.CTkButton(
            parent, text="   " + text, font=theme.font(12),
            fg_color="transparent", text_color=c["text_muted"],
            hover_color=c["btn_hover"], anchor="w",
            height=34, corner_radius=8, command=cmd,
        )
        btn.pack(fill="x", padx=10, pady=1)
        self._btn_refs.append(("sub", btn))
        return btn

    # ─── Accordion Toggle Logic ───────────────────────────────────────────────

    def _toggle_weather(self):
        """Flips boolean state, repacks/unpacks sub-menu, and updates UI arrow."""
        self._weather_open = not self._weather_open
        if self._weather_open:
            # Inject sub-menu exactly beneath the parent button
            self._weather_sub.pack(fill="x", after=self._weather_btn)
        else:
            self._weather_sub.pack_forget()
            
        arrow = "▼" if self._weather_open else "▶"
        self._weather_btn.configure(text=f"🌤  Weather  {arrow}")

    def _toggle_aqi(self):
        self._aqi_open = not self._aqi_open
        if self._aqi_open:
            self._aqi_sub.pack(fill="x", after=self._aqi_btn)
        else:
            self._aqi_sub.pack_forget()
            
        arrow = "▼" if self._aqi_open else "▶"
        self._aqi_btn.configure(text=f"🌫  Air Quality  {arrow}")

    # ─── Navigation Execution ──────────────────────────────────────────────────

    def _nav(self, page: str, **kwargs):
        """Applies active-state highlight logic before firing the injected routing callback."""
        self._highlight(page, kwargs.get("days"))
        self._on_navigate(page, **kwargs)

    def _highlight(self, page: str, days=None):
        """
        Iterates through mapped routes and applies contrasting brand colors 
        to indicate spatial location to the user.
        """
        c = self._c
        key = page if not days else f"aqi_{days}"

        # Hash map of active route strings to Tkinter button objects
        btn_map = {
            "weather_historic": self._historic_btn,
            "weather_today":    self._today_btn,
            "weather_tomorrow": self._tomorrow_btn,
            "diagnostics":      self._diagnostics_btn,
            "aqi_1":            self._aqi_day_btn,
            "aqi_7":            self._aqi_week_btn,
            "aqi_30":           self._aqi_month_btn,
        }
        
        for k, b in btn_map.items():
            if k == key:
                # Active Route Styling
                b.configure(fg_color=c["accent"], text_color="#FFFFFF")
            else:
                # Inactive Route Styling
                b.configure(fg_color="transparent", text_color=c["text_muted"])

    # ─── Pub/Sub Theming Execution ─────────────────────────────────────────────

    def _retheme(self):
        """Updates internal frame elements and iterates through cached button references."""
        c = theme.get()
        self._c = c
        self.configure(fg_color=c["surface"])
        self._nav_lbl.configure(text_color=c["text_dim"])
        self._sep1.configure(fg_color=c["border"])
        self._sep2.configure(fg_color=c["border"])
        
        for kind, btn in self._btn_refs:
            btn.configure(
                text_color=c["text"] if kind == "group" else c["text_muted"],
                hover_color=c["btn_hover"],
            )