for (id in airlines) {
    var name = airlines[id];
    var elementId = "airline-" + id;
    document.getElementById("airline-picker").insertAdjacentHTML('beforeend', "<li><input type='checkbox' onChange='redraw();' checked id='" + elementId + "'><label for='" + elementId + "' />" + airlines[id] + "</li>");
    airlines[id] = { name: name, cb: document.getElementById(elementId) }
}

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

function typesToAirlineNames(route) {
    var typeToNames = new Map();
    for (const [type, allAirlineIds] of Object.entries(route.type_to_airlines)) {
        var airlineIds = allAirlineIds.filter(id => { var cb = airlines[id].cb; /*console.log(cb.id + " -->> " + cb.checked);*/ return cb.checked; });
        if (airlineIds.length) {
            typeToNames.set(type, airlineIds.map(id => airlines[id].name).join(', '));
        }
    }
    return typeToNames;
}

function redraw() {
for (id in airlines) { var cb = airlines[id].cb; console.log(id + " -> " + cb + " == " + cb.checked + " with ID " + cb.id); }
console.log("blu " + currentIcao + " in? " + isInbound);
    document.getElementById("airport-" + currentIcao).innerText = isInbound ? airportArrive : airportDepart;
    while (shown.length) shown.pop().removeFrom(map);
    endpoints.clear();
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var colour = undefined
        var tooltip;
        if (from == currentIcao && !isInbound) {
            colour = "red"; tooltip = "To " + to;
        } else if (to == currentIcao && isInbound) {
            colour = "blue"; tooltip = "From " + from;
        } else {
            continue;
        }
        var airlinesByType = typesToAirlineNames(routes[route])
        if (!airlinesByType.size) continue;
        airlinesByType.forEach((names, type) => tooltip += '<br/>' + type + ": " + names);
        endpoints.set(to, 'to');
        endpoints.set(from, 'from');
        var orientation = 0;
        var polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: colour, weight: 2})
            .setText(routes[route].distance + '►', {repeat: true, attributes: {fill: colour}, orientation: orientation, below: isInbound})
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

function airportClicked(e) {
    var icao = e.target.options.icao;
    if (icao == currentIcao) {
        isInbound = !isInbound;
    } else {
        if (currentIcao) document.getElementById("airport-" + currentIcao).innerText = airportNeutral;
        currentIcao = icao;
    }
    redraw();
}

for (icao in airports) {
    const airport = airports[icao];
    const icon = L.divIcon({html: "<span id='airport-" + icao + "'>" + airportNeutral + "</span></br>" + airport['iata'], className: 'airport'});
    airport.marker = L.marker(airport.latlng, {icao: icao, icon: icon}).addTo(map)
        .bindTooltip("<b>" + icao + "</b><br/>" + airport.names.join('<br/>'))
        .on('click', airportClicked);
}
