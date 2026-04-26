"""
ml_engine/geography.py
Centralized geospatial configuration for the PyChaoS Weather Monitor.

This file acts as the Single Source of Truth (SSOT) for the application's coverage area.
All automated data ingestion (mass_ingestion.py) and UI dynamic routing (page_weather.py)
pull from this target dictionary to ensure synchronization.

Author: Team PyChaoS
College: NIT Kurukshetra
"""

# ─── State-Level District Registries ─────────────────────────────────────────

HARYANA_DISTRICTS = [
    "Bhiwani", "Faridabad", "Jind", "Kaithal", 
    "Kurukshetra", "Rohtak"
]

WEST_BENGAL_DISTRICTS = [
    "Asansol", "Darjeeling", "Kolkata"
]

UTTAR_PRADESH_DISTRICTS = [
    "Agra", "Ayodhya", "Bareilly", "Basti", 
    "Gorakhpur", "Kanpur", "Lalitpur", "Lucknow", 
    "Noida", "Prayagraj", "Varanasi"
]

# ─── Global Target Mapping ───────────────────────────────────────────────────

TARGET_REGIONS = {
    "Haryana": HARYANA_DISTRICTS,
    "West_Bengal": WEST_BENGAL_DISTRICTS,
    "Uttar_Pradesh": UTTAR_PRADESH_DISTRICTS
}

# NOTE FOR FUTURE SCALABILITY:
# To expand the application's coverage, simply declare a new list of districts above
# and map it to the TARGET_REGIONS dictionary. The ML pipeline and UI will adapt automatically.