"""
ui_engine/header.py
Top header bar: college logo · project title · search bar · action buttons.
"""
import os
import customtkinter as ctk
from PIL import Image, ImageDraw
from . import theme

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")
_LOGO_PATHS = [
    os.path.join(_ASSETS, "NIT_Logo.png"),
    os.path.join(_ASSETS, "NIT_Logo.png"),
]


def _make_placeholder_logo(size: int) -> ctk.CTkImage:
    """Generate a circular logo placeholder when no image file is found."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, size - 2, size - 2], fill="#1A4B8C", outline="#3B7DD8", width=3)
    try:
        from PIL import ImageFont
        fnt = ImageFont.truetype("arial.ttf", size // 5)
    except Exception:
        fnt = None
    draw.text(
        (size // 2, size // 2 - size // 10), "NIT",
        fill="white", anchor="mm", font=fnt,
    )
    draw.text(
        (size // 2, size // 2 + size // 7), "KUK",
        fill="#FFD700", anchor="mm", font=fnt,
    )
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def _load_logo(size: int = 68) -> ctk.CTkImage:
    for path in _LOGO_PATHS:
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA")
                return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            except Exception:
                pass
    return _make_placeholder_logo(size)


class HeaderBar(ctk.CTkFrame):
    HEIGHT = 80

    def __init__(self, parent, *, on_search, on_team, on_theme):
        c = theme.get()
        super().__init__(
            parent,
            fg_color=c["surface"],
            corner_radius=0,
            border_width=0,
            height=self.HEIGHT,
        )
        self.pack_propagate(False)
        self._on_search = on_search
        self._on_team   = on_team
        self._on_theme  = on_theme
        self._c = c
        self._build()
        theme.on_change(self._retheme)

    def _build(self):
        c = self._c

        # ── left: logo ────────────────────────────────────────────────────────
        logo_img = _load_logo(62)
        self._logo_lbl = ctk.CTkLabel(self, image=logo_img, text="")
        self._logo_lbl.pack(side="left", padx=(16, 10), pady=8)

        # ── center: title stack ───────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(side="left", fill="y", pady=6)

        self._title = ctk.CTkLabel(
            title_frame,
            text="Smart Weather & Air Quality Monitor",
            font=theme.font(17, "bold"),
            text_color=c["text"],
        )
        self._title.pack(anchor="w")

        self._sub = ctk.CTkLabel(
            title_frame,
            text="CSIC-104  ·  NIT Kurukshetra  ·  Team PyChaoS",
            font=theme.font(10),
            text_color=c["text_muted"],
        )
        self._sub.pack(anchor="w")

        # ── right: search + buttons ───────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=16, pady=12)

        self._search_var = ctk.StringVar()
        self._search = ctk.CTkEntry(
            right,
            placeholder_text="🔍  Search city…",
            textvariable=self._search_var,
            width=210, height=36,
            font=theme.font(12),
            fg_color=c["card"],
            border_color=c["border"],
            text_color=c["text"],
        )
        self._search.pack(side="left", padx=(0, 8))
        self._search.bind("<Return>", self._fire_search)

        self._search_btn = ctk.CTkButton(
            right, text="Search",
            width=72, height=36,
            font=theme.font(12),
            fg_color=c["accent"],
            hover_color=c["accent"],
            command=self._fire_search,
        )
        self._search_btn.pack(side="left", padx=(0, 8))

        self._theme_btn = ctk.CTkButton(
            right,
            text="🌙" if theme.is_dark() else "☀️",
            width=36, height=36,
            font=theme.font(15),
            fg_color=c["card"],
            text_color=c["text"],
            border_width=1,
            border_color=c["border"],
            hover_color=c["btn_hover"],
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side="left", padx=(0, 6))

        self._team_btn = ctk.CTkButton(
            right,
            text="👥 Team",
            width=80, height=36,
            font=theme.font(12),
            fg_color=c["card"],
            text_color=c["text"],
            border_width=1,
            border_color=c["border"],
            hover_color=c["btn_hover"],
            command=self._on_team,
        )
        self._team_btn.pack(side="left")

        # ── bottom separator line ─────────────────────────────────────────────
        sep = ctk.CTkFrame(self, fg_color=c["border"], height=1, corner_radius=0)
        sep.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

    def _fire_search(self, _event=None):
        city = self._search_var.get().strip()
        if city:
            self._on_search(city)

    def _toggle_theme(self):
        self._on_theme()
        self._theme_btn.configure(text="☀️" if not theme.is_dark() else "🌙")

    def _retheme(self):
        c = theme.get()
        self._c = c
        self.configure(fg_color=c["surface"])
        self._title.configure(text_color=c["text"])
        self._sub.configure(text_color=c["text_muted"])
        self._search.configure(fg_color=c["card"], border_color=c["border"],
                                text_color=c["text"])
        self._search_btn.configure(fg_color=c["accent"])
        self._theme_btn.configure(fg_color=c["card"], text_color=c["text"],
                                   border_color=c["border"],
                                   hover_color=c["btn_hover"],
                                   text="☀️" if not theme.is_dark() else "🌙")
        self._team_btn.configure(fg_color=c["card"], text_color=c["text"],
                                  border_color=c["border"], hover_color=c["btn_hover"])