"""
ui_engine/theme.py
Global Styling & Pub/Sub Appearance Engine.

Manages the aesthetic state of the application. Provides strict hexadecimal 
color dictionaries and typography factories. Implements an Observer (Pub/Sub) 
pattern to broadcast instantaneous Dark/Light mode toggles across all active 
UI components.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import customtkinter as ctk
from typing import Literal

# ─── Strict Color Palettes ───────────────────────────────────────────────────

# High-contrast, developer-centric dark mode (Inspired by GitHub Dark Dimmed)
DARK = {
    "bg":          "#0D1117",  # Deepest background
    "surface":     "#161B22",  # Elevated frames (Sidebar/Header)
    "card":        "#1C2128",  # Content containers
    "card2":       "#22272E",  # Secondary content containers
    "border":      "#30363D",  # Subtle dividers
    "accent":      "#2F81F7",  # Primary brand blue
    "accent2":     "#00C9A7",  # Teal highlights
    "accent3":     "#FF8C42",  # Warm orange highlights
    "text":        "#E6EDF3",  # Primary reading text
    "text_muted":  "#8B949E",  # Secondary/subtext
    "text_dim":    "#484F58",  # Tertiary/inactive text
    "success":     "#3FB950",  # Positive status
    "warning":     "#D29922",  # Caution status
    "danger":      "#F85149",  # Critical status
    "rain":        "#58A6FF",  # Meteorological specific blue
    "chart_bg":    "#161B22",  # Matplotlib figure background
    "chart_grid":  "#21262D",  # Matplotlib axis gridlines
    "btn_hover":   "#21262D",  # Button interaction state
    "tag_bg":      "#1C2128",  # Small badge backgrounds
}

# High-legibility light mode (Inspired by GitHub Light Default)
LIGHT = {
    "bg":          "#F0F4F8",
    "surface":     "#FFFFFF",
    "card":        "#FFFFFF",
    "card2":       "#F3F4F6",
    "border":      "#D0D7DE",
    "accent":      "#0969DA",
    "accent2":     "#1B7A6E",
    "accent3":     "#D05A00",
    "text":        "#1F2328",
    "text_muted":  "#656D76",
    "text_dim":    "#9AA0AA",
    "success":     "#1A7F37",
    "warning":     "#9A6700",
    "danger":      "#CF222E",
    "rain":        "#0550AE",
    "chart_bg":    "#FFFFFF",
    "chart_grid":  "#EAEEF2",
    "btn_hover":   "#F3F4F6",
    "tag_bg":      "#EEF1F5",
}

# ─── Global State & Observer Registry ────────────────────────────────────────

_mode = "dark"           # Default operational state
_listeners: list = []    # Array of callback functions from subscribed UI components

def init(mode: str = "dark"):
    """Bootstraps the underlying CustomTkinter theme engine."""
    global _mode
    _mode = mode
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")

def get() -> dict:
    """Returns the currently active hexadecimal palette."""
    return DARK if _mode == "dark" else LIGHT

def is_dark() -> bool:
    """Boolean helper for logic gates in UI components."""
    return _mode == "dark"

def toggle():
    """
    State Mutator & Broadcast Trigger.
    Flips the global state string, updates the OS-level UI rendering, 
    and iterates through the subscriber registry to execute localized redraws.
    """
    global _mode
    _mode = "light" if _mode == "dark" else "dark"
    ctk.set_appearance_mode(_mode)
    
    # Broadcast to all registered subscribers
    for fn in list(_listeners):
        try:
            fn()
        except Exception:
            # Defensive programming: If a component was destroyed but forgot 
            # to unregister, ignore the error and proceed to the next listener.
            pass

def on_change(fn):
    """
    Registration hook for the Observer Pattern.
    UI modules pass their localized `_retheme` function here during initialization.
    """
    _listeners.append(fn)

# ─── Typography Factories ─────────────────────────────────────────────────────

def font(size: int = 13, weight: Literal["normal", "bold"] = "normal") -> ctk.CTkFont:
    """Standardized scalable font constructor for primary UI text."""
    return ctk.CTkFont(family="Helvetica", size=size, weight=weight)

def mono(size: int = 12) -> ctk.CTkFont:
    """Monospaced font constructor for numerical data alignment."""
    return ctk.CTkFont(family="Courier", size=size)