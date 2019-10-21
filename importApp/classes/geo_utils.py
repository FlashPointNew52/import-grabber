import json, requests, traceback
import importApp.classes.proxy as proxy

def get_coords_by_addr(address):
    latitude = 0
    longitude = 0

    if address:
        add = address.strip(',').strip()

        try:
            request = requests.get('https://geocode-maps.yandex.ru/1.x/?format=json&geocode=' + add + "&apikey=2902fd2b-044e-4aad-b52a-911b742bcabf")
            if request and request.status_code == requests.codes.ok:
                json_acceptable_string = request.text.replace("'", "\"")
                res = json.loads(json_acceptable_string)

                if res and int(res['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found']) > 0:
                    pos = res['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos'].split()
                    latitude = pos[1]
                    longitude = pos[0]
        except:
            print(traceback.format_exc())

    return {'latitude': latitude, 'longitude': longitude}

# Получение района
def get_district_by_coords(latitude, longitude):
    data = {
        'district': None,
        'subdistrict': None,
        'metro': None
    }

    if latitude and longitude:
        try:
            request = requests.get('https://geocode-maps.yandex.ru/1.x/?format=json&apikey=2902fd2b-044e-4aad-b52a-911b742bcabf&geocode=' + longitude + ', ' + latitude)
            if request and request.status_code == requests.codes.ok:
                json_acceptable_string = request.text.replace("'", "\"")
                res = json.loads(json_acceptable_string)

                if res and int(res['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found']) > 0:
                    featureMember = res['response']['GeoObjectCollection']['featureMember']
                    districts = []
                    for memb in featureMember:
                        if memb['GeoObject']['metaDataProperty']['GeocoderMetaData']['kind'] == 'district':
                            districts.append(memb['GeoObject']['name'])
                        if memb['GeoObject']['metaDataProperty']['GeocoderMetaData']['kind'] == 'metro':
                            data['metro'] = memb['GeoObject']['name']
                    if len(districts) > 1:
                        data['district'] = districts[1]
                        data['subdistrict'] = districts[0]
                    else:
                        data['district'] = districts[0]
        except:
            None

    return data