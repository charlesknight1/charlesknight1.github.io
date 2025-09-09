---
layout: post
title: Congo Air Boundary Tracker
permalink: /cabtracker
categories: projects
---
Live Congo Air Boundary tracker.

Data is up to date as of <span id="pageTopDate">Loading…</span>.

History:

<!-- Chart.js and D3 (for CSV parsing) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>

<canvas id="trend" height="120"></canvas>
<script>
(async () => {
  const data = await d3.csv('database/rainbelthistory.csv', d3.autoType);
  // data: [{date:"2025-09-09", total_features:131, avg_value:16.9, max_value:90}, ...]

  const labels = data.map(d => d.date);
  const totals = data.map(d => d.total_features);

  const ctx = document.getElementById('trend').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Total features', data: totals, tension: 0.2, pointRadius: 0 }
        // add more datasets with data.map(d => d.avg_value) etc.
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { ticks: { autoSkip: true, maxRotation: 0 } },
        y: { beginAtZero: true }
      }
    }
  });
})();
</script>

Live:

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
.cab-legend-item {
  display: flex;
  align-items: center;
  margin: 5px 0;
  font-size: 12px;
}
.cab-legend-symbol {
  width: 12px;
  height: 8px;
  margin-right: 8px;
  border: 1px solid #16a34a;
  background-color: #16a34a;
}
.rainbelt-legend-symbol {
  width: 16px;
  height: 12px;
  margin-right: 8px;
  border: 1px solid #1d4ed8;
  background-color: rgba(29, 78, 216, 0.3);
}
</style>

<div class="map-controls">
  <button id="toggleLayer">Hide LST Layer</button>
  <button id="toggleRainbelt">Hide Rainbelt</button>
  <button id="toggleCAB">Hide CAB Points</button>
  <button id="resetView">Reset View</button>
</div>

<div id="map" style="height: 500px; width: 100%; position: relative;">
</div>

<div class="legend">
  <strong>Land Surface Temperature (°C)</strong>
  <div class="legend-gradient"></div>
  <div class="legend-labels">
    <span>0°C</span>
    <span>25°C</span>
    <span>50°C</span>
  </div>
  <div style="margin-top: 10px; border-top: 1px solid #ccc; padding-top: 10px;">
    <strong>Map Features</strong>
    <div class="cab-legend-item">
      <div class="cab-legend-symbol"></div>
      <span>Congo Air Boundary Points</span>
    </div>
    <div class="cab-legend-item">
      <div class="rainbelt-legend-symbol"></div>
      <span>Tropical Rainbelt</span>
    </div>
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
      const pageTopEl = document.getElementById('pageTopDate');
      
      if (lastMod) {
        const d = new Date(lastMod);
        const nice = d.toLocaleString('en-GB', {
          timeZone: 'UTC',
          year: 'numeric',
          month: 'short',
          day: '2-digit',
        });
        if (pageTopEl) pageTopEl.textContent = `${nice}`;
      } else {
        if (pageTopEl) pageTopEl.textContent = 'Unavailable';
      }
    } catch (e) {
      console.error('HEAD request failed:', e);
      const pageTopEl = document.getElementById('pageTopDate');
      if (pageTopEl) pageTopEl.textContent = 'Error fetching';
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
  let overlayLayer = null;
  const overlayUrl = '{{ "/tiles/belt.geojson" | relative_url }}';
  
  // Put overlay above the base map but below the info box
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
        }),
        onEachFeature: (feature, layer) => {
          // Show "tropical rainbelt" text on click
          layer.bindPopup("Tropical Rainbelt");
        }
      }).addTo(map);
    } catch (err) {
      console.error('Failed to load belt.geojson:', err);
    }
  }
  addOverlay();

  // Congo Air Boundary points
  let cabLayer = null;
  const cabUrl = '{{ "/tiles/drylines.geojson" | relative_url }}';
  
  // Create a pane for CAB points to ensure proper layering
 // Create panes for different sources
map.createPane('cabPane');
map.getPane('cabPane').style.zIndex = 435;

map.createPane('kdPane');
map.getPane('kdPane').style.zIndex = 430; // Below cab

map.createPane('drylinePane');
map.getPane('drylinePane').style.zIndex = 425; // below kd


// Source configuration
const sourceConfig = {
  'cab': {
    color: '#16a34a',      // Green
    label: 'Congo Air Boundary',
    pane: 'cabPane'
  },
  'kd': {
    color: '#dc2626',      // Red
    label: 'Kalahari Discontinuity',
    pane: 'kdPane'
  },
    'dryline': {
      color: '#ffffff',      // Gray
      label: 'Dryline',
      pane: 'drylinePane'
    },
};
    
