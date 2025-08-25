---
layout: post
title: Congo Air Boundary Tracker
permalink: /cabtracker
categories: projects
---
Live Congo Air Boundary tracker.

Data is up to date as of <span id="pageTopDate">Loading…</span>.

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin></script>
<script src="https://unpkg.com/pmtiles@3.0.5/dist/pmtiles.js"></script>

<style>
.map-controls {
  margin: 1em 0;
  display: flex;
  gap: 1em;
  flex-wrap: wrap;
  align-items: center;
}
.legend {
  background: white;
  padding: 10px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  margin-top: 1em;
}
.legend-gradient {
  width: 200px;
  height: 20px;
  background: linear-gradient(to right, white 0%, black 100%);
  border: 1px solid #ccc;
  margin: 5px 0;
}
.legend-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  width: 200px;
}
.info-box {
  position: absolute;
  top: 10px;
  right: 10px;
  background: white;
  padding: 10px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
  z-index: 1000;
  max-width: 220px;
  font-size: 12px;
}
</style>

<div class="map-controls">
  <label>
    Opacity: 
    <input type="range" id="opacitySlider" min="0" max="100" value="90" />
    <span id="opacityValue">90%</span>
  </label>
  <button id="toggleLayer">Hide Temperature Layer</button>
  <button id="resetView">Reset View</button>
</div>

<div id="map" style="height: 500px; width: 100%; position: relative;">
  <div class="info-box" id="infoBox">
    <strong>Land Surface Temperature</strong><br>
    Data: MLST-AS (MSG satellite)<br>
    <span id="dateInfo">Date: Loading…</span>
  </div>
</div>

<div class="legend">
  <strong>Land Surface Temperature (°C)</strong>
  <div class="legend-gradient"></div>
  <div class="legend-labels">
    <span>0°C</span>
    <span>25°C</span>
    <span>50°C</span>
  </div>
</div>

