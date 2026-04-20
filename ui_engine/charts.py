"""
ui_engine/charts.py
Matplotlib + Seaborn chart builders.
Every public function returns a matplotlib Figure ready to embed via
FigureCanvasTkAgg.  Call embed(fig, frame) to place it in a CTkFrame.
"""
import matplotlib
matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import theme

# ─── Core helpers ─────────────────────────────────────────────────────────────

def _palette(dark: bool) -> dict:
    return theme.DARK if dark else theme.LIGHT


def _make_fig(nrows=1, ncols=1, figsize=(11, 3.8), dark=True):
    c = _palette(dark)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                             facecolor=c["chart_bg"],
                             tight_layout=dict(pad=1.5))
    ax_flat = np.array(axes).flatten() if hasattr(axes, "__len__") else [axes]
    for ax in ax_flat:
        ax.set_facecolor(c["chart_bg"])
        ax.tick_params(colors=c["text_muted"], labelsize=8.5)
        ax.xaxis.label.set_color(c["text_muted"])
        ax.yaxis.label.set_color(c["text_muted"])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(True, color=c["chart_grid"], linewidth=0.5,
                linestyle="--", alpha=0.9, zorder=0)
    return fig, axes, c


def _xfmt(ax, days: int):
    if days <= 1:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    elif days <= 7:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a %d"))
        ax.xaxis.set_major_locator(mdates.DayLocator())
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)


def embed(fig, parent) -> FigureCanvasTkAgg:
    """Embed a matplotlib Figure in a CTk/Tk parent frame."""
    for w in parent.winfo_children():
        w.destroy()
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=0, pady=0)
    plt.close(fig)
    return canvas


# ─── Weather charts ───────────────────────────────────────────────────────────

def temperature_chart(df: pd.DataFrame, days: int = 7, dark: bool = True):
    fig, ax, c = _make_fig(figsize=(11, 3.6), dark=dark)
    t   = df["time"]
    tmp = df["temperature_2m"]
    col = "#FF8C42"

    ax.plot(t, tmp, color=col, linewidth=2.2, zorder=3)
    ax.fill_between(t, tmp, tmp.min() - 1,
                    alpha=0.22, color=col, zorder=2)

    if "apparent_temperature" in df.columns:
        ax.plot(t, df["apparent_temperature"],
                color="#FFD166", linewidth=1.4,
                linestyle="--", alpha=0.75, label="Feels like")
        ax.legend(frameon=False, labelcolor=c["text_muted"],
                  fontsize=8, loc="upper right")

    # Annotate peak and trough
    i_hi = tmp.idxmax(); i_lo = tmp.idxmin()
    for idx, offset, color in [(i_hi, 9, col), (i_lo, -15, "#58A6FF")]:
        ax.annotate(f"{tmp[idx]:.1f}°C",
                    xy=(t[idx], tmp[idx]),
                    xytext=(0, offset), textcoords="offset points",
                    color=color, fontsize=8.5, ha="center",
                    fontweight="bold")

    ax.set_ylabel("°C", color=c["text_muted"])
    ax.set_title("Temperature", color=c["text"], fontsize=11,
                 fontweight="bold", pad=6)
    _xfmt(ax, days)
    return fig


def humidity_chart(df: pd.DataFrame, days: int = 7, dark: bool = True):
    fig, ax, c = _make_fig(figsize=(11, 3.0), dark=dark)
    t = df["time"]
    h = df["relative_humidity_2m"]
    col = "#58A6FF"

    ax.plot(t, h, color=col, linewidth=1.8, zorder=3)
    ax.fill_between(t, h, alpha=0.18, color=col, zorder=2)
    ax.axhspan(40, 60, alpha=0.08, color="#3FB950")
    ax.text(t.iloc[-1], 50, "ideal", color="#3FB950",
            fontsize=7, va="center", ha="right", alpha=0.7)
    ax.set_ylim(0, 105)
    ax.set_ylabel("%", color=c["text_muted"])
    ax.set_title("Relative Humidity", color=c["text"], fontsize=11,
                 fontweight="bold", pad=6)
    _xfmt(ax, days)
    return fig


