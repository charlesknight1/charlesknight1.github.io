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
from shapely.geometry import Polygon, Point, mapping
from shapely.ops import unary_union
from skimage import measure
import rioxarray  # needed for .rio accessors


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

# Create masks for acceptable CAB and KD locations
lat = da.latitude.values
lon = da.longitude.values
lon2,lat2=np.meshgrid(lon,lat)
mask_cab = (lon2<=30)*(lon2>=15)*(lat2<=5)*(lat2>=-18)#*(1-landmask.mask)
# mask_tkd = (lon2<=30)*(lat2<=-12)#*(1-landmask.mask)
q = da.values*1000
# give q an arbitrary time dimension
q = q[np.newaxis,:,:]

#Find dryline CABs. See drylines.py for a description of the inputs
cab_q=find_edge(q,lon,lat,2,theta_min=-np.pi/4,theta_max=np.pi/6,mag_min=0.003,minlen=15,spatial_mask=mask_cab,relative="Grid Cell",output='sparse',plotfreq=0,times=None)
#Find dryline KDs. See drylines.py for a description of the inputs
# kd_q=find_edge(q,lon,lat,2,theta_max=np.pi/2,theta_min=np.pi/6,mag_min=0.003,minlen=10,spatial_mask=mask_tkd,relative="Grid Cell",output='sparse',plotfreq=0,times=None,makefig=q_fig)

# Create a DataArray from the cab_q array
cab_q_da = xr.DataArray(cab_q.astype(int), dims=("time", "latitude", "longitude"), coords={"time": [0], "latitude": lat, "longitude": lon})

# Extract the CAB points (latitude and longitude)
cab_points = np.where(cab_q_da[0] == 1)
cab_latitudes = lat[cab_points[0]]
cab_longitudes = lon[cab_points[1]]

# Create a list of Shapely Point geometries
cab_geometries = [Point(lon, lat) for lon, lat in zip(cab_longitudes, cab_latitudes)]

# Create a GeoJSON FeatureCollection
geojson_features = [
    {
        "type": "Feature",
        "geometry": mapping(point),
        "properties": {}  # Add any additional properties here if needed
    }
    for point in cab_geometries
]

out_path = TILES_DIR / "cab.geojson"
geojson_data = {
    "type": "FeatureCollection",
    "features": geojson_features
}
print(geojson_data)
# Save the GeoJSON to a file
with open(out_path, "w") as f:
    json.dump(geojson_data, f)

print(f"Wrote {out_path}")
