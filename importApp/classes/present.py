import requests, re, time, geohash, json, traceback
import importApp.classes.offers_struct as off_str
import importApp.classes.proxy as proxy
import importApp.classes.geo_utils as geo_utils
from certifi import where
from datetime import timedelta
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from datetime import datetime
from requests.exceptions import ProxyError, ConnectionError, Timeout

es = Elasticsearch()

class PresentParser:

    def parseList(self, params):
        i = 1
        urllist = []
        while i <= int(params['pages']):
            html_code = self.__get_html(params['link']+'?page='+str(i))
            data_table = BeautifulSoup(html_code, 'lxml').find_all('div', {"class": "notice-item__image-wrapper"})
            for data in data_table:
                link = data.find('a', {'class': 'image-flex__wrapper'})['href']
                url_a = link.split('/')
                id = url_a[len(url_a) - 1]
                date_str = data.find_parent('div').find_next_sibling('div').find('div', {"class": 'text-muted'}).text

                date = self.parse_data(date_str.lower())
                url = {
                    'url': params['url'] + link,
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
                try:
                    es.index('urls_history', {"media": params['media'], "eid": eid, "data": url['url']})
                    es.index('resource_urls', {"media": params['media'], "link": url['url'], 'pause': params['pause'], 'city': params['city']})
                    es.reindex
                except Exception as ex:
                    print(traceback.format_exc())

    def parse_data(self, data_str):
        dt_now = datetime.today()
        year = dt_now.year
        mon = dt_now.month
        mday = dt_now.day
        result = re.findall(r'сегодня,\sв\s(\d{1,2}):(\d{1,2})', data_str)
        if len(result) != 0:
            res = datetime(year, mon, mday, int(result[0][0]), int(result[0][1]));
            return res

        result = re.findall(r'вчера', data_str)
        if len(result) != 0:
            res = datetime(year, mon, mday - 1, 0, 1);
            return res

        result = re.findall(r'(\d+)\s(\w+)\s(\d{4})', data_str)
        if len(result) != 0:
            month = self.month_num(result[0][1].lower())
            res = datetime(int(result[0][2]), month, int(result[0][0]), 0, 1)
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
                self.req = requests.get(url, proxies=prox, timeout=(3, 5), headers=proxy.get_headers("present_site"), verify=where(),)
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
        html_code = self.__get_html(url)

        global data

        data = {
            'importId': int(time.time() * 100000),
            'sourceMedia': 'present_site',
            'Url4Search': "\"" + parameters['link'] + "\"",
            'sourceUrl': parameters['link'],
            'addDate': None,
            'offerTypeCode': None,
            'typeCode': None,
            'categoryCode': None,
            'addressBlock': None,
            'phoneBlock': None,
            'emailBlock' : None,
            'buildingType': None,
            'buildingClass': None,
            'newBuilding': None,
            'mortgages' : False,
            'description': ''
        }

        global soup
        global breadcrumbs
        global info
        soup = BeautifulSoup(html_code, 'lxml').find('body')

        tag_breadcrumbs = soup.find('div', class_='breadcrumbs')
        breadcrumbs = re.sub(r'\s+', '', tag_breadcrumbs.get_text().lower()).split("»")
        num = re.sub(r'\D', '', soup.find_all('div', {'class': 'items-bar__group items-bar__group--double-indent'})[1].text)
        if re.sub(r'\D', '' , parameters['link']) != num:
            print('error in link: ' + parameters['link'])
        info = self.__get_info()
        # pprint(info)
        # Обязательные поля
        data['addDate'] = self.__get_date()
        data['changeDate'] =  data['addDate']
        data['offerTypeCode'] = self.__get_offer_type_code()
        data['typeCode'] = self.__get_type_code()
        data['categoryCode'] = self.__get_category_code()
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
        data['newBuilding'] = self.__get_type_novelty()
        # data['object_stage'] = self.__get_object_stage()

        # Прочие поля
        self.__get_price()
        self.__get_photo_url()
        self.__get_email()
        self.__get_balcony()
        self.__get_description()
        self.__get_rooms_count()
        self.__get_floor()
        self.__get_square()
        self.__get_condition()
        self.__get_house_type()
        self.__get_rooms_scheme()
        self.__get_other_fields()
        self.__get_bathroom_type()
        self.__get_mediator_company()
        if data['offerTypeCode'] == 'rent' \
                and data['categoryCode'] == 'rezidential':
            data['conditions'] = self.__get_rent_fields()

        return data

    def __get_info(self):
        info = {}
        all_info = soup.find_all('div', class_='notice-card__field word-break')

        for unit in all_info:
            key = unit.strong.string.lower().replace(':', '')
            value = unit.span.get_text().replace('\r', ' ').replace('\n', ' ')
            info[key] = value

        return info

    def __get_id(self):
        date_create = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour,
                               datetime.now().minute, datetime.now().second, datetime.now().microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_date(self):
        tag_date = soup.find('div', class_='items-bar__group items-bar__group--double-indent')
        info_date = tag_date.get_text().lower().replace('\n', '').replace('размещено:', '')
        dmy = re.findall(r'\w+', info_date)
        date_time = {
            'day': None,
            'month': None,
            'year': None,
            'hour': '12',
            'minute': '00',
            'second': '00'
        }

        now_date = datetime.today()

        if dmy[0] == 'вчера':
            yesterday = now_date - timedelta(days=1)
            date_time['day'] = yesterday.day
            date_time['month'] = yesterday.month
            date_time['year'] = yesterday.year
            date_time['hour'] = yesterday.hour
            date_time['minute'] = yesterday.minute

        elif dmy[0] == 'сегодня':
            date_time['day'] = now_date.day
            date_time['month'] = now_date.month
            date_time['year'] = now_date.year
            date_time['hour'] = int(dmy[2])
            date_time['minute'] = dmy[3]

        else:
            date_time['day'] = dmy[0]
            date_time['month'] = off_str.get_month(dmy[1])
            date_time['year'] = dmy[2]
            date_time['hour'] = now_date.hour
            date_time['minute'] = now_date.minute

        date = datetime(int(date_time['year']), int(date_time['month']), int(date_time['day']), date_time['hour'],
                        int(date_time['minute']))
        msc_date = date - timedelta(hours=7)
        unix_date = int(time.mktime(msc_date.timetuple()))

        return unix_date

    def __get_address(self):
        tag_address = soup.find('div', {"id":'notice-card__map'}) # поиск одной записи с тегом <div>, определенным классом и строкой Адрес

        addressBlock = {
            'region': 'Хабаровский край',
            'city': 'г. Хабаровск',
            'admArea': None,
            'area': None,
            'street': None,
            'building': None,
            'apartment': None,
            'station': None,
            'busStop': None
        }
        address_line = ""
        if tag_address:

            address_line = tag_address['data-address'].replace('\n', '').strip()
            address = re.sub(r'\(.+\)|(,*\s*под(ъ|ь).+)', '', address_line)

            address = address.split(',')  # редактируем запись, избавляясь от лишних символов/слов
            address_clear = address.copy()
            for idx, item in enumerate(address):
                try:
                    item = item.strip()
                    if re.findall(r'(^село)|(^пос(е|ё)лок)|(^с\.)|(^С\.)|(^п\.)|(пгт)', item):
                        addressBlock['city'] = item
                        del address_clear[idx-(len(address)-len(address_clear))]
                    elif re.findall(r'(\s+кра(й|и))|(кра(й|и)\s+)', item):
                        addressBlock['region'] = item
                        del address_clear[idx-(len(address)-len(address_clear))]
                    elif re.findall(r'(\s+((ра(й|и)он)|(р-н)))|((ра(й|и)он)|(р-н))\s+', item):
                        del address_clear[idx-(len(address)-len(address_clear))]
                except ValueError as e:
                    print("Error in address", e)
            try:
                house_number = None
                street = None
                if len(address_clear) == 2 and re.findall(r'(ул(ица|\.|\s))|(\s*пер(еул|\.|\s|$))|(проспект|пр-т|п-т|бульвар)', address_clear[0]):
                    street = address_clear[0]
                    house_number = address_clear[1].strip()
                elif len(address_clear) == 2 and re.findall(r'(ул(ица|\.|\s))|(\s*пер(еул|\.|\s|$))|(проспект|пр-т|п-т|бульвар)', address_clear[1]):
                    street = address_clear[1]
                elif len(address_clear) == 1:
                    street = address_clear[0]
                else:
                    street = address_clear[-2].strip()
                    house_number = address_clear[-1].strip()
                addressBlock['street'] = street.strip()
                addressBlock['house'] = house_number
            except IndexError:
                try:
                    addressBlock['street'] = address_clear.strip()
                except AttributeError:
                    if address_clear:
                        addressBlock['street'] = address_clear[0].strip()
        else:
            if 'улица/переулок' in info:
                addressBlock['street'] = info['улица/переулок']
            elif 'улица' in info:
                addressBlock['street'] = info['улица']
            elif 'местоположение' in info:
                addressBlock['street'] = info['местоположение']
            if 'населенный пункт' in info:
                position = info['населенный пункт'].split(',')
                if len(position) == 1:
                    addressBlock['city'] = str(position[0])
                else:
                    for item in position:
                        if 'село' in item or 'c.' in item:
                            addressBlock['city'] = item
        data['description'] = data['description'] + ' ' + address_line
        addressBlock['city'] = addressBlock['city'].replace(',','')
        return addressBlock

    def __get_type_novelty(self):
        try:
            if breadcrumbs[6] == 'новыеквартиры':
                data['objectStage'] = off_str.get_object_stage('сдан')
                return True

            if 'новые квартиры' in info:
                if info['новые квартиры'].lower() == 'да':
                    data['objectStage'] = off_str.get_object_stage('сдан')
                    return True
                else:
                    return False
            else:
                return False

        except IndexError:
            return False

    def __get_offer_type_code(self):
        try:
            if breadcrumbs[4] == 'посуточно':
                data['rentType'] = 'short'
                return off_str.get_OTC('аренда')
            else:
                if off_str.get_OTC(breadcrumbs[2]) == 'rent':
                    data['rentType'] = 'long'
                return off_str.get_OTC(breadcrumbs[2])
        except IndexError:
            if off_str.get_OTC(breadcrumbs[2]) == 'rent':
                data['rentType'] = 'long'
            return off_str.get_OTC(breadcrumbs[2])

    def __get_category_code(self):
        return off_str.get_CC(breadcrumbs[3])

    def __get_building_type(self):
        if breadcrumbs[3] == 'жилая':
            return off_str.get_BT(data['buildingClass'])

        elif breadcrumbs[3] == 'участкиидачи':
            return off_str.get_BT('dacha_land')

        elif breadcrumbs[3] == 'коммерческая' or breadcrumbs[3] == 'гаражи':
            if 'вид объекта' in info:
                if off_str.get_BT(data['typeCode']):
                    return off_str.get_BT(data['typeCode'])
                else:
                    data['typeCode'] = 'other'
                    return off_str.get_BT('other')
            else:
                data['typeCode'] = 'other'
                return off_str.get_BT('other')

    def __get_building_class(self):
        if breadcrumbs[3] == 'жилая':
            return off_str.get_BC(data['typeCode'])
            # if findall('комнаты,малосемейки', breadcrumbs[4]):
            #     if 'объект аренды' in info:
            #         return off_str.get_BC(info['объект аренды'])
            #     else:
            #         return off_str.get_BC('экономкласс')
            #
            # elif findall('малосемейки', breadcrumbs[4]):
            #     return off_str.get_BC(breadcrumbs[4])
            #
            # elif findall('дома', breadcrumbs[4]):
            #     if 'объект продажи' in info:
            #         return off_str.get_BC(info['объект продажи'])
            #     elif 'объект аренды' in info:
            #         return off_str.get_BC(info['объект аренды'])
            #     else:
            #         return off_str.get_BC('экономкласс')
            #
            # elif findall('квартиры', breadcrumbs[4]) or findall('комнаты', breadcrumbs[4]):
            #     if 'планировка' in info:
            #         return off_str.get_BC(info['планировка'])
            #     else:
            #         return off_str.get_BC('экономкласс')

        elif breadcrumbs[3] == 'коммерческая' or breadcrumbs[3] == 'гаражи':
            return off_str.get_BC('а')

        elif breadcrumbs[3] == 'участкиидачи':
            return None

    def __get_type_code(self):
        if breadcrumbs[3] == 'жилая':
            if 'количество комнат' in info:
                if re.findall('дол', info['количество комнат']):
                    return off_str.get_TC('доля')

            if breadcrumbs[4] == 'малосемейки' or breadcrumbs[4] == 'комнаты':
                return off_str.get_TC('комната')

            elif breadcrumbs[4] == 'дома':
                if 'объект продажи' in info:
                    return off_str.get_TC(info['объект продажи'])
                else:
                    return off_str.get_TC('дом')

            elif breadcrumbs[4] == 'квартиры':
                return off_str.get_TC(breadcrumbs[4])

            elif breadcrumbs[4] == 'комнаты,малосемейки':
                if 'объект аренды' in info:
                    return off_str.get_TC(info['объект аренды'])
                else:
                    return off_str.get_TC('комната')

        elif breadcrumbs[2] == 'сдам' and breadcrumbs[3] == 'коммерческая':
            data['typeCode'] = off_str.get_TC(breadcrumbs[4])
            if 'вид объекта' in info:
                if off_str.get_TC(info['вид объекта']):
                    return off_str.get_TC(info['вид объекта'])
                else:
                    return data['typeCode']

        elif breadcrumbs[3] == 'коммерческая':
            if 'вид объекта' in info:
                if off_str.get_TC(info['вид объекта']):
                    return off_str.get_TC(info['вид объекта'])
                else:
                    return off_str.get_TC('другое')

        elif breadcrumbs[3] == 'участкиидачи':
            return off_str.get_TC('дачныйземельныйучасток')

        elif breadcrumbs[3] == 'гаражи':
            return off_str.get_TC('другое')

    def __get_phones(self):
        phoneBlock = {
            'main': None,
            'cellphone': None,
            'office': None,
            'home': None,
            'other': None,
            'fax': None
        }
        tag_numbers = soup.find_all('p')

        if tag_numbers:
            list_phones = []
            for item in tag_numbers:
                if item.find('a', href=re.compile(r'tel:')):
                    number = re.sub(r'\D', '', item.text)
                    if number.startswith('8') and len(number) == 11:
                        number = number.replace('8', '7', 1)
                    elif len(number) == 6:
                        number = '4212' + number
                    list_phones.append(number)


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

    def __get_price(self):
        check_tag_price = soup.find('div', class_='notice-card__financial-fields media')
        if check_tag_price:
            tag_price = check_tag_price.find('div', class_='media-body').find('p')
            price = float(tag_price.get_text().strip().replace(' ', '').replace('\n', '').replace('\xa0', ''))
            data['ownerPrice'] = price / 1000

        else:
            return None

    def __get_photo_url(self):
        check_tag_photos = soup.find('div', class_='light-box')
        if check_tag_photos:
            photos = []
            tag_photos = check_tag_photos.find_all('div', class_='image-flex mb-1')
            for photo in tag_photos:
                photo = {
                    'addDate': datetime.now(),
                    'ext': "jpg",
                    'fullName': "present_img.jpg",
                    'href': 'https://present-dv.ru' + photo.find('a')['href'],
                    'isTemp': False,
                    'name': "present_img",
                    'type': 0
                }
                photos.append(photo)
            data['photos'] = photos
        else:
            return None

    def __get_email(self):
        if 'e-mail' in info:
            data['emailBlock'] = { 'main' : info['e-mail']}
        else:
            return None

    def __get_balcony(self):
        if 'балкон/лоджия' in info:
            pattr = 'балкон'
            if re.findall(pattr, info['балкон/лоджия']):
                data['balcony'] = True

            pattr = 'лоджия'
            if re.findall(pattr, info['балкон/лоджия']):
                data['loggia'] = True

            if re.findall('без', info['балкон/лоджия']):
                data['balcony'] = False

        else:
            return False

    def __get_description(self):
        if 'дополнительно' in info:
            data['description'] = info['дополнительно'] + " " + data['description']
        try:
            data['description'].replace("\n", " ").replace("\"","'")
        except Exception as e:
            None;

    def __get_bathroom_type(self):
        if 'туалет (санузел)' in info:
            data['bathroom'] = off_str.get_bathroom(info['туалет (санузел)'])

    def __get_rooms_count(self):
        try:

            if breadcrumbs[5] == 'однокомнатные' or breadcrumbs[6] == '1-комнатные':
                data['roomsCount'] = 1
            elif breadcrumbs[5] == 'двухкомнатные' or breadcrumbs[6] == '2-комнатные':
                data['roomsCount'] = 2
            elif breadcrumbs[5] == 'трехкомнатные' or breadcrumbs[6] == '3-комнатные':
                data['roomsCount'] = 3
            elif breadcrumbs[6] == '4-комнатные':
                data['roomsCount'] = 3
        except IndexError:
            return

        if 'количество комнат' in info:
            try:
                data['roomsCount'] = int(info['количество комнат'].split(' ')[0])
            except ValueError:
                try:
                    data['roomsCount'] = int(info['количество комнат'].split('-')[0])
                except ValueError:
                    return None

    def __get_rooms_scheme(self):
        if 'расположение комнат' in info:
            scheme = info['расположение комнат'].lower().replace('комнаты', '').replace('комнаты', '').strip()
            data['roomsScheme'] = off_str.get_room_scheme(scheme)

    def __get_floor(self):
        if 'этажность' in info:
            data['floorsCount'] = int(info['этажность'])

        if 'этаж' in info:
            data['floor'] = int(info['этаж'])

        if 'этажей в доме' in info:
            data['floorsCount'] = int(info['этажей в доме'])

        else:
            return None

    def __get_square(self):
        if 'площадь общая (кв. м)' in info:
            data['squareTotal'] = float(info['площадь общая (кв. м)'].replace(',', '.'))
        if 'площадь (кв. м)' in info and data['categoryCode'] == 'rezidential':
            data['squareTotal'] = float(info['площадь (кв. м)'].replace(',', '.'))
        if 'общая площадь (кв. м)' in info:
            data['squareTotal'] = float(info['общая площадь (кв. м)'].replace(',', '.'))
        if 'площадь жилая (кв. м)' in info:
            data['squareLiving'] = float(info['площадь жилая (кв. м)'].replace(',', '.'))
        if 'площадь комнаты (кв. м)' in info and data['typeCode'] == 'room' or data['typeCode'] == 'share':
            data['squareLiving'] = float(info['площадь комнаты (кв. м)'].replace(',', '.'))
        if 'площадь кухни (кв. м)' in info:
            data['squareKitchen'] = float(info['площадь кухни (кв. м)'].replace(',', '.'))
        if 'площадь участка (сотки)' in info:
            data['squareLand'] = float(info['площадь участка (сотки)'].replace(',', '.'))
            data['squareLandType'] = 'ar'
        if 'площадь (сотки)' in info:
            data['squareLand'] = float(info['площадь (сотки)'].replace(',', '.'))
            data['squareLandType'] = 'ar'
        if 'общая площадь дома (кв. м)' in info:
            data['squareTotal'] = float(info['общая площадь дома (кв. м)'].replace(',', '.'))
        else:
            return None

    def __get_condition(self):
        if 'состояние' in info:
            data['condition'] = off_str.get_condition(info['состояние'])
        else:
            return None

    def __get_house_type(self):
        if 'материал стен' in info:
            data['houseType'] = off_str.get_house_type(info['материал стен'])

    def __get_other_fields(self):
        if 'отопление' in info:
            data['central_heating'] = True
        if 'водоснабжение' in info:
            data['water_supply'] = True
        if 'расстояние до города (км)' in info:
            data['distance'] = info['расстояние до города (км)'].replace('км', '').rstrip() + ' км'

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

        if 'на длительный срок' in info:
            if re.findall('да', info['на длительный срок'].lower()):
                data['rentType'] = 'long'

        if 'комплектация' in info:
            if re.findall('полностью', info['комплектация'].lower()):
                conditions['complete'] = True
                conditions['living_room_furniture'] = True
                conditions['kitchen_furniture'] = True
                conditions['couchette'] = True
                conditions['dishes'] = True
                conditions['refrigerator'] = True
                conditions['washer'] = True
                conditions['microwave_oven'] = True
                conditions['air_conditioning'] = True
                conditions['dishwasher'] = True
                conditions['tv'] = True

            else:
                conditions['complete'] = False

            if 'холодильник' in info:
                if re.findall('да', info['холодильник'].lower()):
                    conditions['refrigerator'] = True
                else:
                    conditions['refrigerator'] = False

            if 'стиральная машина' in info:
                if re.findall('да', info['стиральная машина'].lower()):
                    conditions['washer'] = True
                else:
                    conditions['washer'] = False

            if 'кондиционер' in info:
                if re.findall('да', info['кондиционер'].lower()):
                    conditions['air_conditioning'] = True
                else:
                    conditions['air_conditioning'] = False

            if 'телевизор' in info:
                if re.findall('да', info['телевизор'].lower()):
                    conditions['tv'] = True
                else:
                    conditions['tv'] = False

        if 'можно с домашними питомцами' in info:
            if re.findall('да', info['можно с домашними питомцами'].lower()):
                conditions['with_animals'] = True
            else:
                conditions['with_animals'] = False

        if '+ счетчики' in info:
            data['electrificPay'] = True
            data['waterPay'] = True
            data['gasPay'] = True

        if 'количество спальных мест' in info:
            conditions['couchette'] = True

        return conditions

    def __get_mediator_company(self):
        if 'агентство' in info:
            if info['агентство'].lower() == 'да':
                data['mediatorCompany'] = 'Агентство'
