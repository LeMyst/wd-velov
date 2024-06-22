import copy
import json
import logging
import os
import re
import time
from pprint import pprint

import requests
from wikibaseintegrator import WikibaseIntegrator, wbi_helpers, wbi_login
from wikibaseintegrator.datatypes import ExternalID, GlobeCoordinate, Item, Quantity
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists

import config

# Import local config for user and password

json_velov = 'https://download.data.grandlyon.com/ws/grandlyon/pvo_patrimoine_voirie.pvostationvelov/all.json?maxfeatures=-1'

wbi_config['USER_AGENT'] = 'Update Vélo\'v station'

administrative_locations = {
    'Villeurbanne': 'Q582',
    'Caluire-et-Cuire': 'Q244717',
    'Vénissieux': 'Q13598',
    'Vaulx-en-Velin': 'Q13596',
    'Sainte-Foy-lès-Lyon': 'Q387460',
    'Rillieux-la-Pape': 'Q386122',
    'Saint-Didier-au-Mont-d\'Or': 'Q1617501',
    'La Mulatière': 'Q772460',
    # 'Oullins': 'Q8358',
    'Oullins': 'Q123852858',
    'Écully': 'Q273748',
    'Fontaines-sur-Saône': 'Q1617114',
    'Tassin-la-Demi-Lune': 'Q1647506',
    'Saint-Fons': 'Q828676',
    'Saint-Cyr-au-Mont-d\'Or': 'Q1615759',
    'Collonges-au-Mont-d\'Or': 'Q1469657',
    'Neuville-sur-Saône': 'Q522234',
    'Décines-Charpieu': 'Q1056120',
    'Couzon-au-Mont-d\'Or': 'Q1444999',
    'Saint-Genis-Laval': 'Q910089',
    'Albigny-sur-Saône': 'Q840195',
    'Bron': 'Q1291',
    # 'Pierre-Bénite': 'Q1617042',
    'Pierre-Bénite': 'Q123852858',
    'Saint-Priest': 'Q331083',
    'Lyon 1er Arrondissement': 'Q3337',
    'Lyon 2e Arrondissement': 'Q3344',
    'Lyon 3e Arrondissement': 'Q3348',
    'Lyon 4e Arrondissement': 'Q3351',
    'Lyon 5e Arrondissement': 'Q3354',
    'Lyon 6e Arrondissement': 'Q3358',
    'Lyon 7e Arrondissement': 'Q3360',
    'Lyon 8e Arrondissement': 'Q3363',
    'Lyon 9e Arrondissement': 'Q3366'
}

# login object
login_instance = wbi_login.Login(user=config.user, password=config.password)
# login_instance = wbi_login.OAuth2(consumer_token=config.consumer_token, consumer_secret=config.consumer_secret)


wbi = WikibaseIntegrator(login=login_instance, is_bot=True)

logging.basicConfig(level=logging.DEBUG)

base_filter = [
    Item(prop_nr='P31', value='Q484170'),  # instance of commune of France
    Item(prop_nr='P17', value='Q142'),  # country France
    ExternalID(prop_nr='P374')  # INSEE municipality code
]

if not os.path.isfile('velov.json') or time.time() - os.path.getmtime('velov.json') > 86400:
    r = requests.get(json_velov, allow_redirects=True)
    open('velov.json', 'wb').write(r.content)

if os.path.isfile('somefile.txt'):
    os.remove('somefile.txt')

print('Start parsing JSON')
with open('velov.json') as jsonfile:
    data = json.load(jsonfile)
    for station in data['values']:
        # pprint(station)

        idstation = int(station['idstation'])
        nom = re.sub(' +', ' ', station['nom'].strip())

        ft_search = wbi_helpers.fulltext_search(search='Station Vélo\'v ' + str(idstation))
        if not ft_search or len(ft_search) == 0 or 'title' not in ft_search[0]:
            wd_item = wbi.item.new()
        else:
            if idstation == 2016:  # Place Regaud
                item_id = 'Q62088312'
            elif idstation == 2023:  # Perrache / Petit
                item_id = 'Q117288534'
            elif idstation == 7052:  # Parc Blandan
                item_id = 'Q62087535'
            elif len(ft_search) == 1 and 'title' in ft_search[0]:
                item_id = ft_search[0]['title']
            else:
                with open('somefile.txt', 'a') as the_file:
                    the_file.write(str(idstation) + '\n')
                continue
            wd_item = wbi.item.get(entity_id=item_id)
            # pprint(wd_item.get_json())

        old_item = copy.deepcopy(wd_item)

        if idstation == 2023:
            nom = 'Perrache / Petit'

        # Labels
        wd_item.labels.set(language='fr', value=str(idstation) + ' - ' + nom)
        wd_item.labels.set(language='en', value='Station Vélo\'v ' + str(idstation))

        # Descriptions
        wd_item.descriptions.set(language='fr', value='station de vélopartage Vélo\'v, région lyonnaise, France')
        wd_item.descriptions.set(language='en', value='Vélo\'v bicycle-sharing station, Lyon region, France')

        # Aliases
        wd_item.aliases.set(language='en', values=nom)

        # Claims
        wd_item.claims.add(claims=Item(prop_nr='P31', value='Q61663696'))  # instance of bicycle-sharing station
        wd_item.claims.add(claims=Item(prop_nr='P361', value='Q4096'))  # part of Vélo'v
        wd_item.claims.add(claims=Item(prop_nr='P17', value='Q142'))  # country France
        wd_item.claims.add(claims=Item(prop_nr='P137', value='Q74877'))  # operator JCDecaux
        wd_item.claims.add(claims=Quantity(prop_nr='P1083', amount=station['nbbornettes']))  # maximum capacity
        wd_item.claims.add(claims=ExternalID(prop_nr='P11878', value=str(idstation)))  # Vélo'v station ID
        wd_item.claims.add(claims=GlobeCoordinate(prop_nr='P625', latitude=station['lat'], longitude=station['lon'], precision=0.0001))  # coordinate location
        if station['commune'].strip() in administrative_locations:
            wd_item.claims.add(claims=Item(prop_nr='P131', value=administrative_locations[station['commune'].strip()]), action_if_exists=ActionIfExists.KEEP)  # located in the administrative territorial entity
        else:
            raise ValueError('Commune not found: ' + station['commune'])

        # pprint(wd_item.get_json())

        if wd_item.get_json() != old_item.get_json():
            # from jsondiff import diff
            # pprint(diff(wd_item.get_json(), old_item.get_json()))
            # pprint(diff(old_item.get_json(), wd_item.get_json()))
            pprint(wd_item.get_json())
            print('Update item ' + wd_item.id)
            wd_item.write(summary='Update station information')
            # exit(0)
