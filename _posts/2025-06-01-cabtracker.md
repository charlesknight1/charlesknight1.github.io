---
layout: post
title: Congo Air Boundary Tracker
permalink: /tracker
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
  const rainbelt = await d3.csv('database/rainbelt_history.csv', d3.autoType);
  const cab      = await d3.csv('database/cab_history.csv', d3.autoType);
  const hl       = await d3.csv('database/heatlow_history.csv', d3.autoType);

  // normalize YYYYMMDD -> YYYY-MM-DD
  function normDate(d) {
    return d.slice(0,4) + "-" + d.slice(4,6) + "-" + d.slice(6,8);
  }

  // labels from rainbelt
  const labels = rainbelt.map(d => normDate(String(d.date)));
  const rainbeltValues = rainbelt.map(d => d.mean_latitude);

  // CAB
  const cabMap = new Map(cab.map(d => [normDate(String(d.date)), d.cab_lat]));
  const cabValues = labels.map(d => cabMap.get(d) ?? null);

  // Heat lows
  const hlMapN = new Map(hl.map(d => [normDate(String(d.date)), d.northheatlow_lat]));
  const hlMapS = new Map(hl.map(d => [normDate(String(d.date)), d.southheatlow_lat]));
  const hlValuesN = labels.map(d => hlMapN.get(d) ?? null);
  const hlValuesS = labels.map(d => hlMapS.get(d) ?? null);

  const ctx = document.getElementById('trend').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Tropical rainbelt latitude',
          data: rainbeltValues,
          borderColor: '#1d4ed8',
          backgroundColor: '#1d4ed8',
          tension: 0.2,
          pointRadius: 0
        },
        {
          label: 'CAB latitude',
          data: cabValues,
          borderColor: '#16a34a',
          backgroundColor: '#16a34a',
          tension: 0.2,
          pointRadius: 2,
          spanGaps: true
        },
        {
          label: '',
          data: hlValuesN,
          borderColor: '#ff0000',
          backgroundColor: '#ff0000',
          borderDash: [4,3],
          tension: 0.2,
          pointRadius: 2,
          spanGaps: true
        },
        {
          data: hlValuesS,
          borderColor: '#ff0000',
          backgroundColor: '#ff0000',
          borderDash: [6,3],
          tension: 0.2,
          pointRadius: 2,
          spanGaps: true,
          label: 'Heat Lows',
        }

      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: { usePointStyle: true, boxWidth: 10 }
        }
      },
      scales: {
        x: {
          ticks: { autoSkip: true, maxRotation: 0 }
        },
        y: {
          min: -28,
          max: 28,
          title: { display: true, text: 'Latitude (°)' }
        }
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

.layer-control {
  background: white;
  border-radius: 5px;
  box-shadow: 0 1px 5px rgba(0,0,0,0.4);
  min-width: 200px;
  overflow: hidden;
}

.layer-control-header {
  padding: 8px 10px;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
  transition: background-color 0.2s;
}

.layer-control-header:hover {
  background: #e9ecef;
}

.layer-control-title {
  font-weight: bold;
  font-size: 14px;
  color: #333;
  margin: 0;
}

.layer-control-toggle {
  font-size: 16px;
  color: #666;
  transition: transform 0.3s ease;
}

.layer-control-toggle.collapsed {
  transform: rotate(-90deg);
}

.layer-control-content {
  padding: 10px;
  transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
  overflow: hidden;
}

.layer-control-content.collapsed {
  max-height: 0 !important;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.layer-checkbox-control {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  cursor: pointer;
  font-size: 11px;
  color: #555;
  user-select: none;
}

.layer-checkbox-control:hover {
  color: #0066cc;
  background-color: #f8f8f8;
  border-radius: 3px;
  padding-left: 4px;
  margin-left: -4px;
}

.layer-checkbox-control input[type="checkbox"] {
  cursor: pointer;
  transform: scale(1.1);
  margin: 0;
}

.layer-control-separator {
  border-top: 1px solid #eee;
  margin: 8px 0;
}

.layer-reset-button {
  width: 100%;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #495057;
  transition: all 0.2s;
}

.layer-reset-button:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.layer-reset-button:active {
  background: #dee2e6;
}

/* Make sure the control doesn't interfere with map interactions */
.layer-control * {
  pointer-events: auto;
}

/* Optional: Collapsible control for mobile */
@media (max-width: 768px) {
  .layer-control {
    min-width: 180px;
  }
  
  .layer-control-content {
    padding: 8px;
  }
  
  .layer-checkbox-control {
    font-size: 12px;
  }
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


<div id="map" style="height: 500px; width: 100%; position: relative;">
</div>

<style>
.map-legend {
  background:#fff; border:1px solid #ddd; border-radius:6px;
  box-shadow:0 1px 4px rgba(0,0,0,.1);
  margin:12px 0 0; padding:10px 12px; font-size:12px; color:#333;
  max-width:600px;
}
.map-legend h4 { margin:0 0 6px; font-size:13px; }
.legend-row { display:flex; align-items:center; gap:8px; margin:4px 0; }
.legend-key { flex:0 0 auto; width:16px; height:12px; border:1px solid #888; }
.legend-key.square { width:12px; height:12px; }
.legend-gradient {width: 100%; height: 12px; background: linear-gradient(to right, #ffffff 0%, #000000 100%); border: 1px solid #ccc; border-radius: 2px; }
.legend-ticks { display:flex; justify-content:space-between; font-size:11px; color:#444; margin-top:2px; }
</style>

<section class="map-legend">
  <h4>Land Surface Temp (°C)</h4>
  <div id="lstGradient" class="legend-gradient"></div>
  <div class="legend-ticks">
    <span id="lstMin">0°</span>
    <span id="lstMid">25°</span>
    <span id="lstMax">50°</span>
  </div>

  <h4 style="margin-top:8px;">Map Features</h4>
  <div class="legend-row">
    <span class="legend-key" style="background:rgba(29,78,216,.3); border-color:#1d4ed8;"></span>
    <span>Tropical Rainbelt</span>
  </div>
  <div class="legend-row">
    <span class="legend-key square" style="background:#16a34a; border-color:#15803d;"></span>
    <span>Congo Air Boundary</span>
  </div>
  <div class="legend-row">
    <span class="legend-key square" style="background:#dc2626; border-color:#b91c1c;"></span>
    <span>Kalahari Discontinuity</span>
  </div>
  <div class="legend-row">
    <span class="legend-key square" style="background:#ffffff; border-color:#999;"></span>
    <span>Other Dryline</span>
  </div>
  <div class="legend-row">
    <span class="legend-key" style="background:rgba(255,0,0,.2); border-color:#ff0000;"></span>
    <span>Northern African Heat Low</span>
  </div>
  <div class="legend-row">
    <span class="legend-key" style="background:rgba(255,0,0,.2); border-color:#ff0000;"></span>
    <span>Southern African Heat Low</span>
  </div>
</section>

<script>
document.addEventListener("DOMContentLoaded", async function () {
  const map = L.map('map').setView([0, 20], 3);

  // Base layer
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  // Create custom collapsible control for layer toggles
  const layerControl = L.control({ position: 'topright' });

  layerControl.onAdd = function(map) {
    const div = L.DomUtil.create('div', 'leaflet-control leaflet-bar layer-control');
    
    div.innerHTML = `
      <div class="layer-control-header" id="layerControlHeader">
        <div class="layer-control-title">Map Layers</div>
        <div class="layer-control-toggle collapsed" id="layerControlToggle">►</div>
      </div>
      <div class="layer-control-content collapsed" id="layerControlContent">
        <label class="layer-checkbox-control">
          <input type="checkbox" id="toggleLayer" checked>
          <span>Land Surface Temperature</span>
        </label>
        
        <label class="layer-checkbox-control">
          <input type="checkbox" id="toggleRainbelt" checked>
          <span>Tropical Rainbelt</span>
        </label>
        
        <label class="layer-checkbox-control">
          <input type="checkbox" id="toggleCAB" checked>
          <span>Drylines</span>
        </label>
        
        <label class="layer-checkbox-control">
          <input type="checkbox" id="toggleNorthHeatLow" checked>
          <span>Northern African Heat Low</span>
        </label>
        
        <label class="layer-checkbox-control">
          <input type="checkbox" id="toggleSouthHeatLow" checked>
          <span>Southern African Heat Low</span>
        </label>
        
        <div class="layer-control-separator"></div>
        
        <button id="resetView" class="layer-reset-button">Reset View</button>
      </div>
    `;
    
    // Prevent map interaction when clicking on the control
    L.DomEvent.disableClickPropagation(div);
    L.DomEvent.disableScrollPropagation(div);
    
    return div;
  };

  layerControl.addTo(map);

  let temperatureLayer = null;
  const pmtilesUrl = '/tiles/raster.pmtiles';

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
    const dateInfo = document.getElementById('dateInfo');
    const pageTopDate = document.getElementById('pageTopDate');
    if (dateInfo) dateInfo.textContent = 'Date: Error loading data';
    if (pageTopDate) pageTopDate.textContent = 'Error loading data';
  }

  // Rainbelt overlay
  let rainbeltLayer = null;
  const rainbeltUrl = '/tiles/belt.geojson';
  
  map.createPane('rainbeltPane');
  map.getPane('rainbeltPane').style.zIndex = 420;
    
  async function addRainbelt() {
    try {
      const res = await fetch(rainbeltUrl, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const geojson = await res.json();
  
      rainbeltLayer = L.geoJSON(geojson, {
        pane: 'rainbeltPane',
        style: feature => ({
          color: '#1d4ed8',
          weight: 1.5,
          opacity: 0.9,
          fillColor: '#1d4ed8',
          fillOpacity: 0.3
        }),
        onEachFeature: (feature, layer) => {
          layer.bindPopup("Tropical Rainbelt");
        }
      }).addTo(map);
    } catch (err) {
      console.error('Failed to load belt.geojson:', err);
    }
  }
  addRainbelt();

  // North heat low overlay
  let northHeatLowLayer = null;
  const northHeatLowUrl = '/tiles/north_heat_low.geojson';
  
  map.createPane('northHeatLowPane');
  map.getPane('northHeatLowPane').style.zIndex = 421;
    
  async function addNorthHeatLow() {
    try {
      const res = await fetch(northHeatLowUrl, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const geojson = await res.json();
  
      northHeatLowLayer = L.geoJSON(geojson, {
        pane: 'northHeatLowPane',
        style: feature => ({
          color: '#FF0000',
          weight: 1,
          opacity: 0.9,
          fillColor: '#FF0000',
          fillOpacity: 0.2
        }),
        onEachFeature: (feature, layer) => {
          layer.bindPopup("Northern African Heat Low");
        }
      }).addTo(map);
    } catch (err) {
      console.error('Failed to load north_heat_low.geojson:', err);
    }
  }
  addNorthHeatLow();

  // South heat low overlay
  let southHeatLowLayer = null;
  const southHeatLowUrl = 'tiles/south_heat_low.geojson'; 
  
  map.createPane('southHeatLowPane');
  map.getPane('southHeatLowPane').style.zIndex = 422;
    
  async function addSouthHeatLow() {
    try {
      const res = await fetch(southHeatLowUrl, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const geojson = await res.json();
  
      southHeatLowLayer = L.geoJSON(geojson, {
        pane: 'southHeatLowPane',
        style: feature => ({
          color: '#FF0000',
          weight: 1,
          opacity: 0.9,
          fillColor: '#FF0000',
          fillOpacity: 0.2
        }),
        onEachFeature: (feature, layer) => {
          layer.bindPopup("Southern African Heat Low");
        }
      }).addTo(map);
    } catch (err) {
      console.error('Failed to load south_heat_low.geojson:', err);
    }
  }
  addSouthHeatLow();

  // Congo Air Boundary points
  let cabLayer = null;
  const cabUrl = '{{ "/tiles/drylines.geojson" | relative_url }}';
  
  // Create panes for different sources
  map.createPane('cabPane');
  map.getPane('cabPane').style.zIndex = 435;

  map.createPane('kdPane');
  map.getPane('kdPane').style.zIndex = 430;

  map.createPane('drylinePane');
  map.getPane('drylinePane').style.zIndex = 425;

  // Source configuration
  const sourceConfig = {
    'cab': {
      color: '#16a34a',
      label: 'Congo Air Boundary',
      pane: 'cabPane'
    },
    'kd': {
      color: '#dc2626',
      label: 'Kalahari Discontinuity',
      pane: 'kdPane'
    },
    'dryline': {
      color: '#ffffff',
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
          const config = sourceConfig[source] || sourceConfig['cab'];
          
          return L.rectangle([
            [latlng.lat - 0.13, latlng.lng - 0.13],
            [latlng.lat + 0.13, latlng.lng + 0.13]
          ], {
            color: config.color,
            weight: 1,
            opacity: 1,
            fillColor: config.color,
            fillOpacity: 0.8,
            pane: config.pane
          });
        },
        onEachFeature: (feature, layer) => {
          const props = feature.properties || {};
          const source = props.source || 'default';
          const config = sourceConfig[source] || sourceConfig['cab'];
          
          let popupContent = `<strong>${config.label}</strong>`;
          
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

  // Collapsible control functionality
  let isCollapsed = true;
  
  function toggleLayerControl() {
    const content = document.getElementById('layerControlContent');
    const toggle = document.getElementById('layerControlToggle');
    
    if (!content || !toggle) return;
    
    isCollapsed = !isCollapsed;
    
    if (isCollapsed) {
      content.style.maxHeight = '0px';
      content.classList.add('collapsed');
      toggle.classList.add('collapsed');
      toggle.textContent = '►';
    } else {
      // Calculate natural height
      content.style.maxHeight = 'none';
      const naturalHeight = content.scrollHeight;
      content.style.maxHeight = '0px';
      
      // Force reflow then animate to natural height
      requestAnimationFrame(() => {
        content.style.maxHeight = naturalHeight + 'px';
        content.classList.remove('collapsed');
        toggle.classList.remove('collapsed');
        toggle.textContent = '▼';
      });
    }
  }

  // Controls - Wait for control to be added to DOM
  setTimeout(() => {
    const header = document.getElementById('layerControlHeader');
    const toggleLayerCheckbox = document.getElementById('toggleLayer');
    const toggleCABCheckbox = document.getElementById('toggleCAB');
    const toggleRainbeltCheckbox = document.getElementById('toggleRainbelt');
    const toggleNorthHeatLowCheckbox = document.getElementById('toggleNorthHeatLow');
    const toggleSouthHeatLowCheckbox = document.getElementById('toggleSouthHeatLow');
    const resetButton = document.getElementById('resetView');

    // Add collapse/expand functionality
    if (header) {
      header.addEventListener('click', toggleLayerControl);
    }

    if (toggleLayerCheckbox) {
      toggleLayerCheckbox.addEventListener('change', function() {
        if (!temperatureLayer) return;
        if (this.checked) {
          map.addLayer(temperatureLayer);
        } else {
          map.removeLayer(temperatureLayer);
        }
      });
    }

    if (toggleCABCheckbox) {
      toggleCABCheckbox.addEventListener('change', function() {
        if (!cabLayer) return;
        if (this.checked) {
          map.addLayer(cabLayer);
        } else {
          map.removeLayer(cabLayer);
        }
      });
    }

    if (toggleRainbeltCheckbox) {
      toggleRainbeltCheckbox.addEventListener('change', function() {
        if (!rainbeltLayer) return;
        if (this.checked) {
          map.addLayer(rainbeltLayer);
        } else {
          map.removeLayer(rainbeltLayer);
        }
      });
    }

    if (toggleNorthHeatLowCheckbox) {
      toggleNorthHeatLowCheckbox.addEventListener('change', function() {
        if (!northHeatLowLayer) return;
        if (this.checked) {
          map.addLayer(northHeatLowLayer);
        } else {
          map.removeLayer(northHeatLowLayer);
        }
      });
    }

    if (toggleSouthHeatLowCheckbox) {
      toggleSouthHeatLowCheckbox.addEventListener('change', function() {
        if (!southHeatLowLayer) return;
        if (this.checked) {
          map.addLayer(southHeatLowLayer);
        } else {
          map.removeLayer(southHeatLowLayer);
        }
      });
    }

    if (resetButton) {
      resetButton.addEventListener('click', function() {
        map.setView([0, 20], 3);
      });
    }
  }, 100);

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

1. MSG-3 SEVIRI Land Surface Temperature retrieved for 11:00UTC yesterday. Data available at [https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/MLST/](https://datalsasaf.lsasvcs.ipma.pt/PRODUCTS/MSG/MLST/).
2. GSF atmospheric analysis valid 00:00 UTC today. Data available at [https://nomads.ncep.noaa.gov/](https://nomads.ncep.noaa.gov/)
3. Congo Air Boundary gridcells detected with the canny edge method of Howard and Washington (2019) available on [GitHub](https://github.com/EmmaHoward/drylines).

**Feedback**

This page is experimental and in development. Please get in touch with any suggestions.

**Supporting publications**

Attwood, K., Washington, R. and Munday, C. (2024) ‘The Southern African Heat Low: Structure, Seasonal and Diurnal Variability, and Climatological Trends’, Journal of Climate, 37(10), pp. 3037–3053. Available at: https://doi.org/10.1175/JCLI-D-23-0522.1.

Howard, E. and Washington, R. (2019) 'Drylines in Southern Africa: Rediscovering the Congo Air Boundary', _Journal of Climate_, 32(23), pp. 8223–8242. Available at: [https://doi.org/10.1175/JCLI-D-19-0437.1.](https://doi.org/10.1175/JCLI-D-19-0437.1.)

Howard, E. and Washington, R. (2020) 'Tracing Future Spring and Summer Drying in Southern Africa to Tropical Lows and the Congo Air Boundary', _Journal of Climate_, 33(14), pp. 6205–6228. Available at: [https://doi.org/10.1175/JCLI-D-19-0755.1.](https://doi.org/10.1175/JCLI-D-19-0755.1.)

Knight, C., & Washington, R. (2024). 'Remote Midlatitude Control of Rainfall Onset at the Southern African Tropical Edge'. _Journal of Climate_, 37(8), 2519-2539. Available at: [https://doi.org/10.1175/JCLI-D-23-0446.1](https://doi.org/10.1175/JCLI-D-23-0446.1)


