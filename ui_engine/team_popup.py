"""
ui_engine/team_popup.py
Attribution & Modal Dialog Controller.

Constructs a strictly modal overlay window containing academic metadata, 
external GitHub routing, and the development team roster. Employs iterative 
UI generation and graceful asset loading.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

import os
import webbrowser
import customtkinter as ctk
from PIL import Image
from . import theme

# ─── Data Registries ──────────────────────────────────────────────────────────

_ASSETS = os.path.join(os.path.dirname(__file__), "assets")

# Centralized Roster: Enables rapid roster updates without modifying GUI layout code
TEAM_MEMBERS = [
    {"name": "Tushar Singh",           "role": "Backend & ML Engineer (Lead)", "icon": "👑"},
    {"name": "Abhishek Bhattacharjee", "role": "Machine Learning Engineer",    "icon": "🤖"},
    {"name": "Ujjwal Verma",           "role": "API Integration Engineer",     "icon": "🔗"},
    {"name": "Teena Gautam",           "role": "UI/UX & API Developer",        "icon": "✨"},
    {"name": "Balwant Shakya",         "role": "UI/UX Designer & Frontend",    "icon": "🎨"},
]

PROJECT_INFO = {
    "name":    "Smart Weather & Air Quality Monitor",
    "course":  "CSIC-104 – Programming with Python",
    "college": "NIT Kurukshetra",
    "team":    "Team PyChaoS",
    "year":    "2025–26",
}

# ─── Modal Class Definition ────────────────────────────────────────────────────

class TeamPopup(ctk.CTkToplevel):
    """
    Independent overlay window for project attribution.
    """
    def __init__(self, parent):
        super().__init__(parent)
        c = theme.get()
        
        # Window OS-Level configuration
        self.title("Team PyChaoS – About")
        self.geometry("460x650")
        self.resizable(False, False) # Locks window dimensions to preserve layout integrity
        self.configure(fg_color=c["surface"])
        
        # Enforce Modality: Hijacks all UI events until this window is destroyed
        self.grab_set()           
        self.focus_set()
        
        self._build(c)

    def _build(self, c):
        """Constructs the visual components of the popup."""
        
        # ── Header Band ───────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=c["accent"], corner_radius=0, height=120)
        top.pack(fill="x")
        top.pack_propagate(False)

        # Defensive Asset Loading: Prevents FileNotFoundError crashes
        logo_path = os.path.join(_ASSETS, "pychaoslogo.jpeg")
        if os.path.exists(logo_path):
            img = ctk.CTkImage(Image.open(logo_path), size=(60, 60))
            ctk.CTkLabel(top, image=img, text="").place(relx=0.15, rely=0.5, anchor="center")

        ctk.CTkLabel(
            top, text="Team PyChaoS",
            font=theme.font(22, "bold"), text_color="#FFFFFF",
        ).place(relx=0.6, rely=0.4, anchor="center")

        ctk.CTkLabel(
            top, text=PROJECT_INFO["course"],
            font=theme.font(11), text_color="#E0E0E0", 
        ).place(relx=0.6, rely=0.7, anchor="center")

        # ── Project Info Card ─────────────────────────────────────────────────
        info_frame = ctk.CTkFrame(self, fg_color=c["card"], corner_radius=10, 
                                  border_width=1, border_color=c["border"])
        info_frame.pack(fill="x", padx=18, pady=(14, 8))

        rows = [
            ("🏫 College",  PROJECT_INFO["college"]),
            ("📚 Course",   PROJECT_INFO["course"]),
            ("👥 Team",     PROJECT_INFO["team"]),
            ("📅 Year",     PROJECT_INFO["year"]),
        ]
        
        # Iterative row generation
        for label, value in rows:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(row, text=label, font=theme.font(11), text_color=c["text_muted"], width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, font=theme.font(11, "bold"), text_color=c["text"], anchor="w").pack(side="left", padx=(6, 0))

        # ── External Routing (GitHub Button) ──────────────────────────────────
        github_btn = ctk.CTkButton(
            self, text="🔗 View Project on GitHub", font=theme.font(12, "bold"),
            fg_color="#2EA043", hover_color="#238636", text_color="white",
            # Triggers native OS browser
            command=lambda: webbrowser.open("https://github.com/TusharSingh098/Smart-Weather-and-Air-Quality-Monitoring.git")
        )
        github_btn.pack(fill="x", padx=18, pady=(0, 10))

        # ── Team Roster Section ───────────────────────────────────────────────
        ctk.CTkLabel(self, text="Development Team", font=theme.font(12, "bold"), text_color=c["text_muted"]).pack(anchor="w", padx=18, pady=(4, 6))

        members_frame = ctk.CTkScrollableFrame(self, fg_color=c["bg"], corner_radius=10, scrollbar_button_color=c["border"])
        members_frame.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        # Iterative Component Factory
        for member in TEAM_MEMBERS:
            card = ctk.CTkFrame(members_frame, fg_color=c["card"], corner_radius=10, border_width=1, border_color=c["border"])
            card.pack(fill="x", pady=4, padx=4)

            ctk.CTkLabel(card, text=member["icon"], font=theme.font(22), width=44).pack(side="left", padx=(12, 4), pady=10)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(side="left", fill="x", expand=True, pady=6)
            ctk.CTkLabel(inner, text=member["name"], font=theme.font(13, "bold"), text_color=c["text"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(inner, text=member["role"], font=theme.font(11), text_color=c["accent"], anchor="w").pack(anchor="w")

        # ── Close Action ──────────────────────────────────────────────────────
        ctk.CTkButton(
            self, text="Close", font=theme.font(12), fg_color=c["card"],
            text_color=c["text"], border_width=1, border_color=c["border"], 
            hover_color=c["btn_hover"], command=self.destroy, # Destroys the Toplevel window memory block
        ).pack(pady=(0, 14))