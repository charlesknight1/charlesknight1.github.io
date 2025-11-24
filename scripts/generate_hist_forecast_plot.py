import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import datetime as dt
import numpy as np
from matplotlib.ticker import FuncFormatter
from pathlib import Path

TILES_DIR = Path("assets/tracker")
TILES_DIR.mkdir(parents=True, exist_ok=True)

cab_history = pd.read_csv('database/cab_history.csv', parse_dates=['date'], index_col='date')
heatlow_history = pd.read_csv('database/heatlow_history.csv', parse_dates=['date'], index_col='date')
rainbelt_history = pd.read_csv('database/rainbelt_history.csv', parse_dates=['date'], index_col='date')

most_recent_date = rainbelt_history.index.max()

# Find the oldest date across all datasets
oldest_date = min(cab_history.index.min(), heatlow_history.index.min(), rainbelt_history.index.min())
days_of_history = (most_recent_date - oldest_date).days

# Define transformation function with linear compression
def date_to_compressed(date, most_recent, transition_days=20, compression_factor=0.3, forecast_days=10):
    """Linear scale for recent data, compressed linear scale for historic data, extended for forecast"""
    days_from_recent = (most_recent - date).days
    if days_from_recent < 0:
        # Forecast data: extend linearly into the future
        return -days_from_recent
    elif days_from_recent <= transition_days:
        # Recent data: 1 day = 1 unit
        return -days_from_recent
    else:
        # Historic data: 1 day = compression_factor units
        historic_days = days_from_recent - transition_days
        return -transition_days - (historic_days * compression_factor)

def compressed_to_date(x_val, most_recent, transition_days=20, compression_factor=0.3):
    """Inverse transformation for axis labels"""
    if x_val >= 0:
        # Future dates
        days_forward = x_val
        return most_recent + dt.timedelta(days=days_forward)
    elif x_val >= -transition_days:
        # Recent past
        days_back = -x_val
        return most_recent - dt.timedelta(days=days_back)
    else:
        # Compressed historic
        compressed_part = (-x_val - transition_days)
        days_back = transition_days + (compressed_part / compression_factor)
        return most_recent - dt.timedelta(days=days_back)

# Transform all dates
transition_days = 5
compression_factor = 0.3
forecast_days = 10  # Space for 10 days of projections

rainbelt_x = [date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days) for d in rainbelt_history.index]
heatlow_x = [date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days) for d in heatlow_history.index]
cab_x = [date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days) for d in cab_history.index]

fig, ax = plt.subplots(1, 1, figsize=(10, 5))
# Use oldest_date instead of hardcoded 50 days
ax.set_xlim(date_to_compressed(oldest_date, most_recent_date, transition_days, compression_factor), forecast_days)
ax.set_ylim(-35, 32)
ax.grid(which='both', linestyle='--', alpha=0.5)
ax.set_ylabel('Latitude (°)', fontsize=12)

# Add title
ax.set_title(f"Tropical Rainbelt History and Forecast (valid: {most_recent_date.strftime('%d-%m-%Y')})",
             fontsize=13, pad=10)

# Remove top and right spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Custom x-axis formatter with better tick placement
def format_date_axis(x, pos):
    date = compressed_to_date(x, most_recent_date, transition_days, compression_factor)
    return date.strftime('%d %b')

# Set up x-axis ticks more explicitly
tick_positions = []
tick_dates = []

# Add ticks every 7 days in the compressed historic region
for days_back in range(days_of_history, transition_days, -7):
    date = most_recent_date - dt.timedelta(days=days_back)
    x_pos = date_to_compressed(date, most_recent_date, transition_days, compression_factor)
    tick_positions.append(x_pos)
    tick_dates.append(date.strftime('%d %b'))

# Add ticks every 3-4 days in the recent region
for days_back in range(transition_days, -1, -4):
    date = most_recent_date - dt.timedelta(days=days_back)
    x_pos = date_to_compressed(date, most_recent_date, transition_days, compression_factor)
    tick_positions.append(x_pos)
    tick_dates.append(date.strftime('%d %b'))

# Add ticks in forecast region
for days_forward in range(3, forecast_days+1, 3):
    date = most_recent_date + dt.timedelta(days=days_forward)
    x_pos = date_to_compressed(date, most_recent_date, transition_days, compression_factor)
    tick_positions.append(x_pos)
    tick_dates.append(date.strftime('%d %b'))

