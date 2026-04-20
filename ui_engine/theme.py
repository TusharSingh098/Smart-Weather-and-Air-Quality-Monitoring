"""
ui_engine/theme.py
Color palette and appearance management for the Weather Monitor GUI.
"""
import customtkinter as ctk
from typing import Literal

# ─── Palettes ────────────────────────────────────────────────────────────────

DARK = {
    "bg":          "#0D1117",
    "surface":     "#161B22",
    "card":        "#1C2128",
    "card2":       "#22272E",
    "border":      "#30363D",
    "accent":      "#2F81F7",
    "accent2":     "#00C9A7",
    "accent3":     "#FF8C42",
    "text":        "#E6EDF3",
    "text_muted":  "#8B949E",
    "text_dim":    "#484F58",
    "success":     "#3FB950",
    "warning":     "#D29922",
    "danger":      "#F85149",
    "rain":        "#58A6FF",
    "chart_bg":    "#161B22",
    "chart_grid":  "#21262D",
    "btn_hover":   "#21262D",
    "tag_bg":      "#1C2128",
}

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

# ─── State ───────────────────────────────────────────────────────────────────

_mode = "dark"
_listeners: list = []


def init(mode: str = "dark"):
    global _mode
    _mode = mode
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme("blue")


def get() -> dict:
    return DARK if _mode == "dark" else LIGHT


def is_dark() -> bool:
    return _mode == "dark"


def toggle():
    global _mode
    _mode = "light" if _mode == "dark" else "dark"
    ctk.set_appearance_mode(_mode)
    for fn in list(_listeners):
        try:
            fn()
        except Exception:
            pass


def on_change(fn):
    """Register a callback for theme changes."""
    _listeners.append(fn)


# ─── Font helpers ─────────────────────────────────────────────────────────────

def font(size: int = 13, weight: Literal["normal", "bold"] = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Helvetica", size=size, weight=weight)


def mono(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="Courier", size=size)