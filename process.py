import geopy.distance
import json
import logging
import operator
import regex

from datetime import date, datetime, timedelta
from glob import glob
from locale import strxfrm
from lxml import etree
from math import isnan
from unidecode import unidecode

airline_mappings = {
    'Allegiant Virtual'                :{'display_name':'Allegiant'},
    'ALVA (Aer Lingus Virtual Airline)':{'display_name':'Aer Lingus', 'sort_name':'Linugs', 'type_mapping': # Removed 'A320':'A20N', look into LatinVFR
        {'A333':'A339', '732':'B732', '733':'B733', '734':'B734', '735':'B735', '742':'B742', '752':'B752', '763':'B763', 'B72':'B720', 'L10':'L101', 'SF3':'SF34', 'SH6':'SH36'}},
    'vANA'                             :{'display_name':'All Nippon', 'sort_name':'Nippon'},
    'vBAW'                             :{'display_name':'British Airways'},
    'Air Canada Virtual'               :{'display_name':'Air Canada', 'sort_name':'Canada', 'type_mapping':{'A21N':'A321', 'A330':'A333', 'A350':'A359'}},
    'Virtual Air China'                :{'display_name':'Air China', 'sort_name':'China'},
    'Dan Air Virtual'                  :{'display_name':'Dan Air', 'type_mapping':{'A333':'A339'}}, # Removed {'A320':'A20N'}, look into LatinVFR
    'Delta Virtual'                    :{'display_name':'Delta', 'type_mapping':{'A32N':'A20N', 'A333':'A339', 'A221':'BCS1', 'A223':'BCS3', 'A313':'A310'}}, # Mappings questionable...
    'VEZY'                             :{'display_name':'EasyJet'},
    'vEWG'                             :{'display_name':'Eurowings'},
    'Frontier Airlines'                :{'display_name':'Frontier'},
    'AirGoldberg'                      :{'display_name':'Air Goldberg', 'sort_name':'Goldberg'},
    'Air India Virtual'                :{'display_name':'Air India', 'sort_name':'India'},
    'IndiGo Virtual'                   :{'display_name':'IndiGo'},
    'vJBU'                             :{'display_name':'JetBlue'}, # Removed {'A320':'A20N'}, look into LatinVFR
    'LH-Virtual'                       :{'display_name':'Lufthansa', 'type_mapping':{'A21F':'A321'}},
    'vRYR'                             :{'display_name':'Ryanair'},
    'vSAS'                             :{'display_name':'SAS', 'type_mapping':{'A333':'A339'}},
    'vspirit'                          :{'display_name':'Spirit', 'type_mapping':{'A319':'-', 'A320':'-', 'A321':'-', 'A21N':'-'}},
    'vTCXgroup'                        :{'sort_name':'Thomas Cook', 'type_mapping':{'A321':'A21N'}},
    'Titan Virtual'                    :{'display_name':'Titan'},
    'Virtual United'                   :{'display_name':'United', 'type_mapping':{'A20N':'A320'}},
    'WZZ Virtual'                      :{'display_name':'Wizz'},
}
exclude_types = set(['AJ27', 'B703', 'B712', 'B720', 'B721', 'B722',
                     'B461', 'B462', 'B463',
                     'B732', 'B733', 'B734', 'B735', 'B736', 'B737', 'B738', 'B739', 'B37M', 'B38M', 'B39M',
                     'B742', 'B744', 'B762',  'B772', 'B773', 'B77L', 'B77W', 'B77F',
                     'B752', 'B753', 'B763', 'B764',
                     'B788', 'B789', 'B78X',
                     'CONC', 'CRJ2', 'CRJ5', 'CRJ7', 'CRJ9', 'CRJX', 'DC4', 'DC6', 'DC7', 'DC10', 'DH8D',
                     'E75S', 'E145', 'E170', 'E175', 'E190', 'E195',
                     'F28', 'F50', 'JU52', 'L101', 'MD11', 'MD80', 'MD82', 'PC12',
                     'RJ1H', 'RJ85', 'SH36', 'SF34', 'SW4', 'TBM8',
                     '-'])

aircraft = set()
airlines = {}
airports = {}
routes = {}