def wind_chart(df: pd.DataFrame, days: int = 7, dark: bool = True):
    fig, ax, c = _make_fig(figsize=(11, 2.8), dark=dark)
    t = df["time"]
    w = df["wind_speed_10m"]
    bar_w = 0.025 if days <= 1 else (0.4 if days <= 7 else 0.8)

    ax.bar(t, w, color="#00C9A7", alpha=0.7,
           width=pd.Timedelta(hours=bar_w * 24), zorder=3)
    ax.plot(t, w, color="#00C9A7", linewidth=1, alpha=0.45, zorder=4)
    ax.set_ylabel("km/h", color=c["text_muted"])
    ax.set_title("Wind Speed", color=c["text"], fontsize=11,
                 fontweight="bold", pad=6)
    _xfmt(ax, days)
    return fig


def rain_chart(df: pd.DataFrame, days: int = 7, dark: bool = True):
    fig, ax, c = _make_fig(figsize=(11, 2.6), dark=dark)
    t = df["time"]
    r = df["rain"]
    bar_w = 0.025 if days <= 1 else (0.4 if days <= 7 else 0.8)

    ax.bar(t, r, color="#2F81F7", alpha=0.75,
           width=pd.Timedelta(hours=bar_w * 24), zorder=3)
    ax.set_ylabel("mm", color=c["text_muted"])
    ax.set_title("Rainfall", color=c["text"], fontsize=11,
                 fontweight="bold", pad=6)
    _xfmt(ax, days)
    return fig


def hourly_forecast_chart(df: pd.DataFrame, dark: bool = True):
    """Two-panel hourly chart: temperature (top) + humidity & rain (bottom)."""
    c = _palette(dark)
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 5.5),
        facecolor=c["chart_bg"],
        tight_layout=dict(pad=1.8, h_pad=2.0),
    )
    for ax in (ax1, ax2):
        ax.set_facecolor(c["chart_bg"])
        ax.tick_params(colors=c["text_muted"], labelsize=8.5)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(True, color=c["chart_grid"], linewidth=0.5,
                linestyle="--", alpha=0.9)

    t = df["time"]

    # Top: temperature
    ax1.plot(t, df["temperature_2m"], color="#FF8C42", linewidth=2.4, zorder=3)
    ax1.fill_between(t, df["temperature_2m"],
                     df["temperature_2m"].min() - 1,
                     alpha=0.22, color="#FF8C42")
    if "apparent_temperature" in df.columns:
        ax1.plot(t, df["apparent_temperature"],
                 color="#FFD166", linewidth=1.5, linestyle="--",
                 alpha=0.75, label="Feels like")
        ax1.legend(frameon=False, labelcolor=c["text_muted"],
                   fontsize=8, loc="upper right")
    ax1.set_ylabel("°C", color=c["text_muted"])
    ax1.set_title("Today's Forecast – Temperature", color=c["text"],
                  fontsize=10, fontweight="bold")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    plt.setp(ax1.get_xticklabels(), rotation=25, ha="right", fontsize=8)

    # Bottom: humidity + rain
    ax2.fill_between(t, df["relative_humidity_2m"],
                     alpha=0.35, color="#58A6FF", label="Humidity %")
    ax2.plot(t, df["relative_humidity_2m"], color="#58A6FF", linewidth=1.2)
    ax2.set_ylim(0, 110)
    ax2b = ax2.twinx()
    ax2b.set_facecolor(c["chart_bg"])
    ax2b.tick_params(colors=c["text_muted"], labelsize=8.5)
    for spine in ax2b.spines.values():
        spine.set_visible(False)
    if df["rain"].sum() > 0:
        ax2b.bar(t, df["rain"], color="#2F81F7", alpha=0.65,
                 width=pd.Timedelta(hours=0.6), zorder=3, label="Rain mm")
    ax2.set_ylabel("Humidity %", color=c["text_muted"])
    ax2b.set_ylabel("Rain mm", color=c["text_muted"])
    ax2.set_title("Humidity & Rainfall", color=c["text"],
                  fontsize=10, fontweight="bold")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=3))
    plt.setp(ax2.get_xticklabels(), rotation=25, ha="right", fontsize=8)

    return fig


