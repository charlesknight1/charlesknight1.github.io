---
layout: post
title: "Interactive Map of Southern Africa"
permalink: /leaflet-map/
categories: projects
---

Here’s a live map of Southern Africa using Leaflet.js.

<!-- Load Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-pgf+ZtSGYzAqpNXfsGUZ5UUnh19Q8zsa1ZWG9yyM0w8=" crossorigin=""/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-o9N1j0gLv2a/ORbDRhdf0r0V8vUUUwUBnTMOxE2v0uU=" crossorigin=""></script>

<!-- Map container -->
<div id="map" style="height: 500px; margin-top: 20px;"></div>

<!-- Map script -->
<script>
  var map = L.map('map').setView([-15, 25], 4);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

  L.marker([-15.5, 28.3]).addTo(map)
    .bindPopup('Lusaka, Zambia');
</script>
