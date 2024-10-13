for (const [id, airline] of Object.entries(airlines).toSorted(([id1, airline1], [id2, airline2]) => airline1.sortName.localeCompare(airline2.sortName))) {
    var elementId = "airline-" + id;
    var lastPirepDaysAgo = Math.ceil((Date.now() - Date.parse(airline['last_pirep_start'])) / 86400000)
    var days = `+${lastPirepDaysAgo}`;
    if (airline.requirements) {
        var daysToTargetCompletion = Math.floor((Date.parse(airline.requirements.target_date) - Date.now()) / 86400000)
        var colour = 'green';
        if (daysToTargetCompletion < 7 * 8) {
          days = `<span>-${daysToTargetCompletion}`;
          colour = 'red';
        } else if (!airline.requirements.target_date && airline.requirements.details) {
          colour = 'DarkMagenta';
        }
        days = `<span style='color: ${colour};' title='${airline.requirements.details}'>${days}</span>`;
    }
    var preChecked = (id == 1131/*GBG*/) ? '' : 'checked';
    var callsignSelectors = airline.callsigns.map(callsign => `<input id='${id}-${callsign}' type='checkbox' ${preChecked} onmouseover='redraw("${id}-${callsign}", undefined);' onmouseout='redraw();' />`
        + `<label for='${id}-${callsign}'>${callsign}</label>`);
    document.getElementById("airline-picker").insertAdjacentHTML('beforeend',
        `<li onmouseout='document.getElementById("callsigns-${id}").style.display = "none";' onmouseover='document.getElementById("callsigns-${id}").style.display = "block";'>`
        + `<input type='checkbox' onmouseover='redraw("${id}-", undefined);' onmouseout='redraw();' onChange='airlineChanged(this, ${id}); redraw();' ${preChecked} id='${elementId}'>`
        + `<label for='${elementId}' title='${airline.rank_info}'>${airline.name}</label> ${days}`
        + `<span style='float:right; position: absolute; background-color: #BFBFBF; display: none; margin-left: 1em;' id='callsigns-${id}'>${callsignSelectors.join('<br/>')}</span></li>`);
    airline.cb = document.getElementById(elementId);
}

function airlineChanged(overallCheckbox, id) {
    var callsignCheckboxes = document.querySelectorAll(`[id^="${id}-"]`).forEach(callsignCheckbox => callsignCheckbox.checked = overallCheckbox.checked);
}

function excludeType(cb) {
    //TODO: https://stackoverflow.com/questions/50699948/checkbox-with-three-states for "not" on airlines or types?
    //window.alert('TODO not ' + cb.id);
    //cb.readonly = !cb.readonly;
    // Disabling it then stops the right click being seen again. :-( Perhaps we could hide it and show something else which was itself right-clickable?
    // Deselect radio? https://ux.stackexchange.com/a/140978
    return false;
}

for (const [index, icao] of Object.entries(aircraft)) {
    var flyable = icao == 'A319' || icao == 'A320' || icao == 'A321' || icao == 'A20N' || icao == 'A21N' || icao == 'A339';
    document.getElementById("aircraft-picker").insertAdjacentHTML('beforeend',
        `<li><input type='checkbox' class='wiggle' ${flyable ? 'checked ' : ''}id='type-${icao}' onmouseover='redraw(undefined, "${icao}");' onmouseout='redraw();' onChange='redraw();' oncontextmenu="return excludeType(this);">`
        + `<label for='type-${icao}' />${icao}</li>`);
}

var map = L.map('map').setView([51.55, 10.1], 4.5);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const shown = new Map();
const endpoints = new Map();

var currentIcao = undefined;

function typesToAirlineNames(route, airlineFilter, typeFilter) {
    try {
        var typeToNames = new Map();
        for (const [type, allAirlineIdsToCallsigns] of Object.entries(route.type_to_airlines)) {
            var airlineIdsToCallsigns = Object.entries(allAirlineIdsToCallsigns).filter(([id, callsigns]) => callsigns.some(callsign => airlineFilter(id, callsign)));
            if (!airlineIdsToCallsigns.length || !typeFilter(type)) continue; // Do this second to avoid excluding based on selected types for unselected airlines.
            typeToNames.set(type, airlineIdsToCallsigns.map(([id, callsigns]) => airlines[id].name + ' (' + callsigns + ')').join(', '));
        }
        return typeToNames;
    } catch (e) {
        if (e === "exclude") return new Map();
        throw e;
    }
}

