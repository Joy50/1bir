L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png", {
  minZoom: 1,
  maxZoom: 20,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &mdash; ' +
    '<a href="https://openstreetmap.fr/" target="_blank">OSM France</a>'
}).addTo(map);