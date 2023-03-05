const routes = { // Add approx time, airline/callsigns, aircraft; do we need distance or should we calculate it here?
    'EGLC-EGSS': {distance: '10nm', type_to_airlines: {'A20N': ['356'], 'E192': ['35']}},
    'EGSS-EGLC': {distance: '10nm', type_to_airlines: {'A20N': ['550']}},
    'EGLC-EGMC': {distance: '11nm', type_to_airlines: {'A20N': ['64', '35']}},
    'EGMC-EGKK': {distance: '12nm', type_to_airlines: {'A339': ['356'], 'A321': ['356']}},
    'EGMC-EGSS': {distance: '13nm', type_to_airlines: {'A20N': ['35']}},
    'EGKK-CYVR': {distance: '3000nm', type_to_airlines: {'A20N': ['9', '1'], 'A320': ['1', '55']}},
};
