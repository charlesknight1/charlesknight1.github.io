###############################
# DOWNLOAD SEVIRI IR 10.8 IMAGRY
###############################

# - This code uses the EUMDAC api to download SEVIRI imagry in native (.nat) format
# - Satpy code then produces a netcdf of IR 10.8
# - These are saved individually in the /netcdf output dir
# - All temp files are then deleted.
# - One timestep IR10.8 at 0.125 x 0.125 resolution is 500 kB. A months data is c. 1.5 GB

# Guide to using and configuring EUMDAC https://eumetsatspace.atlassian.net/wiki/spaces/EUMDAC/pages/1759805454/Command+Line+User+Guide

# Import packages
import pandas as pd
import numpy as np
from glob import glob
import subprocess
import matplotlib.pyplot as plt
import glob
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import satpy
import pyresample.geometry
import matplotlib.colors as mcolors
import os
import xarray as xr
from datetime import datetime

# get current date and time
from datetime import datetime

# Get current time
now = datetime.now()

# Format as 'YYYY-MM-DDTHH:MM'
download_start = now.strftime('%Y-%m-%dT00:00')
download_end = now.strftime('%Y-%m-%dT01:00')

print(f'Processing: {download_start} to {download_end}')

# download 1h data with EUMDAC
print(f'Downloading data with EUMDAC ...')
cmd = f'eumdac download -c EO:EUM:DAT:MSG:HRSEVIRI -s {download_start} -e {download_end} -o tempdata/'
process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
output = process.communicate()[0]

# loop through downloads (.zip)
zipfiles = sorted(glob.glob('/soge-home/users/kebl6418/charlesknight1.github.io/livedata/tempdata/*.zip'))
for i2, zipfile in enumerate(zipfiles):
    # unzip files
    print(f'Unzipping ... [{i2}]')
    cmd = f'unzip {zipfile} -d tempdata/'
    process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    # remove EOPMetadata.xml file
    cmd = f'rm tempdata/EOPMetadata.xml'
    process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    # remove manifest.xml file
    cmd = f'rm tempdata/manifest.xml'
    process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    # remove .zip file
    cmd = f'rm {zipfile}'
    process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
    output = process.communicate()[0]

# Read SEVIRI data.
filenames = glob.glob('/soge-home/users/kebl6418/charlesknight1.github.io/livedata/tempdata/*.nat')
for i3, file in enumerate(filenames):
    print(f'Processing scenes with Satpy ... [{i3}]')
    ## extract datetime information from file name
    print(file)
    start_index = file.find('-NA-')
    end_index = file.find('.', start_index)
    datetime_str = file[start_index+4:end_index]
    print(datetime_str)
    sensing_time = pd.to_datetime(datetime_str[-14:], format='%Y%m%d%H%M%S')
    print(datetime_str)

    # Open satpy scene object
    scene = satpy.Scene(filenames=[file], reader='seviri_l1b_native')

    # print available datasets
    print(scene.available_dataset_names())

    # Load the water vapor channels
    scene.load(['WV_062', 'WV_073'], upper_right_corner='NE')

    # Resample to regular lat/lon grid over southern Africa
    area = pyresample.geometry.create_area_def(
        area_id='mygrid', # ID of projection
        projection={'proj': 'latlong', 'lon_0': 0}, # Dictionary or string with Proj.4 parameters
        width=360,  # x dimension in number of pixels, aka number of grid columns
        height=360, # Number of points in grid
        area_extent=(-10, -50, 50, 0) # Area extent in lons lats as a tuple (lower_left_lon, lower_left_lat, upper_right_lon, upper_right_lat)
    )
    resampled = scene.resample(area) # Do the resampling

    for wavelength in ['WV_062', 'WV_073']:

        # Rename projection coordinates from y/x to lat/lon,
        resampled[wavelength] = resampled[wavelength].rename(
            {'y': 'lat', 'x': 'lon'})
        resampled[wavelength]['lon'].attrs = {'units': 'degrees_east',
                                            'standard_name': 'longitude'}
        resampled[wavelength]['lat'].attrs = {'units': 'degrees_north',
                                            'standard_name': 'latitude'}
        # add time dimension
        resampled[wavelength] = resampled[wavelength].assign_coords(time=sensing_time)

    # Save to netCDF.
    resampled.save_datasets(
        datasets=['WV_062', 'WV_073'],
        writer='cf',
        filename=f'tempdata/temp_nc_{i3}_{datetime_str}.nc',
        flatten_attrs=True,
        exclude_attrs=['raw_metadata'],
        include_lonlats=False)  # note this one here!

# merge all netcdf files
print(f'Merging netcdf files ...')
data = xr.open_mfdataset('tempdata/temp_nc_*.nc', combine='by_coords')
# # data = data.mean(dim='time')
# date_obj = datetime.strptime(download_start, '%Y-%m-%dT%H:%M')
# data = data.expand_dims(time=[date_obj])
data.to_netcdf('downloaded_data.nc')

# remove all tempdata associated with hour timestep
print(f'Cleaning up ...')
cmd = f'rm tempdata/*'
process = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE)
output = process.communicate()[0]
print(f'Done! {download_start}')

# plot

ir_data = xr.open_dataset('downloaded_data.nc').WV_062
time = ir_data.time.values[0]
timestr = pd.to_datetime(time).strftime('%Y-%m-%d 00:00')
ir_data = ir_data.mean('time')

fig, ax = plt.subplots(figsize=(6, 5), subplot_kw={'projection': ccrs.PlateCarree()}, dpi=200)
ax.set_title(f'{timestr}', fontsize=12)
plot = ax.pcolormesh(ir_data.lon, ir_data.lat, ir_data, transform=ccrs.PlateCarree(), cmap='terrain', vmin=230, vmax=250)
ax.set_extent([0, 45, 0, -35], crs=ccrs.PlateCarree())
ax.coastlines()
ax.add_feature(cfeature.BORDERS, linestyle='-', linewidth=0.5)

ax.set_ylabel('Latitude', fontsize=10)
ax.set_xlabel('Longitude', fontsize=10)

ax.set_xticks(np.arange(5, 45, 5))
ax.set_yticks(np.arange(-30, 0, 5))

ax.tick_params(axis='both', which='major', labelsize=9)
ax.grid(lw=0.5, ls=':', c='grey')

cbar = plt.colorbar(plot, orientation='horizontal',shrink=0.6, pad=0.15, extend='both')
cbar.set_label('WV6.2 Brightness Temperature (K)', rotation=0, fontsize=10)
cbar.ax.xaxis.set_tick_params(labelsize=9)
cbar.set_ticks(np.arange(230, 251, 5))

plt.tight_layout()
datestr = pd.to_datetime(time).strftime('%Y-%m-%d')
# plt.savefig(f'WV6.2_{datestr}.png')
plt.savefig(f'plot1.png')

