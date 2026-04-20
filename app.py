"""
ui_engine/main.py
Main application window.  Entry point for the Weather Monitor GUI.

Run from the project root:
    python -m ui_engine.main
  or:
    python ui_engine/main.py
"""
import os
import sys

# Ensure project root is on the import path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk

from ui_engine import theme
from ui_engine.header      import HeaderBar
from ui_engine.sidebar     import SidebarNav
from ui_engine.page_home   import HomePage
from ui_engine.page_weather import WeatherPage
from ui_engine.page_aqi    import AQIPage


class WeatherApp(ctk.CTk):
    """Root application window."""

    WIN_W = 1300
    WIN_H = 780

    def __init__(self):
        super().__init__()
        theme.init("dark")
        self._current_city = ""
        self._setup_window()
        self._build_layout()
        self.show_page("home")
        theme.on_change(self._retheme)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ── window setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        self.title("Smart Weather & Air Quality Monitor  |  NIT Kurukshetra")
        w, h = self.WIN_W, self.WIN_H
        sw   = self.winfo_screenwidth()
        sh   = self.winfo_screenheight()
        x    = (sw - w) // 2
        y    = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(960, 620)
        self.configure(fg_color=theme.get()["bg"])

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── header ────────────────────────────────────────────────────────────
        self._header = HeaderBar(
            self,
            on_search=self._on_search,
            on_team=self._open_team,
            on_theme=theme.toggle,
        )
        self._header.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # ── sidebar ───────────────────────────────────────────────────────────
        self._sidebar = SidebarNav(self, on_navigate=self._on_navigate)
        self._sidebar.grid(row=1, column=0, sticky="nsew")

        # ── content area ──────────────────────────────────────────────────────
        c = theme.get()
        self._content = ctk.CTkFrame(self, fg_color=c["bg"], corner_radius=0)
        self._content.grid(row=1, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # Instantiate all pages once and layer them
        self._pages = {
            "home":             HomePage(self._content,    app=self),
            "weather_historic": WeatherPage(self._content, app=self, mode="historic"),
            "weather_today":    WeatherPage(self._content, app=self, mode="today"),
            "weather_tomorrow": WeatherPage(self._content, app=self, mode="tomorrow"),
            "aqi":              AQIPage(self._content,     app=self),
        }
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._active: str = ""

    # ── public API (used by pages) ────────────────────────────────────────────

    def show_page(self, name: str, **kwargs):
        """Raise a page by name.  Extra kwargs forwarded to the page."""
        if name not in self._pages:
            return
        self._pages[name].tkraise()
        self._active = name

        # Forward kwargs to the page
        page = self._pages[name]
        if "days" in kwargs and hasattr(page, "set_days"):
            page.set_days(kwargs["days"])
        if hasattr(page, "on_show"):
            page.on_show()

        # If a city is already selected, push it to the new page
        if self._current_city and name != "weather_tomorrow" and name != "home":
            if hasattr(page, "set_city"):
                page.set_city(self._current_city)

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _on_navigate(self, name: str, **kwargs):
        self.show_page(name, **kwargs)

    def _on_search(self, city: str):
        self._current_city = city
        if self._active in ("home", ""):
            self.show_page("weather_today")
        page = self._pages.get(self._active)
        if page and hasattr(page, "set_city") and self._active != "weather_tomorrow":
            page.set_city(city)

    def _open_team(self):
        from ui_engine.team_popup import TeamPopup
        TeamPopup(self)

    def _retheme(self):
        c = theme.get()
        self.configure(fg_color=c["bg"])
        self._content.configure(fg_color=c["bg"])

    def _on_closing(self):
        """Forcefully kills the app and all lingering background threads."""
        self.quit()
        self.destroy()
        os._exit(0)


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    main()