async function addCABPoints() {
  try {
    const res = await fetch(cabUrl, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const geojson = await res.json();

    cabLayer = L.geoJSON(geojson, {
      pointToLayer: function(feature, latlng) {
        const source = feature.properties?.source || 'default';
        const config = sourceConfig[source] || sourceConfig['default'];
        
        // Create small rectangles with source-specific colors
        return L.rectangle([
          [latlng.lat - 0.13, latlng.lng - 0.13], // Southwest corner
          [latlng.lat + 0.13, latlng.lng + 0.13]  // Northeast corner
        ], {
          color: config.color,        // Source-specific border color
          weight: 1,
          opacity: 1,
          fillColor: config.color,    // Source-specific fill color
          fillOpacity: 0.8,
          pane: config.pane           // Use source-specific pane
        });
      },
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        const source = props.source || 'default';
        const config = sourceConfig[source] || sourceConfig['default'];
        
        let popupContent = `<strong>${config.label}</strong>`;
        
        // Add any available properties to popup
        if (Object.keys(props).length > 0) {
          popupContent += "<br><br>";
          for (const [key, value] of Object.entries(props)) {
            if (value !== null && value !== undefined) {
              popupContent += `<strong>${key}:</strong> ${value}<br>`;
            }
          }
        }
        
        layer.bindPopup(popupContent);
      }
    }).addTo(map);
    
    console.log(`Loaded ${geojson.features?.length || 0} points`);
  } catch (err) {
    console.error('Failed to load geojson:', err);
  }
  }
  addCABPoints();

  // Controls
  const toggleButton = document.getElementById('toggleLayer');
  const toggleCABButton = document.getElementById('toggleCAB');
  const toggleRainbeltButton = document.getElementById('toggleRainbelt');
  const resetButton = document.getElementById('resetView');

  let layerVisible = true;
  toggleButton.addEventListener('click', function() {
    if (!temperatureLayer) return;
    if (layerVisible) {
      map.removeLayer(temperatureLayer);
      this.textContent = 'Show LST Layer';
    } else {
      map.addLayer(temperatureLayer);
      this.textContent = 'Hide LST Layer';
    }
    layerVisible = !layerVisible;
  });

  let cabVisible = true;
  toggleCABButton.addEventListener('click', function() {
    if (!cabLayer) return;
    if (cabVisible) {
      map.removeLayer(cabLayer);
      this.textContent = 'Show CAB Points';
    } else {
      map.addLayer(cabLayer);
      this.textContent = 'Hide CAB Points';
    }
    cabVisible = !cabVisible;
  });

  let rainbeltVisible = true;
  toggleRainbeltButton.addEventListener('click', function() {
    if (!overlayLayer) return;
    if (rainbeltVisible) {
      map.removeLayer(overlayLayer);
      this.textContent = 'Show Rainbelt';
    } else {
      map.addLayer(overlayLayer);
      this.textContent = 'Hide Rainbelt';
    }
    rainbeltVisible = !rainbeltVisible;
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
3. Congo Air Boundary gridcells detected with the canny edge method of Howard and Washington (2019) availible on [GitHub](https://github.com/EmmaHoward/drylines)

**Feedback**

This tracker is in development. Please get in touch with any suggestions.

**Supporting publications**

Howard, E. and Washington, R. (2019) 'Drylines in Southern Africa: Rediscovering the Congo Air Boundary', _Journal of Climate_, 32(23), pp. 8223–8242. Available at: [https://doi.org/10.1175/JCLI-D-19-0437.1.](https://doi.org/10.1175/JCLI-D-19-0437.1.)

Howard, E. and Washington, R. (2020) 'Tracing Future Spring and Summer Drying in Southern Africa to Tropical Lows and the Congo Air Boundary', _Journal of Climate_, 33(14), pp. 6205–6228. Available at: [https://doi.org/10.1175/JCLI-D-19-0755.1.](https://doi.org/10.1175/JCLI-D-19-0755.1.)

Knight, C., & Washington, R. (2024). 'Remote Midlatitude Control of Rainfall Onset at the Southern African Tropical Edge'. _Journal of Climate_, 37(8), 2519-2539. Available at: [https://doi.org/10.1175/JCLI-D-23-0446.1](https://doi.org/10.1175/JCLI-D-23-0446.1)
