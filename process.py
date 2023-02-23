import geopy.distance
import json

with open('vamsys.json', 'r') as f:
    all_data = json.load(f)

types_by_airline = {
    'Dan Air Virtual': {'A20N', 'A320', 'A333'},
    'vTCXgroup': {'A320', 'A339'}
}

airports = {}
routes = {}

def airport(airport):
    icao = airport['icao']
    latitude = float(airport['latitude'])
    longitude = float(airport['longitude'])
    name = airport['name']
    if icao in airports:
        airports[icao]['names'].add(name)
        if airports[icao]['latlng'] != [latitude, longitude]:
            raise ValueError(f"Mismatch in location for {icao}")
    else:
        airports[icao] = {'latlng': [latitude, longitude], 'iata': airport['iata'], 'names': {name}}

def add_or_update_route(origin, destination, distance, airline, type):
    key = f"{origin}-{destination}"
    route = routes.setdefault(key, {'distance': distance, 'type_to_airlines': {}})
    airlines = route['type_to_airlines'].setdefault(type, set())
    airlines.add(airline)

flyable_types = ['A20N', 'A339']
for airline in all_data:
    airline_name = airline['airline']['name']
    types = types_by_airline.get(airline_name, flyable_types)
    for route in airline['map']['routes']:
        airport(route)
        from_latlon = (route['latitude'], route['longitude'])
        for dest in route['destinations']:
            airport(dest)
            to_latlon = (dest['latitude'], dest['longitude'])
            for type in [t for t in dest['types'].split(',') if t in types]:
                dist = round(geopy.distance.distance(from_latlon, to_latlon).nautical)
                add_or_update_route(route['icao'], dest['icao'], f"{dist}nm", airline_name, type)

def writeJsonJs(obj, name):
    def serialize_sets(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj
    with open(f'{name}.vamsys.js', 'w') as f:
        f.write(f'const {name} = ');
        json.dump(obj, f, indent=4, default=serialize_sets)
        f.write(';');

writeJsonJs(airports, 'airports')
writeJsonJs(routes, 'routes')