# ─── AQI charts ───────────────────────────────────────────────────────────────

_BANDS = [
    (0,     12.0,  "#00E400"),
    (12.0,  35.4,  "#F0D000"),
    (35.4,  55.4,  "#FF7E00"),
    (55.4,  150.4, "#FF0000"),
    (150.4, 250.4, "#8F3F97"),
    (250.4, 500.0, "#7E0023"),
]


def _pm_color(val: float) -> str:
    for lo, hi, col in _BANDS:
        if val <= hi:
            return col
    return "#7E0023"


def aqi_gauge(pm25: float, dark: bool = True):
    """Half-circle gauge chart for AQI."""
    c = _palette(dark)
    bg = c["chart_bg"]

    fig = plt.figure(figsize=(5, 3.2), facecolor=bg)
    ax  = fig.add_axes((0.05, 0.05, 0.90, 0.90))
    ax.set_facecolor(bg)
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.3, 1.3)
    ax.axis("off")

    # ── draw band arcs (half-circle, left = 0, right = max_val) ──────────────
    max_v = 300.0
    for lo, hi, band_col in _BANDS:
        lo_c = min(lo, max_v); hi_c = min(hi, max_v)
        theta1 = 180 - (lo_c / max_v) * 180
        theta2 = 180 - (hi_c / max_v) * 180
        arc = mpatches.Wedge(
            (0, 0), 1.1, theta2, theta1,
            width=0.35, facecolor=band_col,
            alpha=0.88, edgecolor="none",
        )
        ax.add_patch(arc)

    # ── inner grey ring ───────────────────────────────────────────────────────
    inner = mpatches.Wedge(
        (0, 0), 0.75, 0, 180,
        width=0.02, facecolor=c["border"],
        alpha=0.5, edgecolor="none",
    )
    ax.add_patch(inner)

    # ── needle ────────────────────────────────────────────────────────────────
    val_clamped = min(pm25, max_v)
    angle_deg   = 180 - (val_clamped / max_v) * 180
    angle_rad   = np.radians(angle_deg)
    nx, ny      = 0.88 * np.cos(angle_rad), 0.88 * np.sin(angle_rad)
    ax.annotate("",
                xy=(nx, ny), xytext=(0, 0),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=c["text"],
                    lw=2.5,
                    mutation_scale=14,
                ))
    ax.plot(0, 0, "o", color=c["text"], markersize=9, zorder=10)

    # ── value + label ─────────────────────────────────────────────────────────
    col_val = _pm_color(pm25)
    from .data_bridge import aqi_level
    level, _ = aqi_level(pm25)
    ax.text(0,  0.28, f"{pm25:.1f}", ha="center", va="bottom",
            fontsize=22, fontweight="bold", color=col_val)
    ax.text(0,  0.12, level, ha="center", va="bottom",
            fontsize=9.5, color=c["text_muted"])
    ax.text(0, -0.02, "PM2.5  μg/m³", ha="center", va="bottom",
            fontsize=8, color=c["text_dim"])

    # ── band labels (tiny) ────────────────────────────────────────────────────
    band_labels = [("Good", 6), ("Mod.", 24), ("USG", 45),
                   ("Unhl.", 103), ("VU", 200)]
    for lbl, v in band_labels:
        a_rad = np.radians(180 - (v / max_v) * 180)
        lx = 1.22 * np.cos(a_rad); ly = 1.22 * np.sin(a_rad)
        ax.text(lx, ly, lbl, ha="center", va="center",
                fontsize=6.5, color=c["text_dim"])

    return fig


