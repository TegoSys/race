import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from adjustText import adjust_text
import os

# --- CONFIGURATION & SETTINGS ---
FILE_NAME = 'S1_#25606_converted.csv'
DOWNSAMPLE_RATE = 50  
SAVE_PLOT = True  
PLOT_FILENAME = 'road_atlanta_analysisManual.png'

# Official Road Atlanta Start/Finish Line (GPS)
SF_LAT, SF_LON = 34.14917, -83.81096 

# --- NEW: MANUAL COORDINATES ---
# Replace these placeholder values with your specific x, y coordinates
manual_turns = {
    'T1': (125,-50),
    'T2': (0, -270),
    'T3': (-50, -325),
    'T4': (-200, -500),
    'T5': (-450, -850),
    'T6': (-460, -1400),
    'T7': (-700, -1400),
    'T8': (-600, -1000),
    'T9': (-650, -500),
    'T10a': (-600, -75),
    'T10b': (-700, 25),
    'T11' : (-600,125),
    'T12': (-375, 210)
}

# --- 1. DATA LOADING & CLEANING ---
df = pd.read_csv(FILE_NAME, skiprows=14, low_memory=False)
df.columns = df.columns.str.strip()
df['GPS Latitude'] = pd.to_numeric(df['GPS Latitude'], errors='coerce')
df['GPS Longitude'] = pd.to_numeric(df['GPS Longitude'], errors='coerce')

df_clean = df[df['GPS Latitude'].between(34.1, 34.3)].dropna(subset=['GPS Latitude']).copy()
df_clean = df_clean.reset_index(drop=True)

# Origin for Projection (Keep for Start/Finish and Track Path)
lat0, lon0 = np.radians(df_clean['GPS Latitude'].iloc[0]), np.radians(df_clean['GPS Longitude'].iloc[0])
R = 6371000

# --- 2. DOWNSAMPLE & PROJECT ---
df_plot = df_clean[::DOWNSAMPLE_RATE].copy()
lat_rad, lon_rad = np.radians(df_plot['GPS Latitude']), np.radians(df_plot['GPS Longitude'])
df_plot['x'] = R * (lon_rad - lon0) * np.cos(lat0)
df_plot['y'] = R * (lat_rad - lat0)

# --- 3. PLOTTING ---
fig, ax = plt.subplots(figsize=(12, 12))

# Plot Track Path
ax.plot(df_plot['x'], df_plot['y'], color='royalblue', linewidth=1.5, alpha=0.5, label='Track Path')

# Start/Finish Marker
sf_x = R * (np.radians(SF_LON) - lon0) * np.cos(lat0)
sf_y = R * (np.radians(SF_LAT) - lat0)
sf_x = -200
sf_y = 200
ax.scatter(sf_x, sf_y, color='black', marker='X', s=150, label='Start/Finish', zorder=6)

# --- 4. PLACING MANUAL TURN LABELS ---
texts = []
for label, (tx, ty) in manual_turns.items():
    # We only add the text, no red dots (ax.scatter) as requested
    texts.append(ax.text(tx, ty, label, fontsize=10, fontweight='bold', color='darkred'))

# Clean up label overlaps
adjust_text(texts, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))

# Formatting
ax.set_aspect('equal')
ax.grid(True, linestyle='--', alpha=0.3)
plt.title("Road Atlanta Turn Placement", fontsize=14)
plt.xlabel("Meters (X)")
plt.ylabel("Meters (Y)")
plt.legend()

# --- 5. SAVE & SHOW ---
if SAVE_PLOT:
    plt.savefig(PLOT_FILENAME, dpi=300, bbox_inches='tight')
    print(f"Successfully saved plot to {os.getcwd()}\\{PLOT_FILENAME}")

plt.show()