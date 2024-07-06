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
        }
        days = `<span style='color: ${colour};' title='${airline.requirements.details}'>${days}</span>`;
    }
    var callsignSelectors = airline.callsigns.map(callsign => `<input id='${id}-${callsign}' type='checkbox' checked onmouseover='redraw("${id}-${callsign}", undefined);' onmouseout='redraw();' />`
        + `<label for='${id}-${callsign}'>${callsign}</label>`);
    document.getElementById("airline-picker").insertAdjacentHTML('beforeend',
        `<li onmouseout='document.getElementById("callsigns-${id}").style.display = "none";' onmouseover='document.getElementById("callsigns-${id}").style.display = "block";'>`
        + `<input type='checkbox' onmouseover='redraw("${id}-", undefined);' onmouseout='redraw();' onChange='airlineChanged(this, ${id}); redraw();' checked id='${elementId}'>`
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
    var flyable = icao == 'A319' || icao == 'A320' || icao == 'A20N' || icao == 'A21N' || icao == 'A339';
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
var isInbound = false;

const airportNeutral = "\u2708";
const airportDepart = "\ud83d\udeeb"; // 1F6EB as a surrogate pair
const airportArrive = "\ud83d\udeec"; // 1F6EC

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
//console.log(`currentIcao ${currentIcao} in? ${isInbound}, airline ${airlineCallsignIdPrefix}, type ${icaoType}`);
    if (currentIcao)
        document.getElementById("airport-" + currentIcao).innerText = isInbound ? airportArrive : airportDepart;
    for (polyline of shown.values()) polyline.removeFrom(map);
    shown.clear();
    endpoints.clear();
    for (route in routes) {
        const from = route.substring(0, 4);
        const to = route.substring(5, 9);
        var tooltip;
        var airlineFilter = (id, callsign) => document.getElementById(`${id}-${callsign}`).checked;
        var typeFilter = id => document.getElementById(`type-${id}`).checked;
        if (airlineCallsignIdPrefix) {
            airlineFilter = (id, callsign) => `${id}-${callsign}`.startsWith(airlineCallsignIdPrefix);
        } else if (icaoType) {
            byCheckbox = typeFilter;
            typeFilter = id => { if (id == icaoType) return true; if (byCheckbox(id)) throw "exclude"; return false; }
        } else if (from == currentIcao && !isInbound) {
            tooltip = "To " + to;
        } else if (to == currentIcao && isInbound) {
            tooltip = "From " + from;
        } else {
            continue;
        }
        var airlinesByType = typesToAirlineNames(routes[route], airlineFilter, typeFilter);
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
    const icon = L.divIcon({html: "<span id='airport-" + icao + "'>" + airportNeutral + "</span></br>" + airport['iata'], className: 'airport', iconAnchor: [18, 15], iconSize: [36, 30]});
    airport.marker = L.marker(airport.latlng, {icao: icao, icon: icon}).addTo(map)
        .bindTooltip("<b>" + icao + "</b><br/>" + airport.names.join('<br/>'))
        .on('click', airportClicked);
}