ax.set_xticks(tick_positions)
ax.set_xticklabels(tick_dates, rotation=90)

# plot rainbelt history
ax.plot(rainbelt_x, rainbelt_history['mean_latitude'], label='Rainbelt Latitude', color='blue')
ax.fill_between(rainbelt_x, rainbelt_history['south_lim'], rainbelt_history['north_lim'], color='blue', alpha=0.15, hatch='///')

# plot heatlow history
cmap = plt.get_cmap('YlOrRd')
norm = plt.Normalize(vmin=297, vmax=301)
shift = 0.5
last_width = 1.0
for idx, (x_pos, row) in enumerate(zip(heatlow_x, heatlow_history.itertuples())):
    if idx < len(heatlow_x) - 1:
        width = heatlow_x[idx + 1] - x_pos
    else:
        width = last_width  # fixed width for last item
    x_pos -= shift  # shift everything left by 0.5
    ax.add_patch(plt.Rectangle((x_pos, row.northheatlow_lat - 1.5), width, 3,
                               color=cmap(norm(row.northheatlow_temp))))
    ax.add_patch(plt.Rectangle((x_pos, row.southheatlow_lat - 1.5), width, 3,
                               color=cmap(norm(row.southheatlow_temp))))

# Background patch
bg_x = date_to_compressed(cab_history.index.min()-dt.timedelta(days=90), most_recent_date, transition_days, compression_factor)
ax.add_patch(plt.Rectangle((bg_x, -50), abs(bg_x), 100, color='lightgrey', alpha=0.5, zorder=0))

# plot cab history
ax.scatter(cab_x, cab_history['cab_lat'], label='CAB Latitude', color='green', s=cab_history['cab_len'], alpha=0.7, edgecolors='k')
# plot kd history
cab_x = np.array(cab_x)   # <-- add this
mask = cab_history['kd_len'] > 30
ax.scatter(
    cab_x[mask],
    cab_history['kd_lat'][mask],
    label='KD Latitude',
    color='red',
    s=cab_history['kd_len'][mask],
    alpha=0.7,
    edgecolors='k')

# Add colorbar
from matplotlib.cm import ScalarMappable
sm = ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax, label='Heat Low Temp (K)', extend='both', shrink=0.8, pad=0.02)
cbar.set_label('Heat Low Strength', labelpad=-1)
cbar.set_ticks([297, 301])
cbar.set_ticklabels(['-', '+'], fontsize=12)

# Add vertical line to show transition point (historic/recent)
transition_x = date_to_compressed(most_recent_date - dt.timedelta(days=transition_days), most_recent_date, transition_days, compression_factor)
ax.axvline(x=transition_x, color='gray', linestyle=':', alpha=0.5, linewidth=1.5)

# Add vertical line to show present day
present_x = date_to_compressed(most_recent_date, most_recent_date, transition_days, compression_factor)
ax.axvline(x=present_x, color='red', linestyle='-', alpha=0.6, linewidth=2, label='Today', zorder=1)

####################
# plot forecast data
####################

today = dt.datetime.now().date()
days_lag = (today - most_recent_date.date()).days
forecast_start = most_recent_date + dt.timedelta(days=days_lag-1)

import datetime as dt
import numpy as np

# --- Forecast plotting: Rainbelt mean lat ---
rainbelt_future = pd.read_csv('database/rainbelt_lat.csv').T
for i, col in enumerate(rainbelt_future.columns):
    future_lats_series = pd.to_numeric(rainbelt_future[col], errors='coerce')
    n_periods = len(future_lats_series)
    future_dates = pd.date_range(start=forecast_start, periods=n_periods)
    # compute compressed x positions as plain floats
    future_x = np.array([date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days)
                         for d in future_dates], dtype=float)
    future_lats = future_lats_series.values.astype(float)
    if i == 0:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5, label='Rainbelt Forecast')
    else:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5, alpha=0.2)# label='Rainbelt Forecast')

# --- Forecast plotting: Rainbelt south ---
rainbelt_future = pd.read_csv('database/rainbelt_lat_south.csv').T
for i, col in enumerate(rainbelt_future.columns):
    future_lats_series = pd.to_numeric(rainbelt_future[col], errors='coerce')
    n_periods = len(future_lats_series)
    future_dates = pd.date_range(start=forecast_start, periods=n_periods)
    # compute compressed x positions as plain floats
    future_x = np.array([date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days)
                         for d in future_dates], dtype=float)
    future_lats = future_lats_series.values.astype(float)
    if i == 0:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5)
    else:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5, alpha=0.2)# label='Rainbelt Forecast')

