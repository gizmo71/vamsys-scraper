import csv
import json

with open('vamsys.json', 'r') as f:
    all_data = json.load(f)

types_by_airline = {
    'Dan Air Virtual': {'A20N', 'A320', 'A333'},
    'vTCXgroup': {'A320', 'A339'}
}

with open('routes.csv', 'w') as f:
    f.write("From,Departure,To,Destination,Type,Carrier\n")
    for airline in all_data:
        types = types_by_airline.get(airline['airline']['name'], ['A20N', 'A339'])
        for route in airline['map']['routes']:
            for dest in route['destinations']:
                for type in [t for t in dest['types'].split(',') if t in types]:
                    f.write(f"{route['icao']},{route['name']},{dest['icao']},{dest['name']},{type},{airline['airline']['name']}\n")
