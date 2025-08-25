#!/usr/bin/env python
import os
import json
import io
import sys
import datetime as dt
from pathlib import Path

import requests
import numpy as np
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from skimage import measure
import rioxarray  # needed for .rio accessors

# ------------------------
# Config
# ------------------------
CYCLE = os.getenv("GDAS_CYCLE", "00")  # "00", "06", "12", "18"
AFRICA_GEOJSON_URL = os.getenv(
    "AFRICA_GEOJSON_URL",
    "https://gist.githubusercontent.com/1310aditya/35b939f63d9bf7fbafb0ab28eb878388/raw/africa.json",
)
TILES_DIR = Path("tiles")
TILES_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------
# Helper: find an available GDAS file for today 00Z, else fallback 1 day
# ------------------------
def gdas_url_for(date_yyyymmdd: str, cycle: str) -> str:
    # Specific humidity ('q') at 850 hPa often lives in pgrb2 files, but your original URL used DPT.
    # We'll pull the standard 0.25° file and open via cfgrib then select 'q' at 850 hPa.
    return (
        "https://nomads.ncep.noaa.gov/cgi-bin/filter_gdas_0p25.pl"
        f"?dir=%2Fgdas.{date_yyyymmdd}%2F{cycle}%2Fatmos"
        "&file=gdas.t{cycle}z.pgrb2.0p25.f000"
        "&lev_850_mb=on"
        # We don't filter var here so the file includes needed fields; cfgrib will select 'q'
        "".format(cycle=cycle)
    )

def try_fetch(url: str, out_path: Path) -> bool:
    r = requests.get(url, stream=True, timeout=90)
    if r.status_code != 200:
        return False
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            if chunk:
                f.write(chunk)
    return True

# ------------------------
# Step 1: Download GRIB for target run
# ------------------------
today = dt.datetime.utcnow().date()
candidates = [
    (today, CYCLE),
    (today - dt.timedelta(days=1), CYCLE),
]

grib_path = Path("gdas.t{z}z.pgrb2.0p25.f000".format(z=CYCLE))
ok = False
for d, z in candidates:
    yyyymmdd = d.strftime("%Y%m%d")
    url = gdas_url_for(yyyymmdd, z)
    print(f"Trying: {url}")
    if try_fetch(url, grib_path):
        run_date = d
        run_cycle = z
        ok = True
        break

if not ok:
    print("ERROR: Could not fetch GDAS file for today or yesterday.", file=sys.stderr)
    sys.exit(1)

print(f"Downloaded GRIB: {grib_path} for {run_date} {run_cycle}Z")

# ------------------------
# Step 2: Load Africa mask geometry
# ------------------------
afr = gpd.read_file(AFRICA_GEOJSON_URL)
if afr.crs is None:
    afr.set_crs(4326, inplace=True)  # assume WGS84 lon/lat
africa_union = unary_union(afr.geometry)

# ------------------------
# Step 3: Open with cfgrib, select specific humidity q at 850 hPa
# ------------------------
ds = xr.open_dataset(
    grib_path,
    engine="cfgrib",
    backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa", "level": 850}},
)

# The specific humidity variable is often named 'q'. Fallback to first data var if needed.
var_name = "q" if "q" in ds.data_vars else list(ds.data_vars)[0]
da = ds[var_name]

# Ensure we have lon in [-180, 180] and rioxarray spatial dims set
# cfgrib gives longitude 0..360 usually; shift to -180..180 to match typical GeoJSON
if da.longitude.max() > 180:
    lon = (((da.longitude + 180) % 360) - 180).values
    da = da.assign_coords(longitude=("longitude", lon)).sortby("longitude")

# write CRS and spatial dims for rioxarray operations
da = da.rio.write_crs(4326)
da = da.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")

# ------------------------
# Step 4: Clip to Africa
# ------------------------
da_clip = da.rio.clip([mapping(africa_union)], crs=afr.crs, drop=False)

# ------------------------
# Step 5: Build boolean belt and extract largest contour polygon
# ------------------------
belt = da_clip > 0.01  # your threshold
# Use the first (or only) time/step dimension if present
for dim in ["time", "step", "valid_time"]:
    if dim in belt.dims:
        belt2d = belt.isel({dim: 0})
        da2d = da_clip.isel({dim: 0})
        break
else:
    belt2d = belt
    da2d = da_clip

# skimage expects rows (y) then cols (x). Our array is [lat, lon] ordering.
arr = belt2d.values.astype(np.uint8)

contours = measure.find_contours(arr, level=0.5)

largest_polygon = None
max_area = 0.0

for contour in contours:
    # contour coords are (row=y, col=x) in index space
    # Convert to lon/lat by mapping through coordinate arrays
    rows = contour[:, 0].astype(int)
    cols = contour[:, 1].astype(int)
    # guard indices
    rows = np.clip(rows, 0, arr.shape[0] - 1)
    cols = np.clip(cols, 0, arr.shape[1] - 1)

    lats = da2d.latitude.values[rows]
    lons = da2d.longitude.values[cols]

    poly = Polygon(zip(lons, lats))
    if not poly.is_valid or poly.area == 0:
        continue
    area = poly.area
    if area > max_area:
        max_area = area
        largest_polygon = poly

if largest_polygon is None:
    print("No valid polygon found; exiting without changes.")
    sys.exit(0)

print(f"Largest polygon area (deg^2): {max_area:.4f}")

# ------------------------
# Step 6: Save to tiles/ with a date-stamped name and a stable latest pointer
# ------------------------
stamp = f"{run_date.strftime('%Y%m%d')}{run_cycle}"
out_dated = TILES_DIR / f"belt_{stamp}.geojson"
out_latest = TILES_DIR / "belt_latest.geojson"

feature = {
    "type": "Feature",
    "geometry": mapping(largest_polygon),
    "properties": {
        "source": "NCEP GDAS 0.25°",
        "level_hPa": 850,
        "var": var_name,
        "threshold": 0.01,
        "run_date": run_date.strftime("%Y-%m-%d"),
        "run_cycle": run_cycle,
    },
}

fc = {"type": "FeatureCollection", "features": [feature]}

with open(out_dated, "w") as f:
    json.dump(fc, f)

with open(out_latest, "w") as f:
    json.dump(fc, f)

print(f"Wrote: {out_dated} and {out_latest}")
