const routes = { // Add approx time, airline/callsigns, aircraft; do we need distance or should we calculate it here?
    'EGLC-EGSS': {distance: '10nm', type_to_airlines: {'A20N': ['Dan Air Virtual'], 'E192': ['vBAW']}},
    'EGSS-EGLC': {distance: '10nm', type_to_airlines: {'A20N': ['vSAS']}},
    'EGLC-EGMC': {distance: '11nm', type_to_airlines: {'A20N': ['JetBlue', 'vBAW']}},
    'EGMC-EGKK': {distance: '12nm', type_to_airlines: {'A339': ['Dan Air Virtual'], 'A321': ['Dan Air Virtual']}},
    'EGMC-EGSS': {distance: '13nm', type_to_airlines: {'A20N': ['vBAW']}},
    'EGKK-CYVR': {distance: '3000nm', type_to_airlines: {'A20N': ['vEWG', 'vEZY'], 'A320': ['vEZY', 'vSpirit']}},
};
