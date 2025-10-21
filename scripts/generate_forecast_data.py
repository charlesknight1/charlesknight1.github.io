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
import pandas as pd 
from shapely.vectorized import contains

from drylines import find_edge,find_ridge,dxdy,ddx,ddy

# ------------------------
# Config
# ------------------------
CYCLE = os.getenv("GDAS_CYCLE", "00")  # "00","06","12","18"
AFRICA_GEOJSON_URL = os.getenv(
    "AFRICA_GEOJSON_URL",
    "https://gist.githubusercontent.com/1310aditya/35b939f63d9bf7fbafb0ab28eb878388/raw/africa.json",
)
# TILES_DIR = Path("tiles")
# TILES_DIR.mkdir(parents=True, exist_ok=True)

def specific_humidity_simple(ds):
    """
    Compute specific humidity (kg/kg) from relative humidity (%) and temperature (K).
    Requires ds['r'] = RH (%) and ds['t'] = temperature (K)
    and coordinate ds['isobaricInhPa'] = pressure (hPa)
    """
    T = ds['t']
    RH = ds['r'] / 100.0  # convert % to fraction
    p = ds['isobaricInhPa']

    # Saturation vapor pressure (Bolton, 1980) [hPa]
    e_s = 6.112 * np.exp(17.67 * (T - 273.15) / (T - 29.65))

    # Actual vapor pressure [hPa]
    e = RH * e_s

    # Specific humidity [kg/kg]
    epsilon = 0.622
    q = (epsilon * e) / (p - (1 - epsilon) * e)

    # Store attributes
    q.name = 'specific_humidity'
    q.attrs['units'] = 'kg kg-1'
    q.attrs['long_name'] = 'specific humidity'

    return q


table_rain = []
table_cab = []

for ensemble_n in ['geavg', 'gec00', 'gep01', 'gep02', 'gep03', 'gep04', 'gep05', 'gep06', 'gep07', 'gep08', 'gep09', 'gep10', 'gep11', 'gep12', 'gep13', 'gep14', 'gep15']:
    row_rain = {'ensemble': ensemble_n}
    row_cab = {'ensemble': ensemble_n}
    for lead in [0, 24, 48, 72, 96, 120, 144, 168, 192, 216, 240]:
        print(f"Downloading ensemble {ensemble_n} lead {lead}")
        url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gefs_atmos_0p50a.pl?dir=%2Fgefs.20251021%2F00%2Fatmos%2Fpgrb2ap5&file={ensemble_n}.t00z.pgrb2a.0p50.f{lead:03d}&var_RH=on&var_TMP=on&lev_850_mb=on&subregion=&toplat=90&leftlon=-180&rightlon=180&bottomlat=-90"
        
        grib_path = Path(f"gdas.t{CYCLE}z.{ensemble_n}.f{lead:03d}")

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

        da = specific_humidity_simple(ds)
        da = da.rio.write_crs(4326).rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")

        # ------------------------
        # Detect CAB
        # ------------------------

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
        cab_q=find_edge(q,lon,lat,0,theta_min=-np.pi/4,theta_max=np.pi/6,mag_min=0.003,minlen=7,spatial_mask=mask_cab,relative="Grid Cell",output='sparse',plotfreq=0,times=None)
        #Find dryline KDs. See drylines.py for a description of the inputs
        kd_q=find_edge(q,lon,lat,0,theta_max=np.pi/2,theta_min=np.pi/6,mag_min=0.003,minlen=5,spatial_mask=mask_tkd,relative="Grid Cell",output='sparse',plotfreq=0,times=None)


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
        # Threshold -> largest contour polygon
        # ------------------------
        belt = da_clip > 0.01
        for dim in ["time", "step", "valid_time"]:
            if dim in belt.dims:
                belt2d = belt.isel({dim: 0})
                da2d = da_clip.isel({dim: 0})
                break
        else:
            belt2d = belt
            da2d = da_clip

        arr = belt2d.values.astype(np.uint8)
        contours = measure.find_contours(arr, level=0.5)

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

        # fail if no polygon found
        if largest_polygon is None:
            print("No valid polygon found; exiting without changes.")
            sys.exit(0)
        # after (FAIL the job)
        if largest_polygon is None:
            raise SystemExit("No valid polygon found — aborting job.")

        print(f"Mean lat: {largest_polygon.centroid.y}")
        row_rain[f"lead_{lead:03d}_mean_lat"] = largest_polygon.centroid.y
        print(f"CAB gridcells: {np.nansum(cab_q)}")
        row_cab[f"lead_{lead:03d}_cab_gridcells"] = np.nansum(cab_q)

        # delete downloaded file
        try:
            ds.close()
            os.remove(grib_path)
            os.remove(grib_path.with_suffix('.idx'))
        except:
            continue
    
    table_rain.append(row_rain)
    table_cab.append(row_cab)

table_rain = pd.DataFrame(table_rain)
table_cab = pd.DataFrame(table_cab)

table_rain.to_csv("rainbelt_lat.csv", index=False)
table_cab.to_csv("cab_gridcells.csv", index=False)
