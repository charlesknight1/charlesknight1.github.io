#!/usr/bin/env python
import os
import sys
import json
import datetime as dt
from datetime import datetime
from pathlib import Path

import requests
import numpy as np
import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon, Point, mapping
from shapely.ops import unary_union
from skimage import measure
import rioxarray  # needed for .rio accessors
from shapely.vectorized import contains

from drylines import find_edge,find_ridge,dxdy,ddx,ddy

# ------------------------
# Config
# ------------------------
CYCLE = os.getenv("GDAS_CYCLE", "00")  # "00","06","12","18"
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
    "&var_SPFH=on&lev_2_m_above_ground=on"
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
# Open GRIB and select variable
# ------------------------
ds = xr.open_dataset(
    grib_path,
    engine="cfgrib")
da = ds["sh2"]

# adjust coords
da = da.assign_coords(longitude=((da.longitude + 180) % 360) - 180)
da = da.sortby(da.longitude)

# get africa_union from your shapefile as before
AFRICA_GEOJSON_URL = "https://gist.githubusercontent.com/1310aditya/35b939f63d9bf7fbafb0ab28eb878388/raw/africa.json"
local_path = Path("africa.geojson")

# download
if not local_path.exists():
    r = requests.get(AFRICA_GEOJSON_URL, timeout=30)
    r.raise_for_status()
    local_path.write_bytes(r.content)

# now read from disk
afr = gpd.read_file(local_path)
if afr.crs is None:
    afr = afr.set_crs(4326)
africa_union = afr.unary_union

# make the lon/lat grid
lat = da.latitude.values
lon = da.longitude.values
lon2, lat2 = np.meshgrid(lon, lat)

# build boolean mask: True inside Africa
mask_africa = contains(africa_union, lon2, lat2)

# Create masks for acceptable CAB and KD locations
mask_cab = mask_africa*(lon2<=30)*(lon2>=15)*(lat2<=0)*(lat2>=-18)
mask_tkd = mask_africa*(lon2<=30)*(lat2<=-12)
# mask_tkd = (lon2<=30)*(lat2<=-12)#*(1-landmask.mask)
q = da.values
# give q an arbitrary time dimension
q = q[np.newaxis,:,:]

#Find dryline CABs. See drylines.py for a description of the inputs
cab_q=find_edge(q,lon,lat,2,theta_min=-np.pi/4,theta_max=np.pi/6,mag_min=0.003,minlen=15,spatial_mask=mask_cab,relative="Grid Cell",output='sparse',plotfreq=0,times=None)
#Find dryline KDs. See drylines.py for a description of the inputs
kd_q=find_edge(q,lon,lat,2,theta_max=np.pi/2,theta_min=np.pi/6,mag_min=0.003,minlen=10,spatial_mask=mask_tkd,relative="Grid Cell",output='sparse',plotfreq=0,times=None)
#Find drylines elsewhere. See drylines.py for a description of the inputs
dryline_q=find_edge(q,lon,lat,2,theta_max=np.pi,theta_min=-np.pi,mag_min=0.003,minlen=30,spatial_mask=mask_africa,relative="Grid Cell",output='sparse',plotfreq=0,times=None)

# Create a DataArray from the cab_q array
cab_q_da = xr.DataArray(cab_q.astype(int), dims=("time", "latitude", "longitude"), coords={"time": [0], "latitude": lat, "longitude": lon})
kd_q_da = xr.DataArray(kd_q.astype(int), dims=("time", "latitude", "longitude"), coords={"time": [0], "latitude": lat, "longitude": lon})
dryline_q_da = xr.DataArray(dryline_q.astype(int), dims=("time", "latitude", "longitude"), coords={"time": [0], "latitude": lat, "longitude": lon})

def write_combined_geojson(named_das: dict, out_path, on_value=1, date_str=None):
    """
    named_das: dict like {"cab": cab_q_da, "kd": kd_q_da, "dryline": dryline_q_da}
    out_path: path to the single output .geojson
    on_value: cell value considered "on" (defaults to 1)
    date_str: optional 'YYYY-MM-DD'; if None, uses today's local date
    """
    if date_str is None:
        date_str = datetime.today().date().isoformat()

    features = []
    for source, q_da in named_das.items():
        arr = q_da.isel(time=0) if "time" in q_da.dims else q_da
        lat = arr.latitude.values
        lon = arr.longitude.values
        ii, jj = np.where(arr.values == on_value)

        for i, j in zip(ii, jj):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(lon[j]), float(lat[i])]},
                "properties": {"source": source, "date": date_str},
            })

    geojson = {"type": "FeatureCollection", "features": features}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(geojson, f)
    return len(features)

# --- Use it ---
all_das = {"cab": cab_q_da, "kd": kd_q_da, "dryline": dryline_q_da}
out_file = TILES_DIR / "drylines.geojson"
n = write_combined_geojson(all_das, out_file)
print(f"Wrote {out_file} with {n} points (date on each feature).")

# ------------------------
# Append cab data to data/cab_history.csv (idempotent per date)
# ------------------------
from pathlib import Path
import pandas as pd

# Use centroid latitude of the polygon as "mean latitude"
lat = cab_q_da.latitude.values
lon = cab_q_da.longitude.values
cab_points = np.where(cab_q_da[0] == 1)
cab_len = len(cab_points)
cab_lat = np.nanmean(lat[cab_points[0]])
kd_points =  np.where(kd_q_da[0] == 1)
kd_len = len(kd_points)
kd_lat = np.nanmean(lat[kd_points[0]])

history_path = Path("database") / "cab_history.csv"
history_path.parent.mkdir(parents=True, exist_ok=True)

row = {
    "date": today_str,                  # YYYYMMDD from earlier in your script
    "cab_len": round(cab_len, 4)
    "cab_lat": round(cab_lat, 4)
    "kd_len": round(kd_len, 4)
    "kd_lat": round(kd_lat, 4)
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
