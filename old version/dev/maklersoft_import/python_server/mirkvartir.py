import requests
import time
import parsingfunctools as sf
import secrettools as ts

from certifi import where
from bs4 import BeautifulSoup
from pprint import pprint
from re import findall, compile
from datetime import datetime, timedelta
from requests.exceptions import ProxyError, ConnectionError, Timeout


class MirKvarParser:

    def __get_html(self, params):
        source = params['source']
        url = params['url']
        ip = params['ip']
        attempt = 1
        delay_sec = 0.5
        while attempt <= 10:
            proxy = ts.set_proxy()
            # pprint(proxy)
            try:
                self.req = requests.get(url,
                                        headers=ts.get_headers(source),
                                        cookies=ts.cook_for_ip(source, ip),
                                        proxies=proxy,
                                        verify=where(),
                                        timeout=(3, 5))
                if self.req.status_code == requests.codes.ok:
                    self.req.encoding = 'utf8'
                    return self.req.text
                else:
                    attempt += 1
                    # time.sleep(delay_sec)
            except (ProxyError, ConnectionError, Timeout):
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        url = parameters['url']
        html_code = self.__get_html(parameters)
        # pprint(html_code)
        global data
        data = {
            'importId': int(time.time() * 100000),
            'source_media': parameters['source'],
            'source_url': parameters['url'],
            'add_date': None,
            'offer_type_code': None,
            'type_code': None,
            'category_code': None,
            'phones_import': None,
            'locality': 'Хабаровск',
            'address': None,

            'building_type': None,
            'building_class': None,
            # 'location_lat': None,
            # 'location_lon': None,
            'new_building': None,
        }

        global soup
        global title_soup
        global breadcrumbs
        global info
        title_soup = BeautifulSoup(html_code, 'lxml').find('title')
        soup = BeautifulSoup(html_code, 'lxml').find('body')

        info = self.__get_info()
        # pprint(info)

        # Обязательные поля
        data['id'] = self.__get_id()
        data['source_media'] = parameters['source']
        data['source_url'] = parameters['url']
        data['add_date'] = self.__get_date()
        self.__get_offer_type_code()
        data['type_code'] = self.__get_type_code()
        data['category_code'] = self.__get_category_code()
        data['phones_import'] = self.__get_phones()
        data['address'] = self.__get_address()

        # Обязательные поля, но возможны значения по умолчанию
        data['building_class'] = self.__get_building_class()
        data['building_type'] = self.__get_building_type()
        data['new_building'] = self.__get_type_novelty()
        # data['object_stage'] = self.__get_object_stage()

        # # Прочие поля
        self.__get_price()
        self.__get_mediator_company()
        self.__get_photo_url()
        # self.__get_email()
        self.__get_balcony()
        self.__get_description()
        self.__get_rooms_count()
        self.__get_floor()
        self.__get_square()
        self.__get_bathroom()
        self.__get_condition()
        self.__get_house_type()
        # self.__other_fields()

        if data['offer_type_code'] == 'rent' \
                and data['category_code'] == 'rezidential':
            self.__get_rent_fields()

        return data

    def __get_id(self):
        now_date = datetime.today()
        date_create = datetime(now_date.year, now_date.month, now_date.day,
                               now_date.hour,
                               now_date.minute, now_date.second, now_date.microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_info(self):
        tag_information = soup.find('div', class_='l-object-info')
        information = {}
        if tag_information:
            tag_information = tag_information.find_all('td')
            for tag in tag_information:
                key = tag.find('span').text.lower()
                raw_value = tag.find('strong').text
                value = raw_value.replace('\u2009', '').replace('\xa0', '').replace(' м²', '').replace('руб.', '')
                information[key] = value

        tag_dopinfo = soup.find('div', class_='details')
        if tag_dopinfo:
            columns = tag_dopinfo.find_all('div', class_='column')

            for column in columns:
                column = column.find_all('p')
                for p in column:
                    key = p.find('span').text.lower()
                    value = p.find('strong').text.lower()
                    if not key in information:
                        information[key] = value

        other_info = soup.find('div', class_='complex-info')
        if other_info:
            other_info = other_info.find('div', class_='details')

            column = other_info.find_all('p')
            for p in column:
                key = p.find('span').text.lower()
                value = p.find('strong').text.lower()
                if not key in information:
                    information[key] = value

        return information

    def __get_date(self):
        tag_date = soup.find('div', class_='dates')
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
            raw_datetime = tag_date.text
            _, raw_datetime = raw_datetime.split(',')
            raw_datetime = raw_datetime.replace(' размещено ', '')
            raw_datetime = raw_datetime.split()

            date_type, _, raw_time = raw_datetime

            if date_type == 'сегодня':
                date_time['day'] = now_date.day
                date_time['month'] = now_date.month

            elif date_type == 'вчера':
                yesterday = now_date - timedelta(days=1)
                date_time['day'] = yesterday.day
                date_time['month'] = yesterday.month
            else:
                raw_date, raw_time = raw_datetime[0], raw_datetime[2]

                day, month, year = raw_date.split('.')
                date_time['day'] = day
                date_time['month'] = month
                date_time['year'] = '20'+year

                hour, minute = raw_time.split(':')
                date_time['hour'] = hour
                date_time['minute'] = minute

            hour, minute = raw_time.split(':')
            date_time['hour'] = hour
            date_time['minute'] = minute

            date = datetime(int(date_time['year']), int(date_time['month']),
                            int(date_time['day']), int(date_time['hour']),
                            int(date_time['minute']))

            msc_date = date - timedelta(hours=7)
            unix_date = int(time.mktime(msc_date.timetuple()))

            data['change_date'] = unix_date

            return unix_date

    def __get_address(self):
        tag_address = soup.find('p', class_='address')
        if tag_address:
            tag_address = tag_address.find_all('a')
            address_list = []
            for tag in tag_address:
                address_list.append(tag.text)
            street, number_house = address_list[-2], address_list[-1]
            address = street + ', ' + number_house
            try:
                city = address_list[-3]
            except IndexError:
                city = address_list[0]
            data['locality'] = 'г. ' + city
            if findall(r'\w\.', city):
                data['locality'] = city
            return address

    def __get_mediator_company(self):
        tag_mediator_company = soup.find('div', class_=compile('seller-info'))
        if tag_mediator_company:
            mediator_company = tag_mediator_company.find('span').text
            mediator_company = mediator_company.lower()
            if findall('агент', mediator_company):
                data['mediator_company'] = 'Агентство'
                name_company = tag_mediator_company.find('strong').text
                name_company = name_company
                if name_company:
                    data['mediator_company'] = name_company
            else:
                return

    def __get_offer_type_code(self):
        title = title_soup.text.lower()
        if title:
            if findall('продажа', title):
                data['offer_type_code'] = 'sale'
            elif findall('снять', title):
                data['offer_type_code'] = 'rent'
            elif findall('аренда', title):
                data['offer_type_code'] = 'rent'

            if findall('студии', title):
                data['rooms_scheme'] = 'studio'
                data['rooms_count'] = 1

    def __get_category_code(self):
        if data['type_code']:
            land_cc = ['dacha_land']
            rezidential_cc = ['share',
                              'room',
                              'apartment',
                              'house',
                              'cottage',
                              'townhouse',
                              'duplex']

            if data['type_code'] in land_cc:
                return 'land'
            elif data['type_code'] in rezidential_cc:
                return 'rezidential'
            else:
                return 'commersial'

    def __get_building_class(self):
        if data['category_code'] == 'land':
            return None

        elif data['category_code'] == 'rezidential':
            if data['type_code'] == 'apartment' or data['type_code'] == 'room' or data['type_code'] == 'share':
                return sf.get_BC('экономкласс')

            else:
                return sf.get_BC(data['type_code'])

        elif data['category_code'] == 'commersial':
            if 'класс бизнес-центра' in info:
                return sf.get_BC(info['класс бизнес-центра'])
            else:
                return 'a'

    def __get_building_type(self):
        if data['type_code']:
            return sf.get_BT(data['type_code'])

    def __get_type_code(self):
        tag_type_code = soup.find('div', class_='l-house-info')
        if tag_type_code:
            type_code = tag_type_code.find('h3')
            type_code = type_code.text
            if findall('квартир', type_code):
                return sf.get_TC('квартира')
            elif findall('комнат', type_code):
                return sf.get_TC('комната')
            elif findall('коттедж', type_code):
                return sf.get_TC('коттедж')
            elif findall('коттедж', type_code):
                return sf.get_TC('коттедж')
            elif findall('дом', type_code):
                return sf.get_TC('дом')
            elif findall('таунхаус', type_code):
                return sf.get_TC('таунхаус')
            elif findall('даче', type_code):
                return sf.get_TC('дача')
            elif findall('псн', type_code):
                return sf.get_TC('псн')
            elif findall('офис', type_code):
                return sf.get_TC('офис')
            elif findall('торгов', type_code):
                return sf.get_TC('торговое помещение')
            elif findall('склад', type_code):
                return sf.get_TC('склад')
            elif findall('участ', type_code):
                return sf.get_TC('участок')
            else:
                return sf.get_TC('другое')

    def __get_phones(self):
        tag_phone = soup.find('a', class_='phone')
        if tag_phone:
            phones = []
            raw_phone = tag_phone.find('span').text
            phone = raw_phone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '').replace('+', '')
            phones.append(phone)

            return phones

    def __get_type_novelty(self):
        tag_type_novelty = soup.find('div', class_='l-house-info')
        if tag_type_novelty:
            type_novelty = tag_type_novelty.find('h3')
            type_novelty = type_novelty.text
            if findall('новострой', type_novelty):
                data['object_stage'] = 'ready'
                return True
            elif 'срок сдачи' in info:
                year = int(findall(r'\d{4}', info['срок сдачи'])[0])
                current_year = datetime.now().year
                if year == current_year:
                    data['object_stage'] = 'ready'
                elif year > current_year:
                    data['object_stage'] = 'building'
                return True
            else:
                return False

        else:
            return False

    def __get_price(self):
        tag_price = soup.find('div', class_='price m-all')
        if tag_price:
            raw_price = tag_price.find('strong').text
            type_price = tag_price.find('span').text
            if type_price and data['offer_type_code'] == 'rent':
                if findall('месяц', type_price):
                    data['rent_type'] = 'long'
                elif findall('день', type_price):
                    data['rent_type'] = 'short'

            price = findall(r'\d+', raw_price)
            price = ''.join(price)
            price = float(float(price) / 1000)
            data['price'] = price

    def __get_photo_url(self):
        tag_photos = soup.find_all('img', src=True)
        if tag_photos:
            photo_url = []
            photo = 'https:' + tag_photos[0]['src']
            photo_url.append(photo)

            data['photo_url'] = photo_url

    def __get_description(self):
        tag_description = soup.find('div', class_='l-object-description')
        if tag_description:
            description = tag_description.find('p').text
            data['description'] = description.replace('\n', ' ')

    def __get_floor(self):
        if 'этаж' in info:
            try:
                floor, floors_count = findall(r'\d+', info['этаж'])
                data['floor'] = int(floor)
                data['floors_count'] = int(floors_count)
            except ValueError:
                try:
                    floor = int(info['этаж'])
                    data['floor'] = int(floor)
                    data['floors_count'] = int(floor)

                except ValueError:
                    exit()

        if 'этажность' in info:
            levels_count = findall(r'\d+', info['этажность'])[0]
            data['levels_count'] = int(levels_count)

    def __get_rooms_count(self):
        if 'комнаты' in info:
            rooms_count = info['комнаты'].split('-')[0]
            data['rooms_count'] = int(rooms_count)

        elif 'комната' in info:
            rooms_count = info['комната']
            data['rooms_count'] = int(rooms_count)

        elif 'всего комнат' in info:
            rooms_count = info['всего комнат']
            data['rooms_count'] = int(rooms_count)

        elif 'квартира' in info and data['type_code'] == 'room':
            rooms_count = findall(r'\d+', info['квартира'])[0]
            data['rooms_count'] = int(rooms_count)
            if data['rooms_count'] > 1 and data['offer_type_code'] == 'sale':
                data['type_code'] = 'share'

    def __get_house_type(self):
        if 'дом' in info:
            try:
                raw_info = info['дом'].split(',')
                house_type = raw_info[0].strip()
                data['house_type'] = sf.get_house_type(house_type)
                build_year = raw_info[1].strip()
                data['build_year'] = build_year
            except (ValueError, IndexError):
                house_type = info['дом'].strip()
                data['house_type'] = sf.get_house_type(house_type)

        if 'тип зданий' in info:
            data['house_type'] = sf.get_house_type(info['тип зданий'])

    def __get_square(self):
        if 'общая площадь' in info:
            data['square_total'] = float(info['общая площадь'])

        if 'площадь кухни' in info:
            data['square_kitchen'] = float(info['площадь кухни'])

        if 'площадь комнаты' in info and data['type_code'] == 'room':
            data['square_living'] = float(info['площадь комнаты'])

        if 'площадь участка' in info:
            square_land = findall(r'\d+', info['площадь участка'])[0]
            if findall('сот', info['площадь участка']):
                data['square_land_type'] = 'ar'
            else:
                data['square_land_type'] = 'ha'

            data['square_land'] = float(square_land)

        if 'площадь' in info:
            square_list = info['площадь'].replace('м', '').split(',')
            square_total = None
            square_kitchen = None
            square_living = None
            square_land = None
            for item in square_list:
                if findall('кухня', item):
                    square_kitchen = findall(r'\d+', item)[0]
                    square_kitchen = float(square_kitchen)
                elif findall('жилая', item):
                    square_living = findall(r'\d+', item)[0]
                    square_living = float(square_living)
                elif findall('участок', item):
                    square_land = findall(r'\d+', item)[0]
                    square_land = float(square_land)
                    if findall('сот', item):
                        data['square_land_type'] = 'ar'
                    else:
                        data['square_land_type'] = 'ha'
                else:
                    square_total = findall(r'\d+', item)[0]
                    square_total = float(square_total)

            if square_total and not 'square_total' in data:
                data['square_total'] = square_total

            if square_kitchen and not 'square_kitchen' in data:
                data['square_kitchen'] = square_kitchen

            if square_living and not 'square_living' in data:
                data['square_living'] = square_living

            if square_land and not 'square_land' in data:
                data['square_land'] = square_land

    def __get_condition(self):
        if 'состояние' in info:
            condition = findall(r'\w* ремонт', info['состояние'])
            if condition:
                condition = condition[0]
            else:
                condition = findall(r'\w*ремонт', info['состояние'])
                if condition:
                    condition = condition[0]
                else:
                    return
            data['condition'] = sf.get_condition(condition)

    def __get_balcony(self):
        if 'планировка' in info:
            if findall('балкон', info['планировка']):
                data['balcony'] = True
            elif findall('лоджия', info['планировка']):
                data['loggia'] = True

    def __get_bathroom(self):
        if 'планировка' in info:
            if findall('совмещенный', info['планировка']):
                data['bathroom'] = sf.get_bathroom('совмещенный')
            elif findall('раздельный', info['планировка']):
                data['bathroom'] = sf.get_bathroom('раздельный')
            elif findall('санузел 2 и более', info['планировка']):
                data['bathroom'] = sf.get_bathroom('санузел 2 и более')

    def __get_rent_fields(self):
        if 'коммуникации' in info:
            if findall('отопление', info['коммуникации']):
                    data['central_heating'] = True

        if 'бытовая техника' in info:
            if findall('телевизор', info['бытовая техника']):
                data['tv'] = True

            if findall('холодильник', info['бытовая техника']):
                data['refrigerator'] = True

            if findall('стиральная', info['бытовая техника']):
                data['washer'] = True

            if findall('посудомоечная', info['бытовая техника']):
                data['dishwasher'] = True

        if 'состояние' in info:
            if findall('кухонный', info['состояние']):
                data['kitchen_furniture'] = True
                data['dishes'] = True

            if findall('мебелир', info['состояние']):
                data['living_room_furniture'] = True

        if 'комфорт' in info:
            if findall('кондиционер', info['комфорт']):
                data['air_conditioning'] = True


if __name__ == '__main__':
    url = 'https://arenda.mirkvartir.ru/211339757/'
    X = MirKvarParser()
    params = {
        'source': 'mkv',
        'url': url,
        'ip': '193.124.182.208'
    }

    pprint(X.get_data(params))
