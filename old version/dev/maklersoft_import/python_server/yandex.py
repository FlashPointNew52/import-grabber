import requests
import time
import datetime
import parsingfunctools as sf
import secrettools as ts


from bs4 import BeautifulSoup
from pprint import pprint
from re import findall, compile
from datetime import datetime, timedelta
from requests.exceptions import ProxyError, ConnectionError, Timeout
from certifi import where


class YandexParser:

    def __get_html(self, params):

        url = params['url']
        ip = params['ip']
        source = params['source']
        attempt = 1
        delay_sec = 0.5
        while attempt <= 10:
            proxy = ts.set_proxy()
            pprint(proxy)
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
                    # time.sleep(delay_sec)
            except (ProxyError, ConnectionError, Timeout):
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        html_code = self.__get_html(parameters)

        global data

        data = {
            'importId': int(time.time() * 100000),
            'source_media': 'yandex',
            'source_url': parameters['url'],
            'add_date': None,
            'offer_type_code': None,
            'type_code': None,
            'category_code': None,
            'phones_import': None,
            'locality': 'г. Хабаровск',
            'address': None,

            'building_type': None,
            'building_class': None,
            'new_building': False,
        }

        global soup
        global breadcrumbs

        soup = BeautifulSoup(html_code, 'lxml')

        breadcrumbs = []
        tag_breadcrumbs = soup.find('div', class_='breadcrumbs-list breadcrumbs-list_type_search breadcrumbs-list_in-card_yes')
        if tag_breadcrumbs:
            tag_breadcrumbs = tag_breadcrumbs.find_all('a')
            for item in tag_breadcrumbs:
                breadcrumbs.append(self.__decode_text(item.text).lower())

        if not breadcrumbs:
            exit()

        # Обязательные поля
        data['add_date'] = self.__get_date()
        data['offer_type_code'] = self.__get_offer_type_code()
        data['type_code'] = self.__get_type_code()
        data['category_code'] = self.__get_category_code()
        data['phones_import'] = self.__get_phones()
        data['address'] = self.__get_address()
        # data['locality'] = self.__get_locality()

        # # Обязательные поля, но возможны значения по умолчанию
        global info
        info = self.__get_info()
        data['building_class'] = self.__get_building_class()
        data['building_type'] = self.__get_building_type()
        # data['new_building'] = self.__get_type_novelty()
        # # data['object_stage'] = self.__get_object_stage()


        # # Прочие поля
        self.__get_price()
        self.__get_photo_url()
        # self.__get_email()
        self.__get_balcony()
        self.__get_description()
        self.__get_mediator_company()
        self.__get_rooms_count()
        self.__get_floor()
        self.__get_square()
        self.__get_condition()
        self.__get_build_year()
        self.__get_house_type()
        # self.__get_rooms_scheme()
        if data['offer_type_code'] == 'rent' \
                and data['category_code'] == 'rezidential':
            self.__get_rent_fields()

        return data

    def __decode_text(self, text):
        return text.encode('latin1').decode(encoding='UTF-8',errors='ignore')

    def __get_info(self):
        information = {}
        tag_main_info = soup.find_all('div', class_="offer-card__main-feature")
        if tag_main_info:
            for item in tag_main_info:
                key = self.__decode_text(item.find('div', class_=compile('offer-card__main-feature-note')).text).lower()
                value = self.__decode_text(item.find('div', class_=compile('offer-card__main-feature-title')).text).replace('м²', '').lower()
                if key:
                    information[key] = value

        tag_dop_info = soup.find_all('div', class_=compile('offer-card__feature offer-card__feature_name_'))
        if tag_dop_info:
            for item in tag_dop_info:
                key = self.__decode_text(item.find('div', class_=compile('offer-card__feature-name')).text).lower()
                value = self.__decode_text(item.find('div', class_=compile('offer-card__feature-value')).text).replace('м²', '').lower()
                if key:
                    information[key] = value

        if data['category_code'] == 'commersial':
            tag_commers_info = soup.find('div', class_=compile('offer-card__features offer-card__features_product_commercial'))
            if tag_commers_info:
                tag_info = tag_commers_info.find_all('div', class_='offer-card__feature')
                for item in tag_info:
                    key = self.__decode_text(item.find('div', class_='offer-card__feature-name').text).lower()
                    value = self.__decode_text(item.find('div', class_='offer-card__feature-value').text).lower()
                    if key:
                        information[key] = value

        return information

    def __get_id(self):
        date_create = datetime(datetime.now().year,
                               datetime.now().month,
                               datetime.now().day,
                               datetime.now().hour,
                               datetime.now().minute,
                               datetime.now().second,
                               datetime.now().microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_date(self):
        tag_date = soup.find('div', class_=compile('offer-card__lot-date'))
        if tag_date:
            raw_date = self.__decode_text(tag_date.text)

            date_time = {
                'day': None,
                'month': None,
                'year': None,
                'hour': '12',
                'minute': '00',
                'second': '00'
            }

            mass_date = raw_date.split()

            now_date = datetime.now()

            if len(mass_date) == 2:
                date_time['day'] = mass_date[0]
                date_time['month'] = sf.get_month(mass_date[1])
                date_time['year'] = now_date.year

            elif len(mass_date) == 3:
                my_date = now_date - timedelta(hours=int(mass_date[0]))
                date_time['day'] = my_date.day
                date_time['month'] = my_date.month
                date_time['year'] = my_date.year
                date_time['hour'] = my_date.hour

            elif len(mass_date) == 1:
                my_date = now_date - timedelta(days=1)
                date_time['day'] = my_date.day
                date_time['month'] = my_date.month
                date_time['year'] = my_date.year
                date_time['hour'] = my_date.hour

            date = datetime(int(date_time['year']),
                            int(date_time['month']),
                            int(date_time['day']),
                            int(date_time['hour']),
                            int(date_time['minute']))

            msc_date = date - timedelta(hours=7)
            unix_date = int(time.mktime(msc_date.timetuple()))

            data['change_date'] = unix_date

            return unix_date

    def __get_address(self):
        tag_address = soup.find('h2', class_=compile('offer-card__address'))
        if tag_address:
            full_address = self.__decode_text(tag_address.text)
            raw_address = full_address.split(',')
            city, address = raw_address[0].strip(), ','.join(raw_address[1:]).strip()
            data['locality'] = 'г. ' + city
            return address

    def __get_type_novelty(self):
        pass

    def __get_offer_type_code(self):
        if breadcrumbs:
            if breadcrumbs[3] == 'продажа':
                return 'sale'
            if breadcrumbs[3] == 'аренда':
                data['rent_type'] = 'long'
                return 'rent'

    def __get_category_code(self):
        if breadcrumbs:
            if findall('участок', breadcrumbs[4]):
                return 'land'
            elif findall('коммерч', breadcrumbs[4]):
                return 'commersial'
            elif findall('квартир', breadcrumbs[4]) or findall('комнат', breadcrumbs[4]) or findall('дом', breadcrumbs[4]):
                return 'rezidential'
            else:
                return 'commersial'

    def __get_building_type(self):
        if data['type_code']:
            return sf.get_BT(data['type_code'])

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

    def __get_type_code(self):
        if breadcrumbs:
            if 'квартира' in breadcrumbs:
                return sf.get_TC('квартира')

            elif 'комната' in breadcrumbs:
                return sf.get_TC('комната')

            elif 'участок' in breadcrumbs:
                return sf.get_TC('участок')

            elif 'дом' in breadcrumbs:
                tag_title = soup.find('h1', class_=compile('offer-card__header-text'))
                if tag_title:
                    title = self.__decode_text(tag_title.text).lower()
                    if findall('части', title) or findall('часть', title):
                        return sf.get_TC('доля')
                    elif findall('дуплекс', title):
                        return sf.get_TC('дуплекс')
                    elif findall('таунхаус', title):
                        return sf.get_TC('таунхаус')
                    else:
                        return sf.get_TC('дом')

            elif 'коммерческая недвижимость' in breadcrumbs:
                if 'офис' in breadcrumbs:
                    return sf.get_TC('офисное помещение')

                elif 'торговое помещение' in breadcrumbs:
                    return sf.get_TC('торговое помещение')

                elif 'помещение свободного назначения' in breadcrumbs:
                    return sf.get_TC('помещение свободного назначения')

                elif 'склад' in breadcrumbs:
                    return sf.get_TC('склад')

                elif 'производственное помещение' in breadcrumbs:
                    return sf.get_TC('производственное помещение')

                elif 'производственное помещение' in breadcrumbs:
                    return sf.get_TC('производственное помещение')

                else:
                    return sf.get_TC('другое')

            else:
                return None

    def __get_phones(self):
        tag_phone = soup.find('div', class_=compile('phones__redirect'))
        pprint(tag_phone)
        if tag_phone:
            phones = []
            numbers = findall(r'\+7\d{10}', tag_phone['data-bem'])
            for number in numbers:
                phones.append(number)

            return phones

    def __get_price(self):
        tag_price = soup.find('h3', class_=compile('offer-price offer-card__price offer-card__price'))
        if tag_price:
            raw_price = self.__decode_text(tag_price.text)
            if findall('млн', raw_price):
                cost, postfix = raw_price.split('млн')
                cost = cost.replace('\xa0', '').replace(' ', '')
                if cost.find(',') >= 1:
                    first_part, second_part = cost.split(',')
                    while len(second_part) != 6:
                        second_part += '0'
                    cost = float(first_part + second_part)
                elif cost.find(',') == -1:
                    cost += '000000'
                    cost = float(cost)

            elif findall('месяц', raw_price) or findall('сутки', raw_price):
                cost, postfix = raw_price.split('₽')
                cost = float(cost.replace(' ', '').replace('\xa0', ''))
                if findall('сутки', raw_price):
                    data['rent_type'] = 'short'
            else:
                cost = float(raw_price.replace('₽', '').replace(' ', '').replace('\xa0', ''))

            cost = cost / 1000
            data['price'] = cost

    def __get_photo_url(self):
        tag_photos = soup.find_all('a', class_=compile('offer-card__react-gallery-photo'))
        if tag_photos:
            photos = []
            for photo in tag_photos:
                photo = 'https:' + photo['href']
                photos.append(photo)

            data['photo_url'] = photos

    def __get_bathroom_type(self):
        if 'санузел' in info:
            data['condition'] = sf.get_bathroom(info['санузел'])

    def __get_balcony(self):
        if 'балкон' in info:
            balcony = info['балкон']
            if findall('да', balcony):
                data['balcony'] = True

            if findall('лоджия', balcony):
                data['loggia'] = True

    def __get_description(self):
        tag_description = soup.find('div', class_='offer-card__desc-text')
        if tag_description:
            data['description'] = self.__decode_text(tag_description.text)

    def __get_rooms_count(self):
        if 'количество комнат' in info:
            data['rooms_count'] = info['количество комнат']
        else:
            tag_rooms_count = soup.find_all('div', class_="offer-card__main-feature")
            if tag_rooms_count:
                for item in tag_rooms_count:
                    key = self.__decode_text(
                        item.find('div', class_=compile('offer-card__main-feature-note')).text).lower()
                    value = self.__decode_text(
                        item.find('div', class_=compile('offer-card__main-feature-title')).text).lower()
                    if not key:
                        if findall('комнат',  value):
                            data['rooms_count'] = int(value.split()[0])
                            break
            else:
                return None

    def __get_rooms_scheme(self):
        pass

    def __get_floor(self):
        if 'этаж' in info:
            floor, floors_count = info['этаж'].split('из')
            data['floor'] = int(floor.strip())
            data['floors_count'] = int(floors_count.strip())
        else:
            tag_floor = soup.find_all('div', class_="offer-card__main-feature")
            if tag_floor:
                for item in tag_floor:
                    key = self.__decode_text(
                        item.find('div', class_=compile('offer-card__main-feature-note')).text).lower()
                    value = self.__decode_text(
                        item.find('div', class_=compile('offer-card__main-feature-title')).text).lower()
                    if findall('в здании', key):
                        if findall('этаж',  value):
                            data['floor'] = int(value.replace(' этаж', '').strip())

                        data['floors_count'] = int(key.replace('из', '').replace(' в здании', '').strip())
                        break
            else:
                return None

    def __get_square(self):
        if 'общая' in info and data['category_code'] == 'land':
            data['square_total'] = float(info['общая'].replace(',', '.').replace('сотки', '').strip())
            data['square_land_type'] = 'ar'

        elif 'общая' in info:
            data['square_total'] = float(info['общая'].strip().replace(',', '.'))

        elif 'общая' in info and data['type_code'] == 'room':
            data['square_living'] = float(info['общая'].strip().replace(',', '.'))

        if 'общая площадь' in info:
            data['square_total'] = float(info['общая площадь'].strip().replace(',', '.'))

        elif 'общая площадь' in info and data['type_code'] == 'room':
            data['square_living'] = float(info['общая площадь'].strip().replace(',', '.'))

        if 'кухня' in info:
            data['square_kitchen'] = float(info['кухня'].strip().replace(',', '.'))

        if 'жилая' in info:
            data['square_living'] = float(info['жилая'].strip().replace(',', '.'))

        if 'площадь участка' in info:
            area = info['площадь участка'].split()
            area_value, area_type = area
            data['square_land'] = float(area_value.strip().replace(',', '.'))
            if findall('сот', area_type):
                data['square_land_type'] = 'ar'
            elif findall('гек', area_type):
                data['square_land_type'] = 'ha'
            else:
                data['square_land_type'] = 'ar'

    def __get_condition(self):
        if 'отделка' in info:
            data['condition'] = sf.get_condition(info['отделка'])

    def __get_house_type(self):
        if 'тип здания' in info:
            data['house_type'] = sf.get_house_type(info['тип здания'])

    def __get_mediator_company(self):
        tag_mc = soup.find('div', class_=compile('offer-card__author-note'))
        if tag_mc:
            mc = self.__decode_text(tag_mc.text)
            if findall('агентство', mc):
                tag_name_company = soup.find('div', class_=compile('offer-card__author-name ellipsis'))
                if tag_name_company:
                    data['mediator_company'] = self.__decode_text(tag_name_company.text)
                else:
                    data['mediator_company'] = 'Агентство'
            else:
                return None

    def __get_build_year(self):
        if 'год постройки' in info:
            data['build_year'] = info['год постройки']
        if 'год постройки дома' in info:
            data['build_year'] = info['год постройки дома']
        if 'год постройки здания' in info:
            data['build_year'] = info['год постройки здания']

    def __get_rent_fields(self):
        if 'телевизор' in info:
            if info['телевизор'] == 'есть':
                data['tv'] = True

        if 'стиральная машина' in info:
            if info['стиральная машина'] == 'есть':
                data['washer'] = True

        if 'холодильник' in info:
            if info['холодильник'] == 'есть':
                data['refrigerator'] = True

        if 'мебель на кухне' in info:
            if info['мебель на кухне'] == 'есть':
                data['kitchen_furniture'] = True

        if 'мебель' in info:
            if info['мебель'] == 'есть':
                data['living_room_furniture'] = True

        if 'кондиционер' in info:
            if info['кондиционер'] == 'есть':
                data['air_conditioning'] = True

        if 'посудомойка' in info:
            if info['посудомойка'] == 'есть':
                data['dishwasher'] = True

        if 'посудомойка' in info:
            if info['посудомойка'] == 'есть':
                data['dishwasher'] = True

        if 'посудомойка' in info:
            if info['посудомойка'] == 'есть':
                data['dishwasher'] = True

        tag_rent_info = soup.find('div', class_=compile('offer-card__terms'))
        if tag_rent_info:
            rent_info = self.__decode_text(tag_rent_info.text)
            rent_info = rent_info.split(',')

            for item in rent_info:
                item = item.lower().strip()
                if item == 'ку включены':
                    data['water_pay'] = True
                    data['gas_pay'] = True
                    data['electrific_pay'] = True

                if findall('предоплата', item):
                    data['prepayment'] = True


# if __name__ == '__main__':
#     url = 'https://realty.yandex.ru/offer/7055983979765059073/'
#     params = {
#         'url': url,
#         'source': 'yandex',
#         'ip': '193.124.180.185'
#     }
#     X = YandexParser()
#     pprint(X.get_data(params))