# --- Forecast plotting: Rainbelt north ---
rainbelt_future = pd.read_csv('database/rainbelt_lat_north.csv').T
for i, col in enumerate(rainbelt_future.columns):
    future_lats_series = pd.to_numeric(rainbelt_future[col], errors='coerce')
    n_periods = len(future_lats_series)
    future_dates = pd.date_range(start=forecast_start, periods=n_periods)
    # compute compressed x positions as plain floats
    future_x = np.array([date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days)
                         for d in future_dates], dtype=float)
    future_lats = future_lats_series.values.astype(float)
    if i == 0:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5)
    else:
        ax.plot(future_x, future_lats, color='black', linestyle='-', lw=1.5, alpha=0.2)# label='Rainbelt Forecast')
        
# --- Forecast plotting: CAB ---
#cab_future = pd.read_csv('database/cab_gridcells.csv').T
#cab_future_numeric = cab_future.apply(pd.to_numeric, errors='coerce')
#cab_future_prob = (cab_future_numeric > 15).sum(axis=1)
#future_CAB_series = pd.to_numeric(cab_future_prob, errors='coerce')
#n_periods = len(future_CAB_series)
#future_dates = pd.date_range(start=forecast_start+dt.timedelta(days=0.5), periods=n_periods)
#future_x = np.array([date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days) for d in future_dates], dtype=float)
#cmap_cab = plt.get_cmap('Greens')
#norm_cab = plt.Normalize(vmin=0, vmax=20)
#for i in range(10):
#    ax.add_patch(plt.Rectangle((future_x[i], -32), 1, 3, color=cmap_cab(norm_cab(future_CAB_series[i])), alpha=1, edgecolor='black', zorder=0))

## --- Forecast plotting: KD ---
#cab_future = pd.read_csv('database/kd_gridcells.csv').T
#cab_future_numeric = cab_future.apply(pd.to_numeric, errors='coerce')
#cab_future_prob = (cab_future_numeric > 10).sum(axis=1)
#future_CAB_series = pd.to_numeric(cab_future_prob, errors='coerce')
#n_periods = len(future_CAB_series)
#future_dates = pd.date_range(start=forecast_start+dt.timedelta(days=0.5), periods=n_periods)
#future_x = np.array([date_to_compressed(d, most_recent_date, transition_days, compression_factor, forecast_days) for d in future_dates], dtype=float)
#cmap_kd = plt.get_cmap('Reds')
#norm_kd = plt.Normalize(vmin=0, vmax=20)
#for i in range(10):
    #ax.add_patch(plt.Rectangle((future_x[i], -35), 1, 3, color=cmap_kd(norm_kd(future_CAB_series[i])), alpha=1, edgecolor='black', zorder=0))
    
## add a colorbar for CAB forecast sizes
#sm_cab = ScalarMappable(cmap=cmap_cab, norm=norm_cab)
#sm_cab.set_array([])
#cbax = fig.add_axes([0.4, 0.19, 0.08, 0.02])  # [left, bottom, width, height]
#cbar_cab = plt.colorbar(sm_cab, cax=cbax, orientation='horizontal', extend='both')
#cbar_cab.set_label('p(CAB)', labelpad=-10)  # Adjust label padding (e.g., 10)
#cbar_cab.set_ticks([0, 20])
#cbar_cab.set_ticklabels(['0', '1'], fontsize=8)
#sm_kd = ScalarMappable(cmap=cmap_kd, norm=norm_kd)
#sm_kd.set_array([])
#cbax = fig.add_axes([0.5, 0.19, 0.08, 0.02])  # [left, bottom, width, height]
#cbar_kd = plt.colorbar(sm_kd, cax=cbax, orientation='horizontal', extend='both')
#cbar_kd.set_label('p(KD)', labelpad=-10)  # Adjust label padding (e.g., 10)
#cbar_kd.set_ticks([0, 20])
#cbar_kd.set_ticklabels(['0', '1'], fontsize=8)

# Add legend
ax.legend(loc='upper right', fontsize=9.5, frameon=False, bbox_to_anchor=(0.95, 1))

plt.tight_layout()
plt.savefig('assets/tracker/history_and_forecast.png', dpi=300)
