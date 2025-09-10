#!/usr/bin/env python
import os
import sys
import json
import datetime as dt
from pathlib import Path

import requests
import numpy as np
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from skimage import measure
import matplotlib.pyplot as plt
import rioxarray  # needed for .rio accessors

from skimage.measure import label, regionprops
import rasterio
from rasterio import features
from affine import Affine
from shapely.geometry import shape


# ------------------------
# Config
# ------------------------
CYCLE = os.getenv("GDAS_CYCLE", "00")  # "00","06","12","18"
AFRICA_GEOJSON_URL = os.getenv(
    "AFRICA_GEOJSON_URL",
    "https://gist.githubusercontent.com/1310aditya/35b939f63d9bf7fbafb0ab28eb878388/raw/africa.json",
)
TILES_DIR = Path("tiles")
TILES_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------
# Build today's URL & download (no fallback)
# ------------------------
today_str = dt.datetime.utcnow().strftime("%Y%m%d")
url = (
    "https://nomads.ncep.noaa.gov/cgi-bin/filter_gdas_0p25.pl"
    f"?dir=%2Fgdas.{today_str}%2F{CYCLE}%2Fatmos"
    f"&file=gdas.t{CYCLE}z.pgrb2.0p25.f000"
    "&lev_850_mb=on"
)

grib_path = Path(f"gdas.t{CYCLE}z.pgrb2.0p25.f000")

print(f"Downloading: {url}")
r = requests.get(url, stream=True, timeout=120)
if r.status_code != 200:
    print(f"ERROR: fetch failed with HTTP {r.status_code}", file=sys.stderr)
    sys.exit(1)
with open(grib_path, "wb") as f:
    for chunk in r.iter_content(chunk_size=1 << 20):
        if chunk:
            f.write(chunk)
print(f"Saved {grib_path}")

# ------------------------
# Load Africa geometry
# ------------------------
afr = gpd.read_file(AFRICA_GEOJSON_URL)
if afr.crs is None:
    afr.set_crs(4326, inplace=True)
africa_union = unary_union(afr.geometry)

# ------------------------
# Open GRIB and select variable
# ------------------------
ds = xr.open_dataset(
    grib_path,
    engine="cfgrib",
    # backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa", "level": 850}},
)
var_name = "t" if "t" in ds.data_vars else list(ds.data_vars)#[0]
da = ds[var_name]
da

# Normalize longitude & set spatial dims/CRS
if float(da.longitude.max()) > 180:
    lon = (((da.longitude + 180) % 360) - 180).values
    da = da.assign_coords(longitude=("longitude", lon)).sortby("longitude")
da = da.rio.write_crs(4326).rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")

# smooth data
da_smooth = da.rolling(
    longitude=8,
    latitude=8,
    center=True,
    min_periods=1
).mean()

# ------------------------
# Clip to Africa
# ------------------------
da_clip = da_smooth.rio.clip([mapping(africa_union)], crs=afr.crs, drop=False)


# ------------------------
# Define thresholds 
# ------------------------

north_africa_threshold = da_clip.sel(latitude=slice(35, 0)).quantile(0.95).item()
print(f"North Africa 90th percentile: {north_africa_threshold:.4f}")
south_africa_threshold = da_clip.sel(latitude=slice(0, -35)).quantile(0.95).item()
print(f"South Africa 90th percentile: {south_africa_threshold:.4f}")

# ------------------------
# Sahara HL
# ------------------------
# threshold northern latitudes only
north_hl = (da_clip.where(da_clip.latitude >= 0) > north_africa_threshold)
# deal with extra dims if present
for dim in ["time", "step", "valid_time"]:
    if dim in north_hl.dims:
        north_hl = north_hl.isel({dim: 0})
        da2d = da_clip.isel({dim: 0})
        break
else:
    north_hl = north_hl
    da2d = da_clip
# get largest contiguous region
mask = north_hl.fillna(False).values.astype(bool)
labels = label(mask, connectivity=2)
props = regionprops(labels)
if not props:
    raise SystemExit("No regions found")
largest = max(props, key=lambda p: p.area)  # area in pixels (robust)
largest_mask = (labels == largest.label)
lon = da2d.longitude.values
lat = da2d.latitude.values
xres = float(lon[1] - lon[0])
yres = float(lat[1] - lat[0])  # note: likely negative (north->south)
transform = Affine.translation(lon[0] - xres/2, lat[0] - yres/2) * Affine.scale(xres, yres)
shapes = features.shapes(largest_mask.astype(np.uint8), mask=largest_mask, transform=transform)
geoms = [shape(geom) for geom, val in shapes if val == 1]
north_largest_polygon = unary_union(geoms)