def aqi_trend_chart(df: pd.DataFrame, days: int = 7, dark: bool = True):
    fig, ax, c = _make_fig(figsize=(11, 3.6), dark=dark)
    t = df["time"]

    if "pm2_5" in df.columns:
        ax.plot(t, df["pm2_5"], color="#FF6B6B", linewidth=2.0,
                label="PM2.5 (μg/m³)", zorder=3)
        ax.fill_between(t, df["pm2_5"], alpha=0.14, color="#FF6B6B")

    if "pm10" in df.columns:
        ax.plot(t, df["pm10"], color="#FFA94D", linewidth=1.7,
                linestyle="--", label="PM10 (μg/m³)", alpha=0.85, zorder=3)

    # WHO / AQI threshold lines
    for val, col, lbl in [(12, "#00E400", "Good"), (35.4, "#F0D000", "Moderate"),
                           (55.4, "#FF7E00", "Unhlthy")]:
        ax.axhline(val, color=col, linewidth=0.8, linestyle=":", alpha=0.55)
        ax.text(t.iloc[0], val + 1.5, lbl, color=col,
                fontsize=7, alpha=0.7)

    ax.set_ylabel("μg/m³", color=c["text_muted"])
    ax.set_title("PM2.5 & PM10 Trend", color=c["text"],
                 fontsize=11, fontweight="bold", pad=6)
    ax.legend(frameon=False, labelcolor=c["text_muted"],
              fontsize=8.5, loc="upper right")
    _xfmt(ax, days)
    return fig


def pollutant_bars(df: pd.DataFrame, dark: bool = True):
    """Average-concentration bar chart for all pollutants."""
    wanted = ["pm2_5", "pm10", "ozone", "nitrogen_dioxide", "sulphur_dioxide"]
    cols   = [col for col in wanted if col in df.columns]
    if not cols:
        return None

    labels = {"pm2_5": "PM2.5", "pm10": "PM10", "ozone": "O₃",
              "nitrogen_dioxide": "NO₂", "sulphur_dioxide": "SO₂"}
    avgs   = [df[col].mean() for col in cols]
    names  = [labels.get(col, col) for col in cols]
    colors = ["#FF6B6B", "#FFA94D", "#74C0FC", "#A9E34B", "#DA77F2"]

    fig, ax, c = _make_fig(figsize=(6.5, 3.2), dark=dark)
    bars = ax.bar(names, avgs, color=colors[:len(cols)],
                  alpha=0.82, edgecolor="none", zorder=3)
    for bar, val in zip(bars, avgs):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(avgs) * 0.025,
                f"{val:.1f}", ha="center", va="bottom",
                color=c["text_muted"], fontsize=8)
    ax.set_title("Average Pollutant Levels", color=c["text"],
                 fontsize=11, fontweight="bold", pad=6)
    ax.set_ylabel("μg/m³", color=c["text_muted"])
    return fig


def rain_probability_gauge(rain_pct: float, dark: bool = True):
    """Simple circular gauge for rain probability %."""
    c = _palette(dark)
    fig, ax = plt.subplots(figsize=(3.5, 3.5), facecolor=c["chart_bg"],
                            subplot_kw={"aspect": "equal"})
    ax.set_facecolor(c["chart_bg"])
    ax.axis("off")

    # Background ring
    bg_circle = mpatches.Circle((0.5, 0.5), 0.42, color=c["border"],
                             fill=False, linewidth=14, zorder=1)
    ax.add_patch(bg_circle)

    # Progress arc
    pct = max(0, min(100, rain_pct))
    col = "#58A6FF" if pct < 50 else ("#2F81F7" if pct < 75 else "#0550AE")
    from matplotlib.patches import Arc as MplArc
    arc = MplArc((0.5, 0.5), 0.84, 0.84,
                  angle=90, theta1=0, theta2=pct * 3.6,
                  color=col, linewidth=14, zorder=2)
    ax.add_patch(arc)

    ax.text(0.5, 0.54, f"{pct:.0f}%", ha="center", va="center",
            fontsize=22, fontweight="bold", color=col,
            transform=ax.transAxes)
    ax.text(0.5, 0.34, "Rain chance", ha="center", va="center",
            fontsize=9, color=c["text_muted"], transform=ax.transAxes)

    return fig