def hours_or_points(s):
    s = s.replace(' ', '').replace(',', '')
    def parse_hours(match):
        hours, minutes, seconds = (match.group(1), match.group(2), match.group(3))
        return str(float(hours) + ((float(minutes) + float(seconds) / 60.0) / 60.0))
    return float(regex.sub(r'(\d+):(\d\d):(\d\d)', parse_hours, s))

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
            raise ValueError(f"Failed to determine whether points target include bonus points for {html}; target {next_points_target} P/BP {achieved['Points']}/{achieved['Bonus Points']} to earn {points_to_earn}")
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
    name = " ".join(airport['name'].split())
    iata = airport['iata']
    if not iata:
        iata = {'EGHL':'QLA', 'LROV':'GHV', 'MUOC':'MUOC', 'VIKA':'KNU', 'VOBG':'VOBG'}.get(icao, None)
    if icao in airports:
        airports[icao]['names'].add(name)
        latlng = [latitude, longitude]
        if airports[icao]['latlng'] != latlng:
            diff = geopy.distance.distance(airports[icao]['latlng'], latlng).nautical
            msg = f"Mismatch in location for {icao}; {airports[icao]['latlng']} against {latlng}, difference of {diff:.3f}"
            if diff >= 0.8:
                raise ValueError(msg)
            elif diff >= 0.025:
                # Consider using logging and suppressing duplicates a la https://stackoverflow.com/questions/44691558/suppress-multiple-messages-with-same-content-in-python-logging-module-aka-log-co
                print(msg)
        if airports[icao]['iata'] != iata:
            raise ValueError(f"{iaco} has inconsistent IATA codes, {airports[icao]['iata']} versus {iata}")
    else:
        airports[icao] = {'latlng': [latitude, longitude], 'iata': iata, 'names': {name}, 'inbound': False, 'outbound': False}

def add_or_update_route(origin, destination, distance, airline, type, callsigns):
    key = f"{origin}-{destination}"
    route = routes.setdefault(key, {'distance': distance, 'type_to_airlines': {}})
    type_to_airlines = route['type_to_airlines'].setdefault(type, {})
    type_to_airlines[airline] = ','.join(sorted(callsigns.split(',')))
    airports[origin]['outbound'] = airports[destination]['inbound'] = True

def time_mode(last_pirep):
    def pause_time(last_pirep, after, before):
        def just_timestamps(events, after, before):
            def transform(item):
                return datetime.fromisoformat(item['timestamp'])
            return [item for item in map(transform, events) if after <= item <= before]
        pauses = just_timestamps(last_pirep['pirep_data'].get('pauses', []), after, before)
        unpauses = just_timestamps(last_pirep['pirep_data'].get('unpauses', []), after, before)
        if len(pauses) != len(unpauses):
            raise ValueError(f"Between {after} and {before}, number of pauses {pauses} inconsistent with unpauses {unpauses}")
        return sum(map(operator.sub, unpauses, pauses), start=timedelta()).total_seconds()

    departure_time = datetime.fromisoformat(last_pirep['departure_time'])
    landing_time = datetime.fromisoformat(last_pirep['landing_time'])
    air_time = (landing_time - departure_time).total_seconds()
    off_blocks_time = datetime.fromisoformat(last_pirep['off_blocks_time'])
    on_blocks_time = datetime.fromisoformat(last_pirep['on_blocks_time'])
    block_time = (on_blocks_time - off_blocks_time).total_seconds()

    off_blocks_time -= timedelta(seconds = 1)
    on_blocks_time += timedelta(seconds = 1)
    block_paused = pause_time(last_pirep, off_blocks_time, on_blocks_time)
    air_paused = pause_time(last_pirep, departure_time, landing_time)

    flight_length = last_pirep['flight_length']
    if abs(air_time - air_paused - flight_length) <= 2:
        return "air"
    elif abs(block_time - block_paused - flight_length) <= 2:
        return "block"
    raise ValueError(f"Couldn't match flight_length {flight_length} against air {air_time} or block {block_time} time for {last_pirep['booking']['callsign']} with pauses in block {block_paused}s/air {air_paused}s")


