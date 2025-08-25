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
import rioxarray  # needed for .rio accessors

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
    backend_kwargs={"filter_by_keys": {"typeOfLevel": "isobaricInhPa", "level": 850}},
)
var_name = "q" if "q" in ds.data_vars else list(ds.data_vars)[0]
da = ds[var_name]


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
da_clip = da.rio.clip([mapping(africa_union)], crs=afr.crs, drop=False)

# ------------------------
# Threshold -> largest contour polygon
# ------------------------
belt = da_clip
for dim in ["time", "step", "valid_time"]:
    if dim in belt.dims:
        belt2d = belt.isel({dim: 0})
        da2d = da_clip.isel({dim: 0})
        break
else:
    belt2d = belt
    da2d = da_clip

arr = belt2d.values.astype(np.uint8)
contours = measure.find_contours(arr, level=0.01)

largest_polygon = None
max_area = 0.0
for contour in contours:
    rows = np.clip(contour[:, 0].astype(int), 0, arr.shape[0] - 1)  # y
    cols = np.clip(contour[:, 1].astype(int), 0, arr.shape[1] - 1)  # x
    lats = da2d.latitude.values[rows]
    lons = da2d.longitude.values[cols]
    poly = Polygon(zip(lons, lats))
    if poly.is_valid and poly.area > max_area:
        max_area = poly.area
        largest_polygon = poly

if largest_polygon is None:
    print("No valid polygon found; exiting.")
    sys.exit(0)

print(f"Largest polygon area (deg^2): {max_area:.4f}")

# ------------------------
# Overwrite a single GeoJSON
# ------------------------
out_path = TILES_DIR / "belt.geojson"
feature = {
    "type": "Feature",
    "geometry": mapping(largest_polygon),
    "properties": {
        "source": "NCEP GDAS 0.25°",
        "level_hPa": 850,
        "var": var_name,
        "threshold": 0.01,
        "run_date": today_str,
        "run_cycle": CYCLE,
    },
}
with open(out_path, "w") as f:
    json.dump({"type": "FeatureCollection", "features": [feature]}, f)
print(f"Wrote {out_path}")
