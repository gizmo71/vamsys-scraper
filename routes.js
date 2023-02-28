var map = L.map('map').setView([51.55, -0.1], 9.5);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const shown = [];
const endpoints = new Map();

var currentIcao = undefined;
var isInbound = false;

const airportNeutral = "\u2708";
const airportDepart = "\ud83d\udeeb"; // 1F6EB as a surrogate pair
const airportArrive = "\ud83d\udeec"; // 1F6EC

function airportClicked(e) {
    var icao = e.target.options.icao;
    if (icao == currentIcao) {
        isInbound = !isInbound;
    } else {
        if (currentIcao) document.getElementById("airport-" + currentIcao).innerText = airportNeutral;
        currentIcao = icao;
    }
    document.getElementById("airport-" + currentIcao).innerText = isInbound ? airportArrive : airportDepart;
    while (shown.length) shown.pop().removeFrom(map);
    endpoints.clear();
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var colour = undefined
        var tooltip = Object.getOwnPropertyNames(routes[route].type_to_airlines).map(type => type + ": " + routes[route].type_to_airlines[type].join(', ')).join('</br>') + ' ';
        if (from == icao && !isInbound) {
            colour = "red"; tooltip += "to " + to;
        } else if (to == icao && isInbound) {
            colour = "blue"; tooltip += "from " + from;
        } else
            continue;
        endpoints.set(to, 'to');
        endpoints.set(from, 'from');
        var polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: colour, weight: 2})
            .setText(routes[route].distance + '►', {repeat: true, attributes: {fill: colour}})
            .bindTooltip(tooltip, {sticky: true})
            .addTo(map);
        shown.push(polyline);
    }
    for (icao in airports) {
        var classList = airports[icao].marker.getElement().classList;
        classList.remove("airport-to");
        classList.remove("airport-from");
        if (endpoints.has(icao)) classList.add("airport-" + endpoints.get(icao));
    }
}

for (icao in airports) {
    const airport = airports[icao];
    const icon = L.divIcon({html: "<span id='airport-" + icao + "'>" + airportNeutral + "</span></br>" + airport['iata'], className: 'airport'});
    airport.marker = L.marker(airport.latlng, {icao: icao, icon: icon}).addTo(map)
        .bindTooltip("<b>" + icao + "</b><br/>" + airport.names.join('<br/>'))
        .on('click', airportClicked);
}