for file in glob('vamsys.*.json'):
    print(file)
    with open(file, 'r') as f:
        airline = json.load(f)
    airline_id = airline['airline']['id']
    airline_mapping = airline_mappings.get(airline['airline']['name'], {})
    airlines[airline_id] = {'name': airline_mapping.get('display_name', airline['airline']['name'])}
    airlines[airline_id]['sortName'] = airline_mapping.get('sort_name', airlines[airline_id]['name'])
    if airline['airline']['activity_requirements']:
        if not airline['airline']['activity_requirement_type_pireps']:
            raise ValueError(f"Activity requirements for {airline['airline']['name']} not PIREPs")
        airlines[airline_id]['requirements'] = f"{airline['airline']['activity_requirement_value']} PIREP(s) required over {airline['airline']['activity_requirement_period']} days"
        completed_pireps = [pirep for pirep in airline['pireps']['pireps'] if pirep['status'] in set(['complete', 'accepted'])]
        pirep_dates = [datetime.fromisoformat(pirep['pirep_end_time']).date() for pirep in reversed(completed_pireps[:airline['airline']['activity_requirement_value']])]
        req_dates = [f"{pirep_date + timedelta(days=airline['airline']['activity_requirement_period'])}" for pirep_date in pirep_dates]
        airlines[airline_id]['requirements'] += f"\nNext {airline['airline']['activity_requirement_value']} PIREP(s) required by {', '.join(req_dates)}"
    airlines[airline_id]['rank_info'] = rank_info(airline['ranks_html'], time_mode(airline['dashboard']['flightProgress']['lastPirep']))
    type_mapping = airline_mapping.get('type_mapping', {})
    for route in airline['map']['routes']:
        from_latlon = (route['latitude'], route['longitude'])
        for dest in route['destinations']:
            to_latlon = (dest['latitude'], dest['longitude'])
            for type in [t for t in map(lambda type: type_mapping.get(type, type), dest['types'].split(',')) if 3 <= len(t) <= 4 and not t in exclude_types]:
                aircraft.add(type)
                airport(route)
                airport(dest)
                dist = round(geopy.distance.distance(from_latlon, to_latlon).nautical)
                add_or_update_route(route['icao'], dest['icao'], f"{dist}nm", airline_id, type, dest['callsigns'])

def writeJsonJs(obj, name):
    def serialize_sets(obj):
        if isinstance(obj, set):
            return list(sorted(obj))
        return obj
    with open(f'../pages/{name}.vamsys.js', 'w') as f:
        f.write(f'const {name} = ');
        json.dump(obj, f, indent=4, default=serialize_sets, sort_keys=True)
        f.write(';');

bad_airports = {icao: airport for icao, airport in airports.items() if not airport['iata']}
if bad_airports:
    print(f"Airports without IATA codes: {', '.join(bad_airports)}")

for airport in airports.values():
    unique_names = []
    #print(f"---- {airport} ----")
    nothing_words = ['', 'airport', 'int', 'international']
    def nothing_word(word):
        return word in nothing_words
    def normalise(name, is_sorting = False):
        words = regex.split(r'[\s\p{Pd}/()]+', name.casefold())
        ordered_name = " ".join(sorted([word for word in words if is_sorting or not nothing_word(word)]))
        #print(f"\t'{name}' -> {words} -> '{ordered_name}'")
        return unidecode(ordered_name) # See https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    def sort_key(name):
        return strxfrm(f"{1000 - len(normalise(name, True)):3}{name}")
    sorted_names = sorted(airport['names'], key=sort_key)
    #print(f"sorted: {sorted_names}")
    for name in sorted_names:
        if '\\' in name:
            raise ValueError(f"'{name}' contains backslash")
        normalised_candidate = normalise(name).replace(' ', r' (?:[^ ]+ )*')
        if not any(regex.search(normalised_candidate, normalise(superstring_candidate)) for superstring_candidate in unique_names):
            unique_names.append(name)
            #print(f"\t\tAdding '{name}' regex /{normalised_candidate}/")
        #else:
            #print(f"\t\tAlready got '{name}' regex /{normalised_candidate}/")
    #print(f"unique: {unique_names}")
    airport['names'] = unique_names

writeJsonJs(sorted(aircraft), 'aircraft');
writeJsonJs(airlines, 'airlines')
writeJsonJs(airports, 'airports')
writeJsonJs(routes, 'routes')