north_mean_temp = da2d.where(largest_mask).mean().item()
print(f"Mean T inside north largest region: {north_mean_temp:.2f} K")


# # ------------------------
# # Southern Africa HL
# # ------------------------

# threshold northern latitudes only
south_hl = (da_clip.where(da_clip.latitude <= 0) > south_africa_threshold)
# deal with extra dims if present
for dim in ["time", "step", "valid_time"]:
    if dim in south_hl.dims:
        south_hl = south_hl.isel({dim: 0})
        da2d = da_clip.isel({dim: 0})
        break
else:
    south_hl = south_hl
    da2d = da_clip
# get largest contiguous region
mask = south_hl.fillna(False).values.astype(bool)
labels = label(mask, connectivity=2)
props = regionprops(labels)
if not props:
    raise SystemExit("No regions found")
largest = max(props, key=lambda p: p.area)  # area in pixels (robust)
largest_mask = (labels == largest.label)
lon = da2d.longitude.values
lat = da2d.latitude.values
xres = float(lon[1] - lon[0])
yres = float(lat[1] - lat[0])  # note: likely negative (north->south)
transform = Affine.translation(lon[0] - xres/2, lat[0] - yres/2) * Affine.scale(xres, yres)
shapes = features.shapes(largest_mask.astype(np.uint8), mask=largest_mask, transform=transform)
geoms = [shape(geom) for geom, val in shapes if val == 1]
south_largest_polygon = unary_union(geoms)


south_mean_temp = da2d.where(largest_mask).mean().item()
print(f"Mean T inside south largest region: {south_mean_temp:.2f} K")

# plot for sanity check
fig, ax = plt.subplots(figsize=(8, 8))
da2d.plot(ax=ax, cmap="Blues", vmin=0, vmax=0.1)
x, y = north_largest_polygon.exterior.xy
ax.plot(x, y, color="red", linewidth=2)
x, y = south_largest_polygon.exterior.xy
ax.plot(x, y, color="red", linewidth=2)
plt.show()

# # ------------------------
# # Write to GeoJSON
# # ------------------------
out_path = TILES_DIR / "north_heat_low.geojson"
feature = {
    "type": "Feature",
    "geometry": mapping(north_largest_polygon),
    "properties": {
        "source": "NCEP GDAS 0.25°",
        "level_hPa": 850,
        "var": var_name,
        "temp": round(north_mean_temp, 3),
        "run_date": today_str,
        "run_cycle": CYCLE,
    },}
import datetime as dt
feature["properties"]["generated_at"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
with open(out_path, "w") as f:
    json.dump({"type": "FeatureCollection", "features": [feature]}, f)
print(f"Wrote {out_path}")


out_path = TILES_DIR / "south_heat_low.geojson"
feature = {
    "type": "Feature",
    "geometry": mapping(south_largest_polygon),
    "properties": {
        "source": "NCEP GDAS 0.25°",
        "level_hPa": 850,
        "var": var_name,
        "temp": round(south_mean_temp, 3),
        "run_date": today_str,
        "run_cycle": CYCLE,
    },}
import datetime as dt
feature["properties"]["generated_at"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
with open(out_path, "w") as f:
    json.dump({"type": "FeatureCollection", "features": [feature]}, f)
print(f"Wrote {out_path}")

# ------------------------
# Append heat low data to data/heatlow_history.csv (idempotent per date)
# ------------------------
from pathlib import Path
import pandas as pd

# Use centroid latitude of the polygon as "mean latitude"
north_mean_lat = float(north_largest_polygon.centroid.y)
south_mean_lat = float(south_largest_polygon.centroid.y)

history_path = Path("database") / "heatlow_history.csv"
history_path.parent.mkdir(parents=True, exist_ok=True)

row = {
    "date": today_str,                  # YYYYMMDD from earlier in your script
    "northheatlow_lat": round(north_mean_lat, 4),
    "northheatlow_temp": round(north_mean_temp, 4),
    "southheatlow_lat": round(south_mean_lat, 4),
    "southheatlow_temp": round(south_mean_temp, 4),
}

if history_path.exists():
    df = pd.read_csv(history_path, dtype={"date": str})
    # drop any existing record for this date
    df = df[df["date"] != row["date"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
else:
    df = pd.DataFrame([row])

df = df.sort_values("date")
df.to_csv(history_path, index=False)

print(f"Updated {history_path} for {row['date']}")

print(df)
