var map = L.map('map').setView([51.55, -0.1], 9.5);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const shown = [];

var currentIcao = "-none-";
var isInbound = false;

function airportClicked(e) {
    var icao = e.target.options.icao;
    if (icao == currentIcao)
        isInbound = !isInbound;
    else
        currentIcao = icao;
    while (shown.length) shown.pop().removeFrom(map);
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var colour = undefined, tooltip = Object.getOwnPropertyNames(routes[route].type_to_airlines).map(type => type + ": " + routes[route].type_to_airlines[type].join(', ')).join('</br>') + ' ';
        if (from == icao && !isInbound) {
            colour = "blue"; tooltip += "from " + from;
        } else if (to == icao && isInbound) {
            colour = "red"; tooltip += "to " + to;
        } else
            continue;
        var polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: colour}).bindTooltip(tooltip);
        shown.push(polyline);
        polyline.setText((colour != "purple" ? '' :   '◄') + routes[route].distance + '►', {repeat: true, attributes: {fill: colour}});
        polyline.addTo(map);
    }
}

const airportIcon = L.divIcon({html: "\u1F6EB;\u1F6EC;"});
for (icao in airports) {
    const airport = airports[icao];
    const icon = L.divIcon({html: "\u2708;</br>" + airport['iata'], className: 'airport'});
    airport.marker = L.marker(airport.latlng, {icao: icao, icon: icon}).addTo(map)
        .bindTooltip("<b>" + icao + "</b><br/>" + airport.names.join('<br/>'))
        .on('click', airportClicked);
}
