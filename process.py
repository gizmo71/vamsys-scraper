import csv
import geopy.distance
import json

with open('vamsys.json', 'r') as f:
    all_data = json.load(f)

types_by_airline = {
    'Dan Air Virtual': {'A20N', 'A320', 'A333'},
    'vTCXgroup': {'A320', 'A339'}
}

with open('routes.csv', 'w', newline='') as f:
    csvwriter = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
    csvwriter.writerow(['From', 'Departure', 'To', 'Destination', 'NM', 'Time', 'Type', 'Carrier'])
    for airline in all_data:
        types = types_by_airline.get(airline['airline']['name'], ['A20N', 'A339'])
        for route in airline['map']['routes']:
            from_latlon = (route['latitude'], route['longitude'])
            for dest in route['destinations']:
                to_latlon = (dest['latitude'], dest['longitude'])
                for type in [t for t in dest['types'].split(',') if t in types]:
                    dist = round(geopy.distance.distance(from_latlon, to_latlon).nautical)
                    csvwriter.writerow([route['icao'], route['name'], dest['icao'], dest['name'], dist, dest['time'], type, airline['airline']['name']])
