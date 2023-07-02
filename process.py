import geopy.distance
import json
import re

from math import isnan
from datetime import date, datetime, timedelta
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
    s = s.replace(' ', '').replace(',', '')
    def parse_hours(match):
        hours, minutes, seconds = (match.group(1), match.group(2), match.group(3))
        return str(float(hours) + ((float(minutes) + float(seconds) / 60.0) / 60.0))
    return float(re.sub(r'(\d+):(\d\d):(\d\d)', parse_hours, s))

rank_criteria = {"Hours": 3, "Points": 4, "Bonus Points": 5}

def rank_info(html, time_mode):
    div = etree.HTML(html)
    current_div = div.xpath("//div[@class = 'row stats']")[0]
    achieved = {}
    for criteria_name in rank_criteria.keys():
        achieved[criteria_name] = hours_or_points(current_div.xpath("normalize-space(./div[h6 = $criteria_name]/h3)", criteria_name = criteria_name))
    need = ''
    next_rank = div.xpath("normalize-space(//div[normalize-space(div) = 'Next Rank:']/div[2])")
    points_to_earn = div.xpath("number(//div[normalize-space(div) = 'Points to earn:']/div[2])")
    if not isnan(points_to_earn) and achieved['Bonus Points']:
        next_points_target = hours_or_points(div.xpath("normalize-space(//tr[td[2] = $next_rank]/td[4])", next_rank = next_rank))
        if next_points_target == achieved['Points'] + achieved['Bonus Points'] + points_to_earn:
            achieved['Points'] += achieved['Bonus Points']
            need += "Bonus points count towards normal points total\n"
        elif next_points_target == achieved['Points'] + points_to_earn:
            need += "Bonus points not included in normal points total\n"
        else:
            raise ValueError(f"Failed to determine whether points target include bonus points for {html}")
    pireps = div.xpath("number(normalize-space(//div[h6/text() = 'PIREPs Filed']/h3))")
    for rank in div.xpath("//table[thead/tr/th[text() = 'Epaulette']]/tbody/tr[td[3]/text() != 'By Appointment Only']"):
        title = rank.xpath("string(./td[2])")
        target = {}
        for criteria_name, cell_index in rank_criteria.items():
            rank_in = hours_or_points(rank.xpath("normalize-space(./td[$cell_index])", cell_index = cell_index)) - achieved[criteria_name]
            if rank_in > 0:
                target[criteria_name] = rank_in
        if target:
            need += f"{title}:"
            for criteria_name in target.keys():
                rank_in = target[criteria_name]
                need += f"\n\t+{round(rank_in, 1)} {criteria_name}"
                if achieved[criteria_name]:
                    avg_pireps = round(rank_in / (achieved[criteria_name] / pireps), 1)
                    need += f" ({avg_pireps} PIREPs)"
            need += "\n"
    return f"{need}Time mode: {time_mode}"

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

def time_mode(last_pirep):
    air_time = (datetime.fromisoformat(last_pirep['landing_time']) - datetime.fromisoformat(last_pirep['departure_time'])).total_seconds()
    block_time = (datetime.fromisoformat(last_pirep['on_blocks_time']) - datetime.fromisoformat(last_pirep['off_blocks_time'])).total_seconds()
    flight_length = last_pirep['flight_length']
    if abs(air_time - flight_length) <= 2:
        return "air"
    elif abs(block_time - flight_length) <= 2:
        return "block"
    raise ValueError(f"Couldn't match flight_length {flight_length} against air {air_time} or block {block_time} time for {last_pirep['booking']['callsign']}")

flyable_types = ['A20N', 'A339']
for airline in all_data:
    airline_id = airline['airline']['id']
    airlines[airline_id] = {'name': map_airline_name(airline['airline']['name'])}
    if airline['airline']['activity_requirements']:
        if not airline['airline']['activity_requirement_type_pireps']:
            raise ValueError(f"Activity requirements for {airline['airline']['name']} not PIREPs")
        if airline['airline']['activity_requirement_value'] != 1:
            raise ValueError(f"{airline['airline']['name']} requires multiple PIREPs in the period")
        last_pirep_datetime = datetime.fromisoformat(airline['dashboard']['flightProgress']['lastPirep']['pirep_end_time'])
        pirep_by = last_pirep_datetime.date() + timedelta(days=airline['airline']['activity_requirement_period'])
        airlines[airline_id]['requirements'] = f"Next PIREP required by {pirep_by}"
    airlines[airline_id]['rank_info'] = rank_info(airline['ranks_html'], time_mode(airline['dashboard']['flightProgress']['lastPirep']))
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
