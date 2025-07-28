---
layout: page
title: Fieldwork
permalink: /fieldwork/
---

Recent fieldwork projects:

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>

<div id="map" style="height: 600px; width: 100%; margin-top: 1em;"></div>

<script>
document.addEventListener("DOMContentLoaded", function () {
  var map = L.map('map').setView([0, 26], 4);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map); 
  // Define custom red and green icons
  var redIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
  var greenIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
    var blueIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
    var orangeIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });
    var violetIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-violet.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  });

  // Apply colored markers
  var marker1 = L.marker([-11.2495, 24.3273], { icon: redIcon }).addTo(map);
  marker1.bindPopup("DRYCAB (click to open)");
  marker1.on("click", function () {
    window.location.href = "https://charlesknight1.github.io/drycab";
  });
  
});
</script>

**2025**
- [Kalahari Drylines](https://charlesknight1.github.io/drylines)

**2024**
- [Masika: East African Long Rains](https://charlesknight1.github.io/masika)

**2023**
- [KAPEX: Kalahari Atmospheric Processes Experiment](https://charlesknight1.github.io/kapex)
- [WesCON-WOEST: Atmospheric observations with UAS](https://charlesknight1.github.io/wescon)

**2022**
- [DRYCAB: Decreasing Rainfall to Year 2100 Role of the Congo Air Boundary](https://charlesknight1.github.io/drycab)
