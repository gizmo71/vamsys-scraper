import geopy.distance
import json
import re

from datetime import date, timedelta
from lxml import etree

with open('vamsys.json', 'r') as f:
    all_data = json.load(f)

type_mapping_by_airline = {
    'ALVA': {'A333':'A339'},
    'Dan Air Virtual': {'A320':'A20N', 'A333':'A339'},
    'vSAS': {'A333':'A339'},
    'vTCXgroup': {'A320':'A20N'}
}

airlines = {}
airports = {}
routes = {}

def hours_or_points(s):
    def parse_hours(match):
        hours, minutes, seconds = (match.group(1), match.group(2), match.group(3))
        return str(float(hours) + (float(minutes) / 60.0 + (float(seconds) / 60.0)))
    return float(re.sub(r'(\d+):(\d\d):(\d\d)', parse_hours, s))

def requirement(div):
    next_in = re.sub('^Next Rank In:? ', '', div.xpath('normalize-space(./h3/@data-original-title)'))
    next_in = re.sub(' pts$', '', next_in)
    next_in = hours_or_points(next_in)
    current = hours_or_points(div.xpath('normalize-space(./h3/text())').replace(' ', ''))
    units = div.xpath('normalize-space(./h6/text())')
    return (next_in, units, current)

def rank_info(html):
    div = etree.HTML(html)
    pireps = div.xpath("number(normalize-space(//div[h6/text() = 'PIREPs Filed']/h3/text()))")
    need = 'Need:'
    for req in div.xpath("//div[./h3[starts-with(@data-original-title, 'Next Rank In') and not(contains(@data-original-title, 'Requirement met'))]]"):
        next_in, units, current = requirement(req)
        need = f"{need}\n{round(next_in, 2)} {units} (~ {round(next_in / (current / pireps), 1)} PIREPs)"
    return need

def airport(airport):
    icao = airport['icao']
    latitude = float(airport['latitude'])
    longitude = float(airport['longitude'])
    name = airport['name']
    if icao in airports:
        airports[icao]['names'].add(name)
        latlng = [latitude, longitude]
        if airports[icao]['latlng'] != latlng:
            diff = geopy.distance.distance(airports[icao]['latlng'], latlng).nautical
            msg = f"Mismatch in location for {icao}; {airports[icao]['latlng']} against {latlng}, difference of {diff:.3f}"
            if diff >= 0.8:
                raise ValueError(msg)
            elif diff >= 0.01:
                print(msg)
    else:
        airports[icao] = {'latlng': [latitude, longitude], 'iata': airport['iata'], 'names': {name}, 'inbound': 0, 'outbound': 0}

def add_or_update_route(origin, destination, distance, airline, type):
    key = f"{origin}-{destination}"
    route = routes.setdefault(key, {'distance': distance, 'type_to_airlines': {}})
    type_to_airlines = route['type_to_airlines'].setdefault(type, set())
    type_to_airlines.add(airline)
    airports[origin]['outbound'] += 1
    airports[destination]['inbound'] += 1

def map_airline_name(vamsys_name):
    if vamsys_name.startswith("ALVA "):
        return "ALVA"
    return vamsys_name

flyable_types = ['A20N', 'A339']
for airline in all_data:
    airline_id = airline['airline']['id']
    airlines[airline_id] = {'name': map_airline_name(airline['airline']['name'])}
    if airline['airline']['activity_requirements']:
        if not airline['airline']['activity_requirement_type_pireps']:
            raise ValueError(f"Activity requirements for {airline['airline']['name']} not PIREPs")
        if airline['airline']['activity_requirement_value'] != 1:
            raise ValueError(f"{airline['airline']['name']} requires multiple PIREPs in the period")
        pirep_by = date.fromisoformat(airline['last_pirep_date']) + timedelta(days=airline['airline']['activity_requirement_period'])
        airlines[airline_id]['requirements'] = f"Next PIREP required by {pirep_by}"
    airlines[airline_id]['rank_info'] = rank_info(airline['rank_html'])
    type_mapping = type_mapping_by_airline.get(airlines[airline_id]['name'], {})
    for route in airline['map']['routes']:
        from_latlon = (route['latitude'], route['longitude'])
        for dest in route['destinations']:
            to_latlon = (dest['latitude'], dest['longitude'])
            for type in [t for t in map(lambda type: type_mapping.get(type, type), dest['types'].split(',')) if t in flyable_types]:
                airport(route)
                airport(dest)
                dist = round(geopy.distance.distance(from_latlon, to_latlon).nautical)
                add_or_update_route(route['icao'], dest['icao'], f"{dist}nm", airline_id, type)

def writeJsonJs(obj, name):
    def serialize_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj
    with open(f'{name}.vamsys.js', 'w') as f:
        f.write(f'const {name} = ');
        json.dump(obj, f, indent=4, default=serialize_sets)
        f.write(';');

writeJsonJs(airlines, 'airlines')
writeJsonJs(airports, 'airports')
writeJsonJs(routes, 'routes')
