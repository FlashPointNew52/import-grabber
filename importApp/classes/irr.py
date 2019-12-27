import requests, re, time, geohash, json  # пакет для работы с http (запросы и т.п.)
import importApp.classes.offers_struct as off_str
import importApp.classes.proxy as proxy
import importApp.classes.geo_utils as geo_utils
from certifi import where
from pybase64 import b64decode
from datetime import timedelta
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from datetime import datetime
from requests.exceptions import ProxyError, ConnectionError, Timeout

es = Elasticsearch()

class IrrParser:

    def parseList(self, params):
        i = 1
        urllist = []
        while i <= int(params['pages']):
            html_code = None
            if i == 1:
                html_code = self.__get_html(params['link'])
            else:
                html_code = self.__get_html(params['link']+'/page'+str(i))
            data_table = BeautifulSoup(html_code, 'lxml').find_all('div', {"class": 'js-productBlock'})
            for data in data_table:
                id = data['data-item-id']
                link = data.find('a', {"class": 'listing__itemTitle'})['href']
                data_str = data.find('span', {"class": 'listing__itemDate'}).text
                date = self.parse_data(data_str.lower())
                url = {
                    'url': link,
                    'id': id,
                    'date': date,
                }
                urllist.append(url)
            i = i + 1
            time.sleep(int(params['pause']))

        for url in urllist:
            eid = url['id'] + "_" + url['date'].strftime('%Y%m%d')
            has_index = es.indices.exists(index='urls_history')
            results = None
            if has_index:
                results = es.search(index='urls_history',
                                body={"query": {"bool": {"must": [{"match": {"media": params['media']}}, {"match": {"eid": eid}}]}}},
                                filter_path=['hits.total.value'])
            if has_index is False or results['hits']['total']['value'] == 0:
                es.index('urls_history', {"media": params['media'], "eid": eid, "data": url['url']})
                es.index('resource_urls', {"media": params['media'], "link": url['url'], 'pause': params['pause'], 'city': params['city']})
                es.reindex
            else:
                print("already add: " + eid)


    def parse_data(self, data_str):
        dt_now = datetime.today()
        year = dt_now.year
        mon = dt_now.month
        mday = dt_now.day
        result = re.findall(r'сегодня,\s(\d{1,2}):(\d{1,2})', data_str)
        if len(result) != 0:
            res = datetime(year, mon, mday, int(result[0][0]), int(result[0][1]));
            return res

        result = re.findall(r'вчера\s(\d{1,2}):(\d{1,2})', data_str)
        if len(result) != 0:
            res = datetime(year, mon, mday - 1, int(result[0][0]), int(result[0][1]));
            return res

        result = re.findall(r'(\d+)\s(\w+)', data_str)
        if len(result) != 0:
            month = self.month_num(result[0][1].lower())
            res = datetime(year, month, int(result[0][0]), 0, 5)
            return res

    def month_num(self, month_str):
        if month_str.find('янв') > -1:
            return 1
        if month_str.find('фев') > -1:
            return 2
        if month_str.find('март') > -1:
            return 3
        if month_str.find('апр') > -1:
            return 4
        if month_str.find('мая') > -1:
            return 5
        if month_str.find('июн') > -1:
            return 6
        if month_str.find('июл') > -1:
            return 7
        if month_str.find('авг') > -1:
            return 8
        if month_str.find('сен') > -1:
            return 9
        if month_str.find('окт') > -1:
            return 10
        if month_str.find('ноя') > -1:
            return 11
        if month_str.find('дек') > -1:
            return 12
        else:
            return 0

    def __get_html(self, url):

        attempt = 1  # счетчик попыток
        delay_sec = 0.01  # время задержки (в секундах)
        while attempt <= 10:
            try:
                prox = proxy.set_proxy()
                self.req = requests.get(url, proxies=prox, timeout=(3, 5), headers=proxy.get_headers("irr"), verify=where(),)
                if self.req.status_code == requests.codes.ok:
                    return self.req.text
                else:
                    attempt += 1
            except (ProxyError, ConnectionError, Timeout):
                # attempt += 1
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        url = parameters['link']
        html_code = self.__get_html(url)  # вызов функции get_html(функция для получения html кода) с параметром в виде url-адреса

        global data
        data = {
            'importId': int(time.time() * 100000),
            'sourceMedia': 'irr',
            'Url4Search': "\"" + parameters['link'] + "\"",
            'sourceUrl': parameters['link'],
            'addDate': None,
            'offerTypeCode': None,
            'typeCode': None,
            'categoryCode': None,
            'phoneBlock': None,
            'buildingType': None,
            'buildingClass': None,
            'newBuilding': None,
            'mortgages': False,
            'description': ''
        }

        global soup
        global breadcrumbs
        global info

        soup = BeautifulSoup(html_code, 'lxml').find('body')
        breadcrumbs = []
        tag_breadcrumbs = soup.find_all('li', {'itemprop': 'itemListElement'})
        if tag_breadcrumbs:
            for item in tag_breadcrumbs:
                item = item.find('span', itemprop='name')
                breadcrumbs.append(item.text.strip().lower())
        else:
            exit()

        info = self.__get_info()
        # Обязательные поля
        data['addDate'] = self.__get_date()
        self.__get_offer_type_code()
        self.__get_locality()
        data['categoryCode'] = self.__get_category_code()
        data['typeCode'] = self.__get_type_code()
        data['phoneBlock'] = self.__get_phones()
        data['addressBlock'] = self.__get_address()
        addr_str = ""
        for value in data['addressBlock'].values():
            if value:
                addr_str = addr_str + ", " + value

        coords = geo_utils.get_coords_by_addr(addr_str)

        data["location"] = {"lat": coords['latitude'],"lon": coords['longitude']}
        data["location_hash"] = geohash.encode(float(coords['latitude']), float(coords['longitude']))

        dop_address = geo_utils.get_district_by_coords(coords['latitude'], coords['longitude'])

        if dop_address:
            try:
                data['addressBlock']['admArea'] = dop_address['district']
                data['addressBlock']['area'] = dop_address['subdistrict']
                data['addressBlock']['station'] = dop_address['metro']
            except:
                None
        # Обязательные поля, но возможны значения по умолчанию
        data['buildingClass'] = self.__get_building_class()
        data['buildingType'] = self.__get_building_type()
        self.__get_type_novelty()

        # # Прочие поля
        self.__get_price()
        self.__get_mediator_company()
        self.__get_photo_url()
        self.__get_balcony()
        self.__get_description()
        self.__get_rooms_count()
        self.__get_floor()
        self.__get_square()
        self.__get_build_year()
        self.__get_bathroom()
        self.__get_condition()
        self.__get_house_type()

        if data['offerTypeCode'] == 'rent' \
                and data['categoryCode'] == 'rezidential':
            data['conditions'] = self.__get_rent_fields()

        return data

    def __get_id(self):
        now_date = datetime.today()
        date_create = datetime(now_date.year, now_date.month, now_date.day,
                               now_date.hour,
                               now_date.minute, now_date.second, now_date.microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_info(self):
        tag_information = soup.find_all('li', {'class': 'productPage__infoColumnBlockText'})
        if tag_information:
            information = {}
            for item in tag_information:
                item = item.text
                try:
                    key, value = item.split(':')
                    value = value.replace('м2', '').strip()
                except ValueError:
                    key = item.strip().lower()
                    value = True

                key = key.strip().lower()
                information[key] = value

            return information

    def __get_date(self):
        tag_date = soup.find('div', {'class': 'createDate'})
        if tag_date:
            now_date = datetime.now()
            date_time = {
                'day': None,
                'month': None,
                'year': now_date.year,
                'hour': now_date.hour,
                'minute': now_date.minute,
                'second': now_date.second,
            }

            raw_date = tag_date.find('span')
            raw_date = raw_date.text.replace(',', '')
            raw_date = raw_date.split()
            if len(raw_date) == 3:
                day, month, year = raw_date
                date_time['day'] = day
                date_time['month'] = off_str.get_month(month)
                date_time['year'] = year

            elif len(raw_date) == 2:
                day_type, month = raw_date

                if day_type == 'сегодня':
                    time_today = month
                    hour, minute = time_today.split(':')
                    date_time['day'] = now_date.day
                    date_time['month'] = now_date.month
                    date_time['hour'] = hour
                    date_time['minute'] = minute

                else:
                    day = day_type
                    date_time['day'] = day
                    date_time['month'] = off_str.get_month(month)

            date = datetime(int(date_time['year']), int(date_time['month']),
                            int(date_time['day']), int(date_time['hour']),
                            int(date_time['minute']))

            msc_date = date - timedelta(hours=7)
            unix_date = int(time.mktime(msc_date.timetuple()))

            data['changeDate'] = unix_date

            return unix_date

    def __get_address(self):
        address = ''
        tag_address = soup.find('div', {'class': 'productPage__infoTextBold js-scrollToMap'})
        addressBlock = {
            'region': None,
            'city': None,
            'admArea': None,
            'area': None,
            'street': None,
            'building': None,
            'apartment': None,
            'station': None,
            'busStop': None
        }
        if tag_address:
            raw_address = tag_address.text.replace('\n', '').replace('\t', '').strip()
            raw_address = raw_address.split(',')
            if len(raw_address) == 2:
                addressBlock["city"], addressBlock["street"] = raw_address
                addressBlock["street"] = addressBlock["street"].title()
                address += addressBlock["street"]

            elif len(raw_address) == 3:
                addressBlock["city"], addressBlock["street"], addressBlock["building"] = raw_address
                address += addressBlock["street"] + ',' + addressBlock["building"]
        else:
            if 'улица' in info:
                addressBlock["street"] = 'ул.' + info['улица'].replace('ул', '').title()
                address += 'ул.' + info['улица'].replace('ул', '').title()
            if 'дом' in info:
                addressBlock["building"] = info['дом']
                address += info['дом']

        data['description'] = data['description'] + ' ' + address
        return addressBlock

    def __get_mediator_company(self):
        tag_mediator_company = soup.find('div', {'class': 'productPage__infoTextBold_inline'})
        if tag_mediator_company:
            mediator_company = tag_mediator_company.text
            if re.findall('собствен', mediator_company):
                return
            else:
                data['mediatorCompany'] = mediator_company.replace('\n', '').replace('\t', '').strip()

    def __get_offer_type_code(self):
        if re.findall('продажа', breadcrumbs[2]):
            data['offerTypeCode'] = 'sale'
        elif re.findall('аренда', breadcrumbs[2]):
            data['offerTypeCode'] = 'rent'
            data['rentType'] = 'long'
            if 'краткосрочная аренда' in info:
                data['rentType'] = 'short'

    def __get_locality(self):
        tag_city = soup.find('div', {'class': 'productPage__infoTextBold js-scrollToMap'})

        if tag_city:
            full_address = tag_city.text.strip()
            raw_city = full_address.split(',')
            city = 'г. ' + raw_city[0]

            data['locality'] = city

    def __get_category_code(self):
        if re.findall('квартир', breadcrumbs[2]) or re.findall('комнат', breadcrumbs[2]):
            return off_str.get_CC('жилая')
        elif re.findall('дома', breadcrumbs[3]) or re.findall('таунхаусы', breadcrumbs[3]):
            return off_str.get_CC('жилая')
        elif re.findall('коммерческ', breadcrumbs[2]):
            return off_str.get_CC('коммерческая')
        elif re.findall('участки', breadcrumbs[3]) or re.findall('дачи', breadcrumbs[3]):
            return off_str.get_CC('участкиидачи')

    def __get_building_class(self):
        if data['categoryCode'] == 'rezidential':
            if 'общежитие' in info:
                return off_str.get_BC('общежитие')
            else:
                return off_str.get_BC(data['typeCode'])

        elif data['categoryCode'] == 'commersial':
            if 'класс' in info:
                return off_str.get_BC(info['класс'].lower())
            else:
                return off_str.get_BC('a')

        elif data['categoryCode'] == 'land':
            return None

    def __get_building_type(self):
        return off_str.get_BT(data['typeCode'])

    def __get_type_code(self):
        if data['categoryCode'] == 'rezidential':
            if re.findall('квартир', breadcrumbs[2]):
                if re.findall('студии', breadcrumbs[2]):
                    data['roomScheme'] = 'studio'
                return off_str.get_TC('квартира')

            elif re.findall('долей', breadcrumbs[2]):
                if 'доля' in info:
                    return off_str.get_TC('доля')

                count_room_sale = 0
                all_count_room = 0
                if 'количество комнат на продажу' in info:
                    count_room_sale = int(info['количество комнат на продажу'])
                if 'всего комнат в квартире' in info:
                    all_count_room = int(info['всего комнат в квартире'])
                if all_count_room > count_room_sale:
                    return off_str.get_TC('доля')

                return off_str.get_TC('комната')

            elif re.findall('комнат', breadcrumbs[2]):
                return off_str.get_TC('комната')

            elif re.findall('дома', breadcrumbs[3]):
                return off_str.get_TC('дом')

            elif re.findall('таунхаусы', breadcrumbs[3]):
                return off_str.get_TC('таунхаус')

        elif data['categoryCode'] == 'commersial':
            if re.findall('свободного назначения', breadcrumbs[3]):
                return off_str.get_TC('другое')
            elif re.findall('офис', breadcrumbs[3]):
                if 'тип здания' in info:
                    if re.findall('офисное здание', info['тип здания']):
                        return off_str.get_TC('производственное помещение')
                    elif re.findall('бизнес', info['тип здания']):
                        return off_str.get_TC('бизнес-центр')
                    elif re.findall('офисное здание', info['тип здания']):
                        return off_str.get_TC('офисное здание')
                    else:
                        return off_str.get_TC('офисное помещение')
                else:
                    return off_str.get_TC('офисное помещение')
            elif re.findall('склады', breadcrumbs[3]):
                if 'назначение помещения' in info:
                    if re.findall('производство', info['назначение помещения']):
                        return off_str.get_TC('производственное помещение')

                    elif re.findall('склад', info['назначение помещения']):
                        return off_str.get_TC('склад')
                    else:
                        return off_str.get_TC('склад')
                else:
                    return off_str.get_TC('склад')

            elif re.findall('здания', breadcrumbs[3]):
                return off_str.get_TC('здание')

            elif re.findall('торговля', breadcrumbs[3]):
                if 'назначение помещения' in info:
                    if re.findall('бытовое', info['назначение помещения']):
                        return off_str.get_TC('магазин')

                    elif re.findall('торговое', info['назначение помещения']):
                        return off_str.get_TC('торговое помещение')

                    elif re.findall('торговый центр', info['тип здания']):
                        return off_str.get_TC('торговый центр')

                    elif re.findall('торгово-развлекательный центр', info['тип здания']):
                        return off_str.get_TC('тогово-развлекательный центр')

                    else:
                        return off_str.get_TC('магазин')
                else:
                    return off_str.get_TC('магазин')

            elif re.findall('кафе', breadcrumbs[3]):
                return off_str.get_TC('кафе')

            else:
                return off_str.get_TC('другое')

        elif data['categoryCode'] == 'land':
            if re.findall('участки', breadcrumbs[3]):
                return off_str.get_TC('участок')
            elif re.findall('дачи', breadcrumbs[3]):
                return off_str.get_TC('дачи')

    def __get_phones(self):
        phoneBlock = {
            'main': None,
            'cellphone': None,
            'office': None,
            'home': None,
            'other': None,
            'fax': None
        }
        tag_phone = soup.find('input', attrs={'name': 'phoneBase64', 'type': 'hidden'})
        if tag_phone:
            list_phones = []
            phone = b64decode(tag_phone['value'])
            phone = re.sub(r'\D', '', phone.decode("utf-8"))
            list_phones.append(phone)
            try:
                phoneBlock['main'] = list_phones[0]
                phoneBlock['cellphone'] = list_phones[1]
                phoneBlock['office'] = list_phones[2]
                phoneBlock['home'] = list_phones[3]
                phoneBlock['other'] = list_phones[4]
                phoneBlock['fax'] = list_phones[5]
            except IndexError:
                None
        return phoneBlock

    def __get_type_novelty(self):
        if data['sourceUrl']:
            url = data['sourceUrl']
            parts_url = url.split('/')
            if 'new' in parts_url:
                data['newBuilding'] = True
                if 'этап строительства' in info:
                    if re.findall('сдан', info['этап строительства']):
                        data['objectStage'] = 'ready'
                    elif re.findall('этап', info['этап строительства']):
                        data['objectStage'] = 'building'
                    else:
                        data['objectStage'] = 'ready'
                elif 'год постройки/сдачи' in info:
                    year = int(re.findall(r'\d{4}', info['год постройки/сдачи'])[0])
                    current_year = datetime.now().year
                    if year > current_year:
                        data['objectStage'] = 'building'
                    elif year <= current_year:
                        data['objectStage'] = 'ready'
                else:
                    data['objectStage'] = 'ready'
            else:
                data['newBuilding'] = False


    def __get_price(self):
        tag_price = soup.find('div', {'class': 'js-contentPrice'})
        if tag_price:
            price = float(tag_price['content']) / 1000

            data['price'] = price

    def __get_photo_url(self):
        tag_photos = soup.find('div', {'class': 'lineGallery js-lineProductGallery'})
        if tag_photos:
            tag_photos = tag_photos.find_all('img')
            photos = []
            for photo in tag_photos:
                photo = {
                    'addDate': int(time.mktime(datetime.now().timetuple())),
                    'ext': "jpg",
                    'fullName': "irr_img.jpg",
                    'href': photo['data-src'],
                    'isTemp': False,
                    'name': "irr_img",
                    'type': 0
                }
                photos.append(photo)

            data['photos'] = photos

    def __get_description(self):
        tag_description = soup.find('p', {'class': 'descriptionText'})
        if tag_description:
            description = tag_description.text.strip().replace('\n', '')
            word_list = description.split()

            description = ''
            for word in word_list:
                description += word + ' '

            data['description'] = description.strip()

    def __get_floor(self):
        if 'этаж' in info:
            data['floor'] = int(info['этаж'])
        if 'этажей в здании' in info:
            data['floorsCount'] = int(info['этажей в здании'])

    def __get_rooms_count(self):
        if 'комнат в квартире' in info:
            data['roomsCount'] = int(info['комнат в квартире'])

    def __get_house_type(self):
        if 'материал стен' in info:
            data['houseType'] = off_str.get_house_type(info['материал стен'])

    def __get_build_year(self):
        if 'год постройки' in info:
            data['buildYear'] = str(info['год постройки'])

    def __get_square(self):
        if data['categoryCode'] == 'rezidential':
            if 'общая площадь' in info:
                data['squareTotal'] = float(info['общая площадь'])
            if 'жилая площадь' in info:
                data['squareLiving'] = float(info['жилая площадь'])
            if 'площадь кухни' in info:
                data['squareKitchen'] = float(info['площадь кухни'])
            if 'площадь арендуемой комнаты' in info:
                data['squareLiving'] = float(info['площадь арендуемой комнаты'])

            if data['typeCode'] == 'share' or data['typeCode'] == 'room':
                sale_square = 0
                all_square = 0
                if 'площадь продажи' in info:
                    sale_square = float(info['площадь продажи'])
                if 'общая площадь квартиры' in info:
                    all_square = float(info['общая площадь квартиры'])

                if sale_square < all_square:
                    data['squareLiving'] = sale_square
                    data['squareTotal'] = all_square
                elif sale_square != 0:
                    data['squareLiving'] = sale_square

        elif data['categoryCode'] == 'commersial':
            if 'общая площадь' in info:
                data['squareTotal'] = float(info['общая площадь'])

        elif data['categoryCode'] == 'land':
            if 'площадь участка' in info:
                square = info['площадь участка'].split()
                data['squareLand'] = float(square[0])
                data['squareLandType'] = 'ar'
                if square[1] != 'сот':
                    data['squareLandType'] = 'ha'

            if 'площадь строения' in info:
                data['squareTotal'] = float(info['площадь строения'])

    def __get_condition(self):
        if 'ремонт' in info:
            data['condition'] = off_str.get_condition(info['ремонт'])

    def __get_balcony(self):
        if 'балкон/лоджия' in info:
            data['loggia'] = True
            data['balcony'] = True

    def __get_bathroom(self):
        if 'санузел' in info:
            data['bathroom'] = off_str.get_bathroom(info['санузел'])

    def __get_rent_fields(self):
        conditions = {
            'complete': False,
            'living_room_furniture': False,
            'kitchen_furniture': False,
            'couchette': False,
            'bedding': False,
            'dishes': False,
            'refrigerator': False,
            'washer': False,
            'microwave_oven': False,
            'air_conditioning': False,
            'dishwasher': False,
            'tv': False,
            'with_animals': False,
            'with_children': False
        }

        if 'бытовая техника' in info:
            conditions['refregirator'] = True
            conditions['washer'] = True
            conditions['dishwasher'] = True
            conditions['tv'] = True
            conditions['air_conditioning'] = True

        if 'можно с детьми' in info:
            conditions['with_children'] = True

        if 'можно с животными' in info:
            conditions['with_animals'] = True