function mergeEndpoint(icao, direction) {
    var existing = endpoints.get(icao);
    if (existing && existing != direction)
        direction = 'both';
    endpoints.set(icao, direction);
}

function redraw(airlineCallsignIdPrefix, icaoType) {
//for (id in airlines) { var cb = airlines[id].cb; console.log(id + " -> " + cb + " == " + cb.checked + " with ID " + cb.id); }
//console.log(`currentIcao ${currentIcao}, airline ${airlineCallsignIdPrefix}, type ${icaoType}`);
    for (polyline of shown.values()) {
        var oneWay = polyline.oneWayMarkers;
        if (oneWay) oneWay.removeFrom(map);
        polyline.removeFrom(map);
    }
    shown.clear();
    endpoints.clear();
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var lineColour = 'purple';
        var tooltip;
        var airlineFilter = (id, callsign) => document.getElementById(`${id}-${callsign}`).checked;
        var typeFilter = id => document.getElementById(`type-${id}`).checked;
        var canonicalRoute = to < from ? `${to}-${from}` : `${from}-${to}`;
        if (airlineCallsignIdPrefix) {
            airlineFilter = (id, callsign) => `${id}-${callsign}`.startsWith(airlineCallsignIdPrefix);
        } else if (icaoType) {
            byCheckbox = typeFilter;
            typeFilter = id => { if (id == icaoType) return true; if (byCheckbox(id)) throw "exclude"; return false; }
        } else if (from == currentIcao) {
            tooltip = "To " + to;
            lineColour = 'red';
        } else if (to == currentIcao) {
            tooltip = "From " + from;
            lineColour = 'blue';
        } else {
            continue;
        }
        var airlinesByType = typesToAirlineNames(routes[route], airlineFilter, typeFilter);
        if (!airlinesByType.size) continue;
        airlinesByType.forEach((names, type) => tooltip += `<br/>${type}: ${names}`);
        mergeEndpoint(to, 'to');
        mergeEndpoint(from, 'from');
        var polyline = shown.get(canonicalRoute);
        if (!polyline) {
            polyline = new L.Geodesic([airports[from].latlng, airports[to].latlng], {opacity: 0.666, color: lineColour, weight: 1.5, wrap: true});
            polyline.oneWayMarkers = L.polylineDecorator(polyline, { patterns: [ {repeat: 40, symbol: L.Symbol.arrowHead({pixelSize: 4, polygon: false, pathOptions: {stroke: true, color: lineColour}}) } ] });
            polyline.oneWayMarkers.addTo(map);
            if (tooltip) {
                tooltip = `${routes[route].distance}<br/>` + tooltip
                polyline.bindTooltip(tooltip, {sticky: true});
            }
            polyline.addTo(map);
            shown.set(canonicalRoute, polyline);
        } else {
            polyline.setStyle({color: 'purple'});
            polyline.oneWayMarkers.removeFrom(map);
            polyline.oneWayMarkers = null;
            if (tooltip)
                polyline.getTooltip().setContent(polyline.getTooltip().getContent() + '<hr/>' + tooltip);
        }
    }
    if (currentIcao) endpoints.set(currentIcao, 'selected');
    for (icao in airports) {
        var classList = airports[icao].marker.getElement().classList;
        ["to", "from", "both", "selected"].forEach(css => classList.remove(`airport-${css}`));
        if (endpoints.has(icao)) classList.add(`airport-${endpoints.get(icao)}`);
    }
}

function airportClicked(e) {
    var icao = e.target.options.icao;
    currentIcao = icao == currentIcao ? undefined : icao;
    redraw();
}

function utcTime(when) {
    return when.getUTCHours().toString().padStart(2, '0') + ":" + when.getUTCMinutes().toString().padStart(2, '0') + "Z";
}

for (icao in airports) {
    const airport = airports[icao];
    const isRoutable = airport.inbound || airport.outbound;
    const icon = L.divIcon({html: "\u2708</br>" + airport['iata'], className: 'airport', iconAnchor: [18, 15], iconSize: [36, 30]});
    var times = SunCalc.getTimes(new Date(), airport.latlng[0], airport.latlng[1]);
    airport.marker = L.marker(airport.latlng, {icao: icao, icon: icon}).addTo(map)
        .bindTooltip("<b>" + icao + "</b><br/>" + airport.names.join('<br/>') +
                     "<br/>Sunrise: " + utcTime(times.sunrise) + "<br/>Sunset: " + utcTime(times.sunset));
    if (isRoutable)
        airport.marker.on('click', airportClicked);
    else
        airports[icao].marker.getElement().classList.add('airport-unroutable')
}
