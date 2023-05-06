for (const [id, airline] of Object.entries(airlines)) {
    var elementId = "airline-" + id;
    document.getElementById("airline-picker").insertAdjacentHTML('beforeend',
        `<li><input type='checkbox' onmouseover='redraw(${id});' onmouseout='redraw();' onChange='redraw();' checked id='${elementId}'>`
        + `<label for='${elementId}' title='${airline.rank_info}' />${airline.name}` + (airline.requirements ? `<sup title='${airline.requirements}'>*</sup>` : "") + `</li>`);
    airline.cb = document.getElementById(elementId);
}

var map = L.map('map').setView([51.55, 10.1], 4.5);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const shown = new Map();
const endpoints = new Map();

var currentIcao = undefined;
var isInbound = false;

const airportNeutral = "\u2708";
const airportDepart = "\ud83d\udeeb"; // 1F6EB as a surrogate pair
const airportArrive = "\ud83d\udeec"; // 1F6EC

function typesToAirlineNames(route, airlineFilter) {
    var typeToNames = new Map();
    for (const [type, allAirlineIds] of Object.entries(route.type_to_airlines)) {
        var airlineIds = allAirlineIds.filter(airlineFilter);
        if (airlineIds.length) {
            typeToNames.set(type, airlineIds.map(id => airlines[id].name).join(', '));
        }
    }
    return typeToNames;
}

function mergeEndpoint(icao, direction) {
    var existing = endpoints.get(icao);
    if (existing && existing != direction)
        direction = 'both';
    endpoints.set(icao, direction);
}

function redraw(airlineId) {
//for (id in airlines) { var cb = airlines[id].cb; console.log(id + " -> " + cb + " == " + cb.checked + " with ID " + cb.id); }
console.log(`currentIcao ${currentIcao} in? ${isInbound}, airline ${airlineId}`);
    if (currentIcao)
        document.getElementById("airport-" + currentIcao).innerText = isInbound ? airportArrive : airportDepart;
    for (polyline of shown.values()) polyline.removeFrom(map);
    shown.clear();
    endpoints.clear();
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var tooltip;
        var airlineFilter = id => { var cb = airlines[id].cb; /*console.log(`${cb.id} -->> ${cb.checked}`);*/ return cb.checked; };
        if (airlineId) {
            airlineFilter = id => id == airlineId;
        } else if (from == currentIcao && !isInbound) {
            tooltip = "To " + to;
        } else if (to == currentIcao && isInbound) {
            tooltip = "From " + from;
        } else {
            continue;
        }
        var airlinesByType = typesToAirlineNames(routes[route], airlineFilter);
        if (!airlinesByType.size) continue;
        tooltip += `, ${routes[route].distance}`
        airlinesByType.forEach((names, type) => tooltip += `<br/>${type}: ${names}`);
        mergeEndpoint(to, 'to');
        mergeEndpoint(from, 'from');
        var canonicalRoute = to < from ? `${to}-${from}` : `${from}-${to}`;
        var polyline = shown.get(canonicalRoute);
        if (!polyline) {
            polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: 'purple', weight: 1.5});
            if (tooltip)
                polyline.bindTooltip(tooltip, {sticky: true});
            polyline.addTo(map);
            shown.set(canonicalRoute, polyline);
        }
    }
    for (icao in airports) {
        var classList = airports[icao].marker.getElement().classList;
        ["to", "from", "both"].forEach(css => classList.remove(`airport-${css}`));
        if (endpoints.has(icao)) classList.add(`airport-${endpoints.get(icao)}`);
    }
}

var icaoClicks = 0;
function airportClicked(e) {
    var icao = e.target.options.icao;
    if (currentIcao) document.getElementById("airport-" + currentIcao).innerText = airportNeutral;
    if (icao == currentIcao) {
        if (++icaoClicks >= 2)
            currentIcao = undefined;
        else
            isInbound = !isInbound;
    } else {
        currentIcao = icao;
        icaoClicks = 0;
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
