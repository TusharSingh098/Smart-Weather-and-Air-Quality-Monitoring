"""
app.py
Master Application Orchestrator & SPA Router.

The primary entry point for the GUI. Assembles the decoupled UI components,
manages global application state (like the actively searched city), and 
implements a highly efficient Single-Page Application (SPA) routing protocol.

Author: Team PyChaos
College: NIT Kurukshetra
"""

import os
import sys

# ─── Dynamic Environment Pathing ──────────────────────────────────────────────
# Ensures the Python interpreter can locate all internal project modules 
# regardless of the directory from which the script is executed.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import customtkinter as ctk

from ui_engine              import theme
from ui_engine.header       import HeaderBar
from ui_engine.sidebar      import SidebarNav
from ui_engine.page_home    import HomePage
from ui_engine.page_weather import WeatherPage
from ui_engine.page_aqi     import AQIPage

class WeatherApp(ctk.CTk):
    """Root application window and central Mediator."""

    WIN_W = 1300
    WIN_H = 780

    def __init__(self):
        super().__init__()
        
        # Bootstrap the global styling engine
        theme.init("dark")
        
        # Initialize global application state
        self._current_city = ""
        
        # Scaffolding sequence
        self._setup_window()
        self._build_layout()
        
        # Set default route
        self.show_page("home")
        
        # Subscribe to Pub/Sub theme engine
        theme.on_change(self._retheme)
        
        # OS-Level Event Binding: Trap the "X" button click
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ─── OS Window Configuration ──────────────────────────────────────────────

    def _setup_window(self):
        """Configures OS window properties, centering it perfectly on the user's monitor."""
        self.title("Smart Weather & Air Quality Monitor  |  NIT Kurukshetra")
        w, h = self.WIN_W, self.WIN_H
        
        # Screen geometry math for perfect center alignment
        sw   = self.winfo_screenwidth()
        sh   = self.winfo_screenheight()
        x    = (sw - w) // 2
        y    = (sh - h) // 2
        
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(960, 620) # Prevent UI distortion from excessive shrinking
        self.configure(fg_color=theme.get()["bg"])

        self.after(0, lambda: self.state("zoomed"))

    # ─── Component Assembly ───────────────────────────────────────────────────

    def _build_layout(self):
        """Instantiates and grids the core layout and all sub-pages."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Instantiate Header (Injecting Mediator Callbacks)
        self._header = HeaderBar(
            self,
            on_search=self._on_search,
            on_team=self._open_team,
            on_theme=theme.toggle,
        )
        self._header.grid(row=0, column=0, columnspan=2, sticky="nsew")

        # 2. Instantiate Sidebar (Injecting Routing Callbacks)
        self._sidebar = SidebarNav(self, on_navigate=self._on_navigate)
        self._sidebar.grid(row=1, column=0, sticky="nsew")

        # 3. Establish the Content 'Stage'
        c = theme.get()
        self._content = ctk.CTkFrame(self, fg_color=c["bg"], corner_radius=0)
        self._content.grid(row=1, column=1, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        # 4. SPA Page Pre-fetching
        # Instantiate all views simultaneously into RAM to eliminate load times during navigation
        self._pages = {
            "home":             HomePage(self._content,    app=self),
            "weather_historic": WeatherPage(self._content, app=self, mode="historic"),
            "weather_today":    WeatherPage(self._content, app=self, mode="today"),
            "weather_tomorrow": WeatherPage(self._content, app=self, mode="tomorrow"),
            "diagnostics":      WeatherPage(self._content, app=self, mode="diagnostics"),
            "aqi":              AQIPage(self._content,     app=self)
        }
        
        # Stack all pages precisely on top of one another
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self._active: str = ""

    # ─── Single-Page Application (SPA) Routing ────────────────────────────────

    def show_page(self, name: str, **kwargs):
        """
        The core SPA routing protocol.
        Brings the requested memory-cached frame to the top of the UI stack
        and forwards any updated system state.
        """
        if name not in self._pages:
            return
            
        # Z-Index manipulation: Instantly swaps the view with zero rendering overhead
        self._pages[name].tkraise()
        self._active = name

        # Forward dynamic routing arguments to the target page
        page = self._pages[name]
        if "days" in kwargs and hasattr(page, "set_days"):
            page.set_days(kwargs["days"])
        if hasattr(page, "on_show"):
            page.on_show()

        # State propagation: Ensure the new page inherits the globally active city
        if self._current_city and name not in ("weather_tomorrow", "home", "diagnostics"):
            if hasattr(page, "set_city"):
                page.set_city(self._current_city)

    # ─── Mediator Callbacks ───────────────────────────────────────────────────

    def _on_navigate(self, name: str, **kwargs):
        """Triggered by the SidebarNav."""
        self.show_page(name, **kwargs)

    def _on_search(self, city: str):
        """
        Triggered by the HeaderBar.
        Updates global state and forces an automatic route to the live forecast.
        """
        self._current_city = city
        
        # If searching from Home, automatically route to the live Today view
        if self._active in ("home", ""):
            self.show_page("weather_today")
            
        # Force the active page to pull new API data
        page = self._pages.get(self._active)
        if page and hasattr(page, "set_city") and self._active not in ("weather_tomorrow", "diagnostics"):
            page.set_city(city)

    def _open_team(self):
        """Spawns the modal attribution overlay."""
        from ui_engine.team_popup import TeamPopup
        TeamPopup(self)

    def _retheme(self):
        """Updates the root OS window background when a theme toggle is broadcast."""
        c = theme.get()
        self.configure(fg_color=c["bg"])
        self._content.configure(fg_color=c["bg"])

    def _on_closing(self):
        """
        Memory Management & Thread Killing.
        Forcefully kills the Python process at the OS level to ensure any 
        lingering API fetching daemon threads are instantly terminated.
        """
        self.quit()
        self.destroy()
        os._exit(0)

# ─── Executable Entry Point ───────────────────────────────────────────────────

def main():
    """Bootstraps the application class and starts the infinite GUI event loop."""
    app = WeatherApp()
    app.mainloop()

if __name__ == "__main__":
    main()
