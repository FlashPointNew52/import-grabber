import requests  # пакет для работы с http (запросы и т.п.)
import time
import datetime
import parsingfunctools as sf
import secrettools as ts
import re

from datetime import timedelta
from bs4 import BeautifulSoup  # пакет для анализа html страниц
from pprint import pprint  # пакет для "красивого" вывода информации в терминал
from re import findall  # пакет для работы с регулярными выражениями

from datetime import datetime  # пакет для определения времени
from requests.exceptions import ProxyError, ConnectionError, Timeout
from certifi import where


class AvitoParser:

    def __get_html(self, params):
        source = params['source']
        url = params['url']
        ip = params['ip']
        attempt = 1  # счетчик попыток
        delay_sec = 0.01  # время задержки (в секундах)
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
                print('except and sleep: ', delay_sec, ' attempt ' , attempt)
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        url = parameters['url']

        html_code = self.__get_html(parameters)  # вызов функции get_html(функция для получения html кода) с параметром в виде url-адреса
        # pprint(html_code)

        global data
        data = {
            'importId': int(time.time() * 100000),
            'sourceMedia': 'avito',
            'sourceUrl': parameters['url'],
            'addDate': None,
            'offerTypeCode': None,
            'typeCode': None,
            'categoryCode': None,
            'phoneBlock': None,
            'buildingType': None,
            'buildingClass': None,
            'newBuilding': None,
            'mortgages' : False
        }  # сформирован dict(словарь), в котором находятся записи в формате ключ:значение

        # обозначение "глобальности" переменных
        global soup
        global breadcrumbs
        global info
        global dop_info

        soup = BeautifulSoup(html_code, 'lxml').find('body')  # создание "дерева кода" для анализа страницы
        breadcrumbs = []  # объявление списка "хлебных крошек"
        tag_breadcrumbs = soup.find_all('a',
                                        class_='js-breadcrumbs-link js-breadcrumbs-link-interaction')  # получение "хлебных крошек"
        for i in tag_breadcrumbs:
            breadcrumbs.append(i.get_text().lower())  # внесение каждой "крошки" в список

        info = self.__get_info()
        dop_info = self.__get_advanced_info()
        # pprint(dop_info)
        # Обязательные поля
        data['addDate'] = self.__get_date()
        data['changeDate'] = data['addDate']
        self.__get_offer_type_code()
        data['typeCode'] = self.__get_type_code()
        data['categoryCode'] = self.__get_category_code()
        # data['phoneBlock'] = { 'main' : self.__get_phones(parameters)}


        # Обязательные поля, но возможны значения по умолчанию

        data['buildingClass'] = self.__get_building_class()
        data['buildingType'] = self.__get_building_type(data['typeCode'])
        data['newBuilding'] = self.__get_type_novelty()
        # data['object_stage'] = self.__get_object_stage()

        # # Прочие поля
        self.__get_price()
        self.__get_mediator_company()
        self.__get_photo_url()
        # self.__get_email()
        self.__get_balcony()
        self.__get_description()
        data['addressBlock'] = self.__get_address(url)
        self.__get_rooms_count()
        self.__get_floor()
        self.__get_square()
        # self.__get_condition()
        self.__get_house_type()

        if data['offerTypeCode'] == 'rent' \
                and data['categoryCode'] == 'rezidential':
            self.__get_rent_fields()

        return data

    def __get_id(self):
        now_date = datetime.today()
        date_create = datetime(now_date.year, now_date.month, now_date.day, now_date.hour,
                               now_date.minute, now_date.second, now_date.microsecond)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_info(self):
        info = {}  # сформирован словарь
        all_info = soup.find_all('li', class_='item-params-list-item')  # поиск всех записей с тегом <li> и определенным классом
        if all_info:
            for unit in all_info:  # достаем по одной записи из всех записей
                unit_str = unit.get_text().lower().replace('\n', '').split(":")  # разбираем и редактируем запись
                key = unit_str[0]  # ключем является определяющее слово (пр. адрес)
                value = unit_str[1].replace(' ', '').replace('\xa0', '')  # значением является информирующее слово (пр. ул.Ленина)
                info[key] = value  # записываем пару в словарь

        else:
            all_info = soup.find('div', class_='item-params')

            all_info = all_info.text.replace('\n', '').replace(' ','').replace('м²','').replace('\xa0', '').split(';')

            for unit in all_info:
                unit_str = unit.lower().split(':')
                key = unit_str[0]
                value = unit_str[1]

                info[key] = value

        return info

    def __get_advanced_info(self):
        dop_info = []
        advanced_info = soup.find_all('li', class_='advanced-params-param-item')
        if advanced_info:
            for item in advanced_info:
                dop_info.append(item.text.lower())

            return dop_info

    def __get_date(self):
        tag_date = soup.find('div',
                             class_='title-info-metadata-item')  # поиск одной записи с тегом <div> и определенным классом

        # pprint(tag_date)
        info_date = tag_date.get_text().replace('\n', '')  # редактируем запись, избавляясь от лишних символов/слов
        # pprint(info_date)

        dmy = findall(r'\w+',info_date)  # используя регулярное выражение получаем список [номер объявления, когда размещена, 'в', часы, минуты]
        hms = findall(r'\w+',info_date)
        now_date = datetime.today()

        date_time = {
            'day': None,
            'month': None,
            'year': None,
            'hour': None,
            'minute': None,
            'second': None
        }  # сформирован словарь

        result = re.findall(r'(\d*) (\w+) в (\d{1,2}):(\d{1,2})', info_date)

        if result[0]:
            if result[0][1] == 'вчера':
                date_time['day'] = int((now_date - timedelta(1)).day)
                date_time['month'] = (now_date - timedelta(1)).month
                date_time['year'] = (now_date - timedelta(1)).year
            elif result[0][1] == 'сегодня':
                date_time['day'] = int(now_date.day)
                date_time['month'] = now_date.month
                date_time['year'] = now_date.year
            else:
                date_time['day'] = int(result[0][0])
                date_time['month'] = sf.get_month(result[0][1])
                date_time['year'] = now_date.year

            if result[0][2]:
                date_time['hour'] = result[0][2]
            else:
                date_time['hour'] = now_date.hour

            if result[0][3]:
                date_time['minute'] = result[0][3]
            else:
                date_time['minute'] = now_date.minute


        date = datetime(int(date_time['year']), int(date_time['month']), int(date_time['day']), int(date_time['hour']), int(date_time['minute']))
        msc_date = date #mediatorCompany- timedelta(hours=7)
        unix_date = int(time.mktime(msc_date.timetuple()))

        return unix_date

    def __get_address(self, url):
        tag_address = soup.find('div', class_='seller-info-label', string='Адрес') # поиск одной записи с тегом <div>, определенным классом и строкой Адрес

        addressBlock = {
            'region': 'Хабаровский край',
            'city': 'г. Хабаровск',
            'admArea': None,
            'area': None,
            'street': None,
            'house': None,
            'housing': None,
            'apartment': None,
            'metro': None,
            'bus_stop': None
        }

        if tag_address:
            tag_address = tag_address.find_next("div")
            address_line = tag_address.get_text().replace('\n', '').strip()
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
                    print("Error in address", item , e)
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
            data['description'] = data['description'] + ' ' + address_line
        return addressBlock

    def __get_mediator_company(self):
        tag_agency = soup.find('div', string='Агентство')
        if tag_agency:
            tag_mediator_company = soup.find('div', class_='seller-info-name')
            if not tag_mediator_company:
                data['mediatorCompany'] = 'Агентство'
            else:
                tag_mediator_company = tag_mediator_company.find_next('a')
                mediator_company = tag_mediator_company.text.strip()
                data['mediatorCompany'] = mediator_company

    def __get_offer_type_code(self):
        # определение типа предложения с помощью "хлебных крошек"
        try:
            if breadcrumbs[4] == 'посуточно':  # если 6-й элемент списка содержит слово 'посуточно' => offer_type_code = short
                data['offerTypeCode'] = 'rent'
                data['rentType'] = 'short'
            elif breadcrumbs[4] == 'на длительный срок':  # если 6-й элемент списка содержит слово 'посуточно' => offer_type_code = short
                data['offerTypeCode'] = 'rent'
                data['rentType'] = 'long'
            elif breadcrumbs[5] == 'на длительный срок':  # если 6-й элемент списка содержит слово 'посуточно' => offer_type_code = short
                data['offerTypeCode'] = 'rent'
                data['rentType'] = 'long'
            elif breadcrumbs[5] == 'посуточно':  # если 6-й элемент списка содержит слово 'посуточно' => offer_type_code = short
                data['offerTypeCode'] = 'rent'
                data['rentType'] = 'short'
            else:  # иначе offer_type_code равен 4-му элементу списка (продам/сдам)
                offer_type = breadcrumbs[3]
                data['offerTypeCode'] = sf.get_OTC(offer_type)

        except IndexError:
            offer_type = breadcrumbs[3]
            data['offerTypeCode'] = sf.get_OTC(offer_type)

    def __get_category_code(self):
        # определение типа категории недвижимости с помощью "хлебных крошек"
        category = breadcrumbs[2]

        if category == 'дома, дачи, коттеджи':
            category = breadcrumbs[4]

        return sf.get_CC(category)

    def __get_building_class(self):
        if breadcrumbs[2] == 'коммерческая недвижимость':
            if 'классздания' in info:
                return sf.get_BC(info['классздания'])
            else:
                return sf.get_BC('а')

        elif breadcrumbs[2] == 'земельные участки':
            return None

        elif breadcrumbs[2] == 'комнаты' or breadcrumbs[2] == 'квартиры':
            return sf.get_BC('экономкласс')

        elif breadcrumbs[2] == 'дома, дачи, коттеджи':
            return sf.get_BC(breadcrumbs[4])

    def __get_building_type(self, type_code):
        return sf.get_BT(type_code)

    def __get_type_code(self):
        if breadcrumbs[2] == 'комнаты':
            return sf.get_TC(breadcrumbs[2])
        elif breadcrumbs[2] == 'квартиры':
            return sf.get_TC(breadcrumbs[2])
        elif breadcrumbs[2] == 'дома, дачи, коттеджи':
            return sf.get_TC(breadcrumbs[4])
        elif breadcrumbs[2] == 'коммерческая недвижимость':
            return sf.get_TC(breadcrumbs[4])
        elif breadcrumbs[2] == 'земельные участки':
            return sf.get_TC('дачныйземельныйучасток')

    def __get_phones(self, params):
        params['url'] = params['url'].replace('www', 'm')  # изменяем url с "компьютерной" версии, на мобильную версию
        tag_numbers = None
        while tag_numbers is None:  # "крутить" цикл, пока не поймана запись с заданным атрибутом
            mobile_html_code = self.__get_html(params)  # получение html кода мобильной версии сайта
            mobile_soup = BeautifulSoup(mobile_html_code, 'lxml')  # создание "дерева кода" для анализа страницы
            tag_numbers = mobile_soup.find(
                attrs={'data-marker': 'item-contact-bar/call'})  # поиск записи с определенным аттрибутом
        number = re.sub(r'\D', '', tag_numbers['href']) #удаляем из номера все символы кроме цифер
        if number.startswith('8') and len(number) == 11:
            number = number.replace('8', '7', 1)
        elif len(number) == 6:
            number = '74212' + number
        return number

    def __get_type_novelty(self):
        try:
            if breadcrumbs[5] == 'новостройки':
                return True
            else:
                return False
        except IndexError:
            return False

    def __get_price(self):
        tag_price = soup.find('span', class_='js-item-price')
        if tag_price:
            price = float(tag_price.text.replace(' ', '')) / 1000

            data['ownerPrice'] = price

        else:
            return None

    def __get_photo_url(self):
        tag_photos = soup.find_all('div', class_='gallery-extended-img-frame')
        if tag_photos:
            photos = []

            for photo_url in tag_photos:
                photos.append('https:' + photo_url['data-url'])

            data['photoUrl'] = photos

        else:
            return None

    def __get_description(self):
        tag_description = soup.find('div', itemprop='description')
        if tag_description:
            data['description'] = tag_description.text.replace('\n', '').replace('\xa0', '').replace("\"", "'")
        else:
            return None

    def __get_floor(self):
        if 'этажей в доме' in info:
            data['floorsCount'] = int(info['этажей в доме'])

        if 'этаж' in info:
            data['floor'] = int(info['этаж'])

        else:
            return None

    def __get_rooms_count(self):
        if 'количество комнат' in info:
            if info['количество комнат'] == 'студии':
                data['roomsCount'] = 1
                data['roomsScheme'] = sf.get_room_scheme(info['количество комнат'])

            else:
                rooms = int(info['количество комнат'].replace('-комнатные',''))
                data['roomsCount'] = rooms

        else:
            return None

    def __get_house_type(self):
        if 'тип дома' in info:
            data['houseType'] = sf.get_house_type(info['тип дома'])

        elif 'материал стен' in info and data['categoryCode'] == 'land':
            data['houseType'] = sf.get_house_type(info['материал стен'])

        else:
            return None

    def __get_square(self):
        if 'общая площадь' in info:
            data['squareTotal'] = float(info['общая площадь'].replace('м²',''))

        if 'площадь кухни' in info:
            data['squareKitchen'] = float(info['площадь кухни'].replace('м²',''))

        if 'жилая площадь' in info:
            data['squareLiving'] = float(info['жилая площадь'].replace('м²',''))

        if 'площадь комнаты' in info and breadcrumbs[2] == 'комнаты':
            data['squareLiving'] = float(info['площадь комнаты'].replace('м²',''))

        if ('площадь' in info or 'площадь участка' in info) and data['categoryCode'] == 'land':
            try:
                square = float(info['площадь'].replace('сот.', ''))
            except KeyError:
                square = float(info['площадь участка'].replace('сот.', ''))

            data['squareLand'] = square
            data['squareLandType'] = 'ar'

        if 'площадь дома' in info and data['categoryCode'] == 'land':
            data['squareTotal'] = float(info['площадь дома'].replace('м²', ''))

        if 'площадь' in info and data['categoryCode'] == 'commersial':
            square = float(info['площадь'].replace('м²',''))
            data['squareTotal'] = square

    def __get_balcony(self):
        if dop_info:
            for item in dop_info:
                if findall('балкон', item):
                    data['balcony'] = True

                if findall('лоджия', item):
                    data['loggia'] = True

    def __get_other_fields(self):
        if 'расстояние до города' in info:
            try:
                distance = int(info['расстояние до города'])
                data['distance'] = str(distance).replace('км', '').rstrip() + ' км'
            except ValueError:
                return None

    def __get_rent_fields(self):
        if dop_info:
            for item in dop_info:
                if findall('телевизор', item):
                    data['tv'] = True
                if findall('холодильник', item):
                    data['refrigerator'] = True
                if findall('стиральная', item):
                    data['washer'] = True
                if findall('кондиционер', item):
                    data['air_conditioning'] = True
                if findall('микроволновка', item):
                    data['microwave_oven'] = True
                if findall('можно с детьми', item):
                    data['with_children'] = True
                if findall('можно с животными', item):
                    data['with_animals'] = True
                if findall('можно с животными', item):
                    data['with_animals'] = True


# if __name__ == '__main__':  # НАЧАЛО ТУТ)
#     avito_url = 'https://www.avito.ru/habarovsk/kommercheskaya_nedvizhimost/stolovaya_kafe_ili_tseh_80_m_707657579'
#     X = AvitoParser()
#     params = {
#             'source': 'avito',
#             'url': avito_url,
#             'ip': '193.124.180.185'
#     }
#     pprint(X.get_data(params))
