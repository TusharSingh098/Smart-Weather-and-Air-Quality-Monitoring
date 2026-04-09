import customtkinter as ctk
import tkinter as tk
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# OPTIONAL: import your backend
# from weather_api import WeatherToday, AirQuality

# --- THEME ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- APP WINDOW ---
app = ctk.CTk()
app.title("Smart Weather & Monitoring Project")
app.geometry("1200x700")

# GRID CONFIG
app.grid_rowconfigure(1, weight=1)
app.grid_columnconfigure(1, weight=1)

# ================= HEADER =================
header = ctk.CTkFrame(app, height=60)
header.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

header.grid_columnconfigure(1, weight=1)

# LOGO
logo_img = ctk.CTkImage(Image.open("National_Institute_of_Technology,_Kurukshetra_Logo.png"), size=(50, 50))
ctk.CTkLabel(header, image=logo_img, text="").grid(row=0, column=0, padx=10)

# TITLE
ctk.CTkLabel(header,
             text="🌍 Smart Weather & Monitoring Project",
             font=("Arial", 22, "bold")).grid(row=0, column=1, sticky="w")

# SEARCH BAR
city_entry = ctk.CTkEntry(header, placeholder_text="Enter City")
city_entry.grid(row=0, column=2, padx=10)

# ================= SIDEBAR =================
sidebar = ctk.CTkFrame(app, width=250)
sidebar.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

sidebar.grid_rowconfigure(10, weight=1)

# TEAM INFO
ctk.CTkLabel(sidebar, text="👥 Team Info",
             font=("Arial", 16, "bold")).grid(row=0, column=0, pady=10)

ctk.CTkLabel(sidebar, text="""
Tushar Singh– Data Engineer | ML Engineer
Abhishek Bhattacharjee – Data Engineer | ML Engineer
Balwant Shakya – UI|UX Engineer
Teena Gautam – UI|UX Engineer
""", justify="left").grid(row=1, column=0, padx=10)

# BUTTONS
def load_data():
    city = city_entry.get()
    print(f"Fetching data for {city}")
    show_weather_graph()
    show_aqi_graph()

ctk.CTkButton(sidebar, text="📊 Load Data",
              command=load_data).grid(row=2, column=0, pady=10)

# MODE SWITCH
def toggle_mode():
    mode = ctk.get_appearance_mode()
    ctk.set_appearance_mode("light" if mode == "dark" else "dark")

ctk.CTkButton(sidebar, text="🌗 Toggle Theme",
              command=toggle_mode).grid(row=3, column=0, pady=10)

# ================= MAIN AREA =================
main_frame = ctk.CTkFrame(app)
main_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

# TABS
tabview = ctk.CTkTabview(main_frame)
tabview.pack(fill="both", expand=True)

tab_weather = tabview.add("🌤️ Weather")
tab_history = tabview.add("📊 History")
tab_aqi = tabview.add("🌫️ AQI")

# ================= SAMPLE DATA =================
def get_sample_data():
    return pd.DataFrame({
        "time": pd.date_range(start="2024-01-01", periods=24, freq="h"),
        "temperature": [20 + i*0.5 for i in range(24)],
        "humidity": [60 + i for i in range(24)],
        "pm2_5": [30 + i for i in range(24)]
    })

# ================= GRAPH FUNCTIONS =================
def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def show_weather_graph():
    clear_frame(tab_weather)
    df = get_sample_data()

    fig, ax = plt.subplots()
    ax.plot(df["time"], df["temperature"])
    ax.set_title("Temperature Trend")

    canvas = FigureCanvasTkAgg(fig, master=tab_weather)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def show_history_graph():
    clear_frame(tab_history)
    df = get_sample_data()

    fig, ax = plt.subplots()
    ax.plot(df["time"], df["humidity"])
    ax.set_title("Humidity Trend")

    canvas = FigureCanvasTkAgg(fig, master=tab_history)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def show_aqi_graph():
    clear_frame(tab_aqi)
    df = get_sample_data()

    fig, ax = plt.subplots()
    ax.plot(df["time"], df["pm2_5"])
    ax.set_title("PM2.5 Levels")

    canvas = FigureCanvasTkAgg(fig, master=tab_aqi)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

# INITIAL LOAD
show_weather_graph()
show_history_graph()
show_aqi_graph()

# ================= FOOTER =================
footer = ctk.CTkFrame(app, height=40)
footer.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

ctk.CTkLabel(footer,
             text="Team Pychaos | NIT Kurukshetra",
             font=("Arial", 12)).pack()

# RUN APP
app.mainloop()
df = get_sample_data()
weather = WeatherToday()
weather.geolocator(city_entry.get())
df = weather.forecast_today()
