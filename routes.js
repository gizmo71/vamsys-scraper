var map = L.map('map').setView([51.55, -0.1], 9.5);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const shown = [];

function airportClicked(e) {
    var icao = e.target.options.icao;
    while (shown.length) shown.pop().removeFrom(map);
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        if (icao != to && icao != from) continue;
        var colour = undefined, tooltip = routes[route].airlines.join(', ') + ' ';
        if (routes.hasOwnProperty(to + "-" + from)) {
            if (to == icao) continue; // Only do one copy of the route
            colour = "purple", tooltip += "to/from " + to;
        } else if (from != icao) {
            colour = "blue"; tooltip += "from " + from;
        } else if (to != icao) {
            colour = "red"; tooltip += "to " + to;
        }
        var polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: colour}).bindTooltip(tooltip);
        shown.push(polyline);
        polyline.setText((colour != "purple" ? '' :   '◄') + routes[route].distance + '►', {repeat: true, attributes: {fill: colour}});
        polyline.addTo(map);
    }
}

for (airport in airports) {
    L.marker(airports[airport].latlng, {icao: airport}).addTo(map)
        .bindTooltip("<b>" + airport + "</b><br/>" + airports[airport].names.join('<br/>'))
        .on('click', airportClicked);
}