<script>
document.addEventListener("DOMContentLoaded", async function () {
  const map = L.map('map').setView([0, 20], 3);

  // Base layer
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  let temperatureLayer = null;
  const pmtilesUrl = '{{ "/tiles/raster.pmtiles" | relative_url }}';

  async function setPmtilesLastModified() {
    try {
      const headResp = await fetch(pmtilesUrl, { method: 'HEAD' });
      const lastMod = headResp.headers.get('Last-Modified');
      const infoEl = document.getElementById('dateInfo');
      const pageTopEl = document.getElementById('pageTopDate');
      if (lastMod) {
        const d = new Date(lastMod);
        const nice = d.toLocaleString('en-GB', {
          timeZone: 'UTC',
          year: 'numeric',
          month: 'short',
          day: '2-digit',
        });
        const txt = `Date (from .pmtiles): ${nice}`;
        infoEl.textContent = txt;
        pageTopEl.textContent = `${nice}`;
      } else {
        infoEl.textContent = 'Date: Unavailable';
        pageTopEl.textContent = 'Unavailable';
      }
    } catch (e) {
      console.error('HEAD request failed:', e);
      document.getElementById('dateInfo').textContent = 'Date: Error fetching';
      document.getElementById('pageTopDate').textContent = 'Error fetching';
    }
  }
  setPmtilesLastModified();

  try {
    const p = new pmtiles.PMTiles(pmtilesUrl);
    p.getHeader().then(h => console.log('PMTiles header:', h)).catch(console.error);

    temperatureLayer = pmtiles.leafletRasterLayer(p, {
      opacity: 0.9,
      attribution: 'Temperature data: LSA SAF'
    })
      .on('tileerror', (e) => console.error('Tile load error:', e))
      .addTo(map);
  } catch (err) {
    console.error('PMTiles init error:', err);
    document.getElementById('dateInfo').textContent = 'Date: Error loading data';
    document.getElementById('pageTopDate').textContent = 'Error loading data';
  }

  // Rainbelt overlay
    // --- Blue semitransparent overlay from tiles/overlay.geojson ---
  let overlayLayer = null;
  const overlayUrl = '{{ "/tiles/belt.geojson" | relative_url }}';
  
  // (optional) put overlay above the base map but below the info box
  map.createPane('overlayPane');
  map.getPane('overlayPane').style.zIndex = 420; // OSM default tiles are ~200
    
  async function addOverlay() {
    try {
      const res = await fetch(overlayUrl, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const geojson = await res.json();
  
      overlayLayer = L.geoJSON(geojson, {
        pane: 'overlayPane',
        style: feature => ({
          color: '#1d4ed8',       // stroke
          weight: 1.5,
          opacity: 0.9,
          fillColor: '#1d4ed8',   // fill = same blue
          fillOpacity: 0.3        // semi-transparent
        }),  // <-- Changed semicolon to comma
        onEachFeature: (feature, layer) => {  // <-- Added missing onEachFeature function
          // Show "tropical rainbelt" text on click
          layer.bindPopup("tropical rainbelt");
        }  // <-- Removed extra closing brace
      }).addTo(map);
    } catch (err) {
      console.error('Failed to load overlay.geojson:', err);
    }
  }
  addOverlay();

  // Controls
  const opacitySlider = document.getElementById('opacitySlider');
  const opacityValue = document.getElementById('opacityValue');
  const toggleButton = document.getElementById('toggleLayer');
  const resetButton = document.getElementById('resetView');

  opacitySlider.addEventListener('input', function() {
    const opacity = this.value / 100;
    opacityValue.textContent = this.value + '%';
    if (temperatureLayer) temperatureLayer.setOpacity(opacity);
  });

  let layerVisible = true;
  toggleButton.addEventListener('click', function() {
    if (!temperatureLayer) return;
    if (layerVisible) {
      map.removeLayer(temperatureLayer);
      this.textContent = 'Show Temperature Layer';
    } else {
      map.addLayer(temperatureLayer);
      this.textContent = 'Hide Temperature Layer';
    }
    layerVisible = !layerVisible;
  });

  resetButton.addEventListener('click', function() {
    map.setView([-23, 25], 4);
  });

  // Scale + coordinates
  L.control.scale({ position: 'bottomleft' }).addTo(map);

  const coordsControl = L.control({ position: 'bottomright' });
  coordsControl.onAdd = function() {
    const div = L.DomUtil.create('div', 'leaflet-control-attribution leaflet-control');
    div.innerHTML = '<span id="coords">Move mouse to see coordinates</span>';
    return div;
  };
  coordsControl.addTo(map);

  map.on('mousemove', function(e) {
    const coords = document.getElementById('coords');
    if (coords) coords.textContent = `${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
  });
});
</script>

**Data Sources**

1. MSG-3 SEVIRI Land Surface Temperature retrieved for 11:00UTC yesterday (<span id="pageTopDate">Loading…</span>). Data available at [https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/MLST/](https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/MLST/).
2. GSF atmospheric reanalysis valid 00:00 UTC today. Data available at [https://nomads.ncep.noaa.gov/](https://nomads.ncep.noaa.gov/)

**Feedback**

This tracker is in development. Please get in touch with any suggestions.

**Supporting publications**

Howard, E. and Washington, R. (2019) ‘Drylines in Southern Africa: Rediscovering the Congo Air Boundary’, _Journal of Climate_, 32(23), pp. 8223–8242. Available at: [https://doi.org/10.1175/JCLI-D-19-0437.1.](https://doi.org/10.1175/JCLI-D-19-0437.1.)

Howard, E. and Washington, R. (2020) ‘Tracing Future Spring and Summer Drying in Southern Africa to Tropical Lows and the Congo Air Boundary’, _Journal of Climate_, 33(14), pp. 6205–6228. Available at: [https://doi.org/10.1175/JCLI-D-19-0755.1.](https://doi.org/10.1175/JCLI-D-19-0755.1.)

Knight, C., & Washington, R. (2024). 'Remote Midlatitude Control of Rainfall Onset at the Southern African Tropical Edge'. _Journal of Climate_, 37(8), 2519-2539. Available at: [https://doi.org/10.1175/JCLI-D-23-0446.1](https://doi.org/10.1175/JCLI-D-23-0446.1)
