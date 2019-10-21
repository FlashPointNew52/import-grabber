import requests
import time
import datetime
import parsingfunctools as sf
import secrettools as ts
import re

from bs4 import BeautifulSoup
from pprint import pprint
from re import findall, compile
from datetime import datetime, timedelta
from requests.exceptions import ProxyError, ConnectionError, Timeout
from certifi import where


class CianParser:

    def __get_html(self, params):
        source = params['source']
        url = params['url']
        ip = params['ip']
        attempt = 1
        delay_sec = 0.5
        while attempt <= 10:
            proxy = ts.set_proxy()
            try:
                self.req = requests.get(url,
                                        headers=ts.get_headers(source),
                                        cookies=ts.cook_for_ip(source, ip),
                                        proxies=proxy,
                                        verify=where(),
                                        timeout=(3, 5))
                if self.req.status_code == requests.codes.ok:
                    return self.req.text
                else:
                    attempt += 1
            except (ProxyError, ConnectionError, Timeout):
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        html_code = self.__get_html(parameters)

        global data

        data = {
            'importId': int(time.time() * 100000),
            'sourceMedia': 'cian',
            'sourceUrl': parameters['url'],
            'addDate': None,
            # 'locality': None,
            'offerTypeCode': None,
            'typeCode': None,
            'categoryCode': None,
            'addressBlock': None,

            'buildingType': None,
            'buildingClass': None,
            'newBuilding': False,
            'mortgages' : False
        }

        global soup
        global breadcrumbs

        soup = BeautifulSoup(html_code, 'lxml').find('body')
        tag_breadcrumbs = soup.find_all('span', itemprop='itemListElement')
        breadcrumbs = []
        for item in tag_breadcrumbs:
            breadcrumbs.append(item.find('a')['title'].lower())

        if not breadcrumbs:
            exit()

        # Обязательные поля
        data['addDate'] = self.__get_date()
        data['changeDate'] = data['addDate']
        data['offerTypeCode'] = self.__get_offer_type_code()
        data['typeCode'] = self.__get_type_code()
        data['categoryCode'] = self.__get_category_code()
        data['phoneBlock'] = { 'main' : self.__get_phones()}
        data['addressBlock'] = self.__get_address()

        # Обязательные поля, но возможны значения по умолчанию

        global info
        info = self.__get_info()
        data['buildingClass'] = self.__get_building_class()
        data['buildingType'] = self.__get_building_type()
        self.__get_type_novelty()

        # Прочие поля
        self.__get_price()
        self.__get_photo_url()
        self.__get_balcony()
        self.__get_source_media_text()
        self.__get_rooms_count()
        self.__get_square()
        self.__get_condition()
        self.__get_house_type()
        self.__get_build_year()
        self.__get_bathroom()
        self.__get_floor()
        self.__mediator_company()

        if data['offerTypeCode'] == 'rent' and data['categoryCode'] == 'rezidential':
            self.__get_rent_fields()

        return data

    def __get_info(self):
        information = {}

        tag_info = soup.find('article', class_=compile('--container--'))
        if tag_info:
            tag_info = tag_info.find_all('li', class_=compile('item'))
            for item in tag_info:
                key = item.find('span', class_=compile('name')).text.lower()
                value = item.find('span', class_=compile('value')).text.lower()
                information[key] = value

        tag_dop_info = soup.find_all('ul', class_=compile('--container--'))
        if tag_dop_info:
            for container in tag_dop_info:
                container = container.find_all('li', class_=compile('item'))
                for item in container:
                    key = item.text.lower().strip()
                    value = True
                    information[key] = value

        tag_about_home = soup.find('div', class_=compile('--column--'))
        if tag_about_home:
            tag_about_home = tag_about_home.find_all('div', class_=compile('--item--'))
            for item in tag_about_home:
                key = item.find('div', class_=compile('--name--')).text.lower()
                value = item.find('div', class_=compile('--value--')).text.lower()
                information[key] = value

        tag_info_block = soup.find('div', class_=compile('info-block'))
        if tag_info_block:
            tag_info_block = tag_info_block.find_all('div', class_=compile('--info--'))
            for item in tag_info_block:
                key = item.find('div', class_=compile('info-title')).text.lower()
                value = item.find('div', class_=compile('info-text')).text
                information[key] = value

        return information

    def __get_id(self):
        date_create = datetime(datetime.now().year, datetime.now().month, datetime.now().day, datetime.now().hour,
                               datetime.now().minute, datetime.now().second, datetime.now().microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_date(self):
        tag_date = soup.find('div', class_=compile('.+offer_meta_main_left.+'))
        if tag_date:
            info_date = tag_date.find('div', class_=compile('container')).text
            info_date = info_date.replace(',', '').replace(':', ' ').split()

            date_time = {
                'day': None,
                'month': None,
                'year': None,
                'hour': '12',
                'minute': '00',
                'second': '00'
            }

            now_date = datetime.today()

            if info_date[0] == 'вчера':
                date_time['day'] = (now_date - timedelta(1)).day
                date_time['month'] = (now_date - timedelta(1)).month
                date_time['year'] = (now_date - timedelta(1)).year
                date_time['hour'] = info_date[1]
                date_time['minute'] = info_date[2]

            elif info_date[0] == 'сегодня':
                date_time['day'] = now_date.day
                date_time['month'] = now_date.month
                date_time['year'] = now_date.year
                date_time['hour'] = info_date[1]
                date_time['minute'] = info_date[2]

            else:
                date_time['day'] = info_date[0]
                date_time['month'] = sf.get_month(info_date[1])
                date_time['year'] = now_date.year
                date_time['hour'] = info_date[2]
                date_time['minute'] = info_date[3]

            date = datetime(int(date_time['year']), int(date_time['month']), int(date_time['day']),
                            int(date_time['hour']), int(date_time['minute']))
            msc_date = date - timedelta(hours=7)
            unix_date = int(time.mktime(msc_date.timetuple()))

            return unix_date

    def __get_address(self):
        addressBlock = {
            'region': None,
            'city': None,
            'admArea': None,
            'area': None,
            'street': None,
            'house': None,
            'housing': None,
            'apartment': None,
            'metro': None,
            'bus_stop': None
        }
        tag_address = soup.find_all('a', class_=compile('address-item'))
        if tag_address:
            list_address = []
            for item in tag_address:
                list_address.append(item.text)

            street, house_number = list_address[-2:]
            addressBlock['street'] = street + ', ' + house_number
            addressBlock['city'] = list_address[1]
        return addressBlock

    def __get_type_novelty(self):
        if info:
            if 'тип жилья' in info:
                if info['тип жилья'] == 'новостройка':
                    data['newBuilding'] = True
                else:
                    data['newBuilding'] = False

    def __get_offer_type_code(self):
        if breadcrumbs[1] == 'продажа':
            return sf.get_OTC('продажа')

        elif breadcrumbs[1] == 'аренда':
            data['rentType'] = 'long'
            return sf.get_OTC('аренда')

        elif breadcrumbs[1] == 'коммерческая':
            if findall('продажа', breadcrumbs[2]):
                return sf.get_OTC('продажа')
            elif findall('аренда', breadcrumbs[2]):
                data['rent_type'] = 'long'
                return sf.get_OTC('аренда')

        elif breadcrumbs[1] == 'новостройки':
            data['newBuilding'] = True
            tag_object_stage = soup.find('span', class_=compile('newObj-subtitle'))
            if tag_object_stage:
                object_stage = tag_object_stage.text.replace('\n', '').strip().lower().split()
                data['objectStage'] = sf.get_object_stage(object_stage[0])
            return sf.get_OTC('продажа')

        elif breadcrumbs[1] == 'посуточно':
            data['rentType'] = 'short'
            return sf.get_OTC('аренда')

    def __get_category_code(self):
        if breadcrumbs[1] == 'коммерческая':
            return sf.get_CC('коммерческая')
        elif findall('земельных', breadcrumbs[2]):
            return sf.get_CC('участкиидачи')
        else:
            return sf.get_CC('жилая')

    def __get_building_type(self):
        return sf.get_BT(data['typeCode'])

    def __get_building_class(self):
        if data['categoryCode'] == 'land':
            return None

        elif data['categoryCode'] == 'commersial':
            tag_square = soup.find('div', class_=compile('info-block'))
            if tag_square:
                tag_square = tag_square.find_all('div', class_=compile('--info--'))
                for item in tag_square:
                    title = item.find('div', class_=compile('info-title')).text.lower()
                    if title == 'класс':
                        value = item.find('div', class_=compile('info-text')).text.lower()

                        return sf.get_BC(value)

                return sf.get_BC('a')
            else:
                return sf.get_BC('a')

        elif data['categoryCode'] == 'rezidential':
            if findall('квартир', breadcrumbs[2]) or findall('комнат', breadcrumbs[2]) or findall('дол', breadcrumbs[2]):
                return sf.get_BC('экономкласс')
            elif findall('таунхаус', breadcrumbs[2]):
                return sf.get_BC('таунхаус')
            elif findall('частей домов', breadcrumbs[2]):
                return sf.get_BC('дуплекс')
            elif findall('домов', breadcrumbs[2]):
                tag_type_house = soup.find('h1', class_=compile('--title--'))
                if tag_type_house:
                    type_house = tag_type_house.text.lower()
                    if findall('коттедж', type_house):
                        return sf.get_BC('коттедж')
                    else:
                        return sf.get_BC('дом')

    def __get_type_code(self):
        if findall('квартир', breadcrumbs[2]):
            return sf.get_TC('квартира')
        elif findall('комнат', breadcrumbs[2]):
            return sf.get_TC('комната')
        elif findall('дол', breadcrumbs[2]):
            return sf.get_TC('доля')
        elif findall('таунхаус', breadcrumbs[2]):
            return sf.get_TC('таунхаус')
        elif findall('частей домов', breadcrumbs[2]):
            return sf.get_TC('дуплекс')
        elif findall('домов', breadcrumbs[2]):
            tag_type_house = soup.find('h1', class_=compile('--title--'))
            if tag_type_house:
                type_house = tag_type_house.text.lower()
                if findall('коттедж', type_house):
                    return sf.get_TC('коттедж')
                else:
                    return sf.get_TC('дом')

        elif findall('участков', breadcrumbs[2]):
            return sf.get_TC('дачныйземельныйучасток')

        elif findall('склад', breadcrumbs[2]):
            return sf.get_TC('склад')
        elif findall('производство', breadcrumbs[2]):
            return sf.get_TC('производство')
        elif findall('производство', breadcrumbs[2]):
            return sf.get_TC('производство')
        elif findall('гараж', breadcrumbs[2]):
            return sf.get_TC('другое')
        elif findall('здание', breadcrumbs[2]):
            return sf.get_TC('здание')
        elif findall('офис', breadcrumbs[2]):
            return sf.get_TC('офисное помещение')
        elif findall('торговых', breadcrumbs[2]):
            return sf.get_TC('магазин')
        elif findall('свободного', breadcrumbs[2]):
            return sf.get_TC('помещение свободного назначения')

    def __get_phones(self):
        tag_phone = soup.find('a', href=compile('tel:'))
        number = None
        if tag_phone:
            number = re.sub(r'\D', '', tag_phone.text)
            if number.startswith('8') and len(number) == 11:
                number = number.replace('8', '7', 1)
            elif len(number) == 6:
                number = '74212' + number

        return number

    def __get_price(self):
        tag_price = soup.find('span', itemprop='price')
        if tag_price:
            price = tag_price.text.replace('₽', '').replace('\xa0', '').replace(' ', '').replace('/мес.', '').replace('/сут.', '')

            price = int(price) / 1000
            data['ownerPrice'] = price

    def __get_photo_url(self):
        tag_photos = soup.find_all('span', content=compile(r'https://cdn-p\.cian'))
        if tag_photos:
            photo_url = []
            for photo in tag_photos:
                photo_url.append(photo['content'])

            data['photoUrl'] = photo_url

    def __get_balcony(self):
        if info:
            if 'балкон' in info:
                data['balcony'] = True

            if 'лоджия'in info:
                data['loggia'] = True

    def __get_source_media_text(self):
        tag_source_media_text = soup.find('p', class_=compile('description-text'))
        if tag_source_media_text:
            source_media_text = tag_source_media_text.text
            data['description'] = source_media_text

    def __get_rooms_count(self):
        if info:
            if 'количество комнат' in info:
                data['roomsCount'] = int(info['количество комнат'])

    def __get_square(self):
        if info:
            if 'жилая' in info:
                data['squareLiving'] = float(info['жилая'].replace(',', '.').replace(' ', '').replace('м²', '').strip())

            if 'общая' in info:
                data['squareTotal'] = float(info['общая'].replace(',', '.').replace(' ', '').replace('м²', '').strip())

            if 'кухня' in info:
                data['squareKitchen'] = float(info['кухня'].replace(',', '.').replace(' ', '').replace('м²', '').strip())

            if 'комната' in info:
                data['squareLiving'] = float(info['комната'].replace(',', '.').replace(' ', '').replace('м²', '').strip())

            if 'площадь' in info and data['categoryCode'] == 'land':
                if findall('га', info['площадь']):
                    data['squareLandType'] = 'ha'
                elif findall('сот', info['площадь']):
                    data['squareLandType'] = 'ar'

                square = float(info['площадь'].replace(',', '.').replace(' ', '').replace('м²', '').replace('га', '').replace('сот.', '').strip())
                data['squareLand'] = square
                data['squareLandType'] = 'ar'

            if 'площадь' in info and data['categoryCode'] == 'commersial':
                square = info['площадь'].replace(',', '.').replace(' ', '').replace('м²', '').strip()
                if findall('от', square):
                    square = square.replace('от','')
                    square = square.split('до')
                    square = (float(square[0]) + float(square[1])) / 2
                square = float(square)
                data['squareTotal'] = square

            if 'участок' in info:
                if findall('га', info['участок']):
                    data['squareLandType'] = 'ha'
                elif findall('сот', info['участок']):
                    data['squareLandType'] = 'ar'

                square = float(info['участок'].replace(',', '.').replace(' ', '').replace('м²', '').replace('га', '').replace('сот.', '').strip())
                data['squareLand'] = square

    def __get_floor(self):
        if info:
            if 'этаж' in info:
                floor, floors_count = info['этаж'].split('из')
                data['floor'] = int(floor.strip())
                data['floorsCount'] = int(floors_count.strip())

    def __get_condition(self):
        if info:
            if 'ремонт' in info:
                data['condition'] = sf.get_condition(info['ремонт'])

    def __get_house_type(self):
        if info:
            if 'тип дома' in info:
                data['houseType'] = sf.get_house_type(info['тип дома'])

            elif 'материалы стен' in info:
                data['houseType'] = sf.get_house_type(info['материалы стен'])

    def __get_build_year(self):
        if info:
            if 'построен' in info:
                data['buildYear'] = str(info['построен'])

            elif 'год постройки' in info:
                data['buildYear'] = str(info['год постройки'])

    def __get_bathroom(self):
        if info:
            if 'раздельный санузел' in info:
                data['bathroom'] = sf.get_bathroom('раздельный санузел')
            elif 'совмещенный санузел' in info:
                data['bathroom'] = sf.get_bathroom('совмещенный санузел')
            elif 'совмещённый санузел' in info:
                data['bathroom'] = sf.get_bathroom('совмещенный санузел')

    def __mediator_company(self):
        tag_check = soup.find('h2', class_=compile('--title--'))
        if tag_check:
            name = tag_check.text.strip()

            if findall('ID', name):
                return None
            else:
                tag_mc = soup.find('div', class_=compile('--type--'))
                if tag_mc:
                    mc = tag_mc.text.strip()
                    if findall('Агентство', mc):
                        tag_name_mc = soup.find('h2', class_=compile('--title--'))
                        if tag_name_mc:
                            data['mediatorCompany'] = name
                        else:
                            data['mediatorCompany'] = 'Агентство'
                    else:
                        data['mediatorCompany'] = mc

    def __get_rent_fields(self):
        if info:
            if 'холодильник' in info:
                data['refregirator'] = True

            if 'мебель на кухне' in info:
                data['kitchen_furniture'] = True

            if 'мебель в комнатах' in info:
                data['living_room_furniture'] = True

            if 'стиральная машина' in info:
                data['washer'] = True

            if 'телевизор' in info:
                data['tv'] = True

            if 'посудомоечная машина' in info:
                data['dishwasher'] = True

            if 'кондиционер' in info:
                data['air_conditioning'] = True

            if 'можно с детьми' in info:
                data['with_children'] = True

            if 'можно с животными' in info:
                data['with_animals'] = True


# if __name__ == '__main__':
#     cian_url = 'https://habarovsk.cian.ru/sale/suburban/196891515/'
#     X = CianParser()
#     params = {
#             'source': 'cian',
#             'url': cian_url,
#             'ip': '194.67.199.69'
#     }
#
#     pprint(X.get_data(params))
