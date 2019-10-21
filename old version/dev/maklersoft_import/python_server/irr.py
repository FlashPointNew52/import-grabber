import requests
import time
import parsingfunctools as sf
import secrettools as ts

from certifi import where
from pybase64 import b64decode
from bs4 import BeautifulSoup
from pprint import pprint
from re import findall, compile
from datetime import datetime, timedelta
from requests.exceptions import ProxyError, ConnectionError, Timeout


class IrrParser:

    def __get_html(self, params):
        source = params['source']
        url = params['url']
        ip = params['ip']
        attempt = 1
        delay_sec = 1
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
                    time.sleep(delay_sec)
            except (ProxyError, ConnectionError, Timeout):
                time.sleep(delay_sec)
                continue
        exit()

    def get_data(self, parameters):
        html_code = self.__get_html(parameters)

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
            'new_building': None,
        }

        global soup
        global breadcrumbs
        global info

        soup = BeautifulSoup(html_code, 'lxml').find('body')
        breadcrumbs = []
        tag_breadcrumbs = soup.find_all('li',
                                        itemprop=compile('itemListElement'))
        if tag_breadcrumbs:
            for item in tag_breadcrumbs:
                item = item.find('span', itemprop='name')
                breadcrumbs.append(item.text.strip().lower())
        else:
            exit()

        info = self.__get_info()
        # Обязательные поля
        data['add_date'] = self.__get_date()
        self.__get_offer_type_code()
        self.__get_locality()
        data['category_code'] = self.__get_category_code()
        data['type_code'] = self.__get_type_code()
        data['phones_import'] = self.__get_phones()
        data['address'] = self.__get_address()

        # Обязательные поля, но возможны значения по умолчанию
        data['building_class'] = self.__get_building_class()
        data['building_type'] = self.__get_building_type()
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
        tag_information = soup.find_all('li',
                                        class_=compile('infoColumnBlockText'))
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
        tag_date = soup.find('div', class_=compile('createDate'))
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
                date_time['month'] = sf.get_month(month)
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
                    date_time['month'] = sf.get_month(month)

            date = datetime(int(date_time['year']), int(date_time['month']),
                            int(date_time['day']), int(date_time['hour']),
                            int(date_time['minute']))

            msc_date = date - timedelta(hours=7)
            unix_date = int(time.mktime(msc_date.timetuple()))

            data['change_date'] = unix_date

            return unix_date

    def __get_address(self):
        address = ''
        tag_address = soup.find('div', class_=compile(
            'productPage__infoTextBold js-scrollToMap'))
        if tag_address:
            raw_address = tag_address.text.replace('\n', '').replace('\t',
                                                                     '').strip()
            raw_address = raw_address.split(',')
            if len(raw_address) == 2:
                town, street = raw_address
                street = street.title()
                address += street

            elif len(raw_address) == 3:
                town, street, number_house = raw_address
                address += street + ',' + number_house

            return address

        else:
            if 'улица' in info:
                address += 'ул.' + info['улица'].replace('ул', '').title()
            if 'дом' in info:
                address += info['дом']

            return address

    def __get_mediator_company(self):
        tag_mediator_company = soup.find('div', class_=compile('productPage__infoTextBold_inline'))
        if tag_mediator_company:
            mediator_company = tag_mediator_company.text
            if findall('собствен', mediator_company):
                return
            else:
                data['mediator_company'] = mediator_company.replace('\n', '').replace('\t', '').strip()

    def __get_offer_type_code(self):
        if findall('продажа', breadcrumbs[2]):
            data['offer_type_code'] = 'sale'
        elif findall('аренда', breadcrumbs[2]):
            data['offer_type_code'] = 'rent'
            data['rent_type'] = 'long'
            if 'краткосрочная аренда' in info:
                data['rent_type'] = 'short'

    def __get_locality(self):
        tag_city = soup.find('div', class_=compile('productPage__infoTextBold js-scrollToMap'))

        if tag_city:
            full_address = tag_city.text.strip()
            raw_city = full_address.split(',')
            city = 'г. ' + raw_city[0]

            data['locality'] = city

    def __get_category_code(self):
        if findall('квартир', breadcrumbs[2]) or findall('комнат', breadcrumbs[2]):
            return sf.get_CC('жилая')
        elif findall('дома', breadcrumbs[3]) or findall('таунхаусы', breadcrumbs[3]):
            return sf.get_CC('жилая')
        elif findall('коммерческ', breadcrumbs[2]):
            return sf.get_CC('коммерческая')
        elif findall('участки', breadcrumbs[3]) or findall('дачи', breadcrumbs[3]):
            return sf.get_CC('участкиидачи')

    def __get_building_class(self):
        if data['category_code'] == 'rezidential':
            if 'общежитие' in info:
                return sf.get_BC('общежитие')
            else:
                return sf.get_BC(data['type_code'])

        elif data['category_code'] == 'commersial':
            if 'класс' in info:
                return sf.get_BC(info['класс'].lower())
            else:
                return sf.get_BC('a')

        elif data['category_code'] == 'land':
            return None

    def __get_building_type(self):
        return sf.get_BT(data['type_code'])

    def __get_type_code(self):
        if data['category_code'] == 'rezidential':
            if findall('квартир', breadcrumbs[2]):
                if findall('студии', breadcrumbs[2]):
                    data['room_scheme'] = 'studio'
                return sf.get_TC('квартира')

            elif findall('долей', breadcrumbs[2]):
                if 'доля' in info:
                    return sf.get_TC('доля')

                count_room_sale = 0
                all_count_room = 0
                if 'количество комнат на продажу' in info:
                    count_room_sale = int(info['количество комнат на продажу'])
                if 'всего комнат в квартире' in info:
                    all_count_room = int(info['всего комнат в квартире'])
                if all_count_room > count_room_sale:
                    return sf.get_TC('доля')

                return sf.get_TC('комната')

            elif findall('комнат', breadcrumbs[2]):
                return sf.get_TC('комната')

            elif findall('дома', breadcrumbs[3]):
                return sf.get_TC('дом')

            elif findall('таунхаусы', breadcrumbs[3]):
                return sf.get_TC('таунхаус')

        elif data['category_code'] == 'commersial':
            if findall('свободного назначения', breadcrumbs[3]):
                return sf.get_TC('другое')
            elif findall('офис', breadcrumbs[3]):
                if 'тип здания' in info:
                    if findall('офисное здание', info['тип здания']):
                        return sf.get_TC('производственное помещение')
                    elif findall('бизнес', info['тип здания']):
                        return sf.get_TC('бизнес-центр')
                    elif findall('офисное здание', info['тип здания']):
                        return sf.get_TC('офисное здание')
                    else:
                        return sf.get_TC('офисное помещение')
                else:
                    return sf.get_TC('офисное помещение')
            elif findall('склады', breadcrumbs[3]):
                if 'назначение помещения' in info:
                    if findall('производство', info['назначение помещения']):
                        return sf.get_TC('производственное помещение')

                    elif findall('склад', info['назначение помещения']):
                        return sf.get_TC('склад')
                    else:
                        return sf.get_TC('склад')
                else:
                    return sf.get_TC('склад')

            elif findall('здания', breadcrumbs[3]):
                return sf.get_TC('здание')

            elif findall('торговля', breadcrumbs[3]):
                if 'назначение помещения' in info:
                    if findall('бытовое', info['назначение помещения']):
                        return sf.get_TC('магазин')

                    elif findall('торговое', info['назначение помещения']):
                        return sf.get_TC('торговое помещение')

                    elif findall('торговый центр', info['тип здания']):
                        return sf.get_TC('торговый центр')

                    elif findall('торгово-развлекательный центр', info['тип здания']):
                        return sf.get_TC('тогово-развлекательный центр')

                    else:
                        return sf.get_TC('магазин')
                else:
                    return sf.get_TC('магазин')

            elif findall('кафе', breadcrumbs[3]):
                return sf.get_TC('кафе')

            else:
                return sf.get_TC('другое')

        elif data['category_code'] == 'land':
            if findall('участки', breadcrumbs[3]):
                return sf.get_TC('участок')
            elif findall('дачи', breadcrumbs[3]):
                return sf.get_TC('дачи')

    def __get_phones(self):
        tag_phone = soup.find('input',
                              attrs={'name': 'phoneBase64', 'type': 'hidden'})
        if tag_phone:
            phones = []
            phone = b64decode(tag_phone['value'])
            phone = phone.decode("utf-8").replace('(', '').replace(')','').replace(' ', '').replace('-', '')
            phones.append(phone)

            return phones

    def __get_type_novelty(self):
        if data['source_url']:
            url = data['source_url']
            parts_url = url.split('/')
            if 'new' in parts_url:
                data['new_building'] = True
                if 'этап строительства' in info:
                    if findall('сдан', info['этап строительства']):
                        data['object_stage'] = 'ready'
                    elif findall('этап', info['этап строительства']):
                        data['object_stage'] = 'building'
                    else:
                        data['object_stage'] = 'ready'
                elif 'год постройки/сдачи' in info:
                    year = int(findall(r'\d{4}', info['год постройки/сдачи'])[0])
                    current_year = datetime.now().year
                    if year > current_year:
                        data['object_stage'] = 'building'
                    elif year <= current_year:
                        data['object_stage'] = 'ready'
                else:
                    data['object_stage'] = 'ready'
            else:
                data['new_building'] = False


    def __get_price(self):
        tag_price = soup.find('div', class_=compile('js-contentPrice'))
        if tag_price:
            price = float(tag_price['content']) / 1000

            data['price'] = price

    def __get_photo_url(self):
        tag_photos = soup.find('div', class_=compile(
            'lineGallery js-lineProductGallery'))
        if tag_photos:
            tag_photos = tag_photos.find_all('img')
            photos = []
            for photo in tag_photos:
                photos.append(photo['data-src'])

            data['photo_url'] = photos

    def __get_description(self):
        tag_description = soup.find('p', class_=compile('descriptionText'))
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
            data['floors_count'] = int(info['этажей в здании'])

    def __get_rooms_count(self):
        if 'комнат в квартире' in info:
            data['rooms_count'] = int(info['комнат в квартире'])

    def __get_house_type(self):
        if 'материал стен' in info:
            data['house_type'] = sf.get_house_type(info['материал стен'])

    def __get_build_year(self):
        if 'год постройки' in info:
            data['build_year'] = str(info['год постройки'])

    def __get_square(self):
        if data['category_code'] == 'rezidential':
            if 'общая площадь' in info:
                data['square_total'] = float(info['общая площадь'])
            if 'жилая площадь' in info:
                data['square_living'] = float(info['жилая площадь'])
            if 'площадь кухни' in info:
                data['square_kitchen'] = float(info['площадь кухни'])
            if 'площадь арендуемой комнаты' in info:
                data['square_living'] = float(info['площадь арендуемой комнаты'])

            if data['type_code'] == 'share' or data['type_code'] == 'room':
                sale_square = 0
                all_square = 0
                if 'площадь продажи' in info:
                    sale_square = float(info['площадь продажи'])
                if 'общая площадь квартиры' in info:
                    all_square = float(info['общая площадь квартиры'])

                if sale_square < all_square:
                    data['square_living'] = sale_square
                    data['square_total'] = all_square
                elif sale_square != 0:
                    data['square_living'] = sale_square

        elif data['category_code'] == 'commersial':
            if 'общая площадь' in info:
                data['square_total'] = float(info['общая площадь'])

        elif data['category_code'] == 'land':
            if 'площадь участка' in info:
                square = info['площадь участка'].split()
                data['square_land'] = float(square[0])
                data['square_land_type'] = 'ar'
                if square[1] != 'сот':
                    data['square_land_type'] = 'ha'

            if 'площадь строения' in info:
                data['square_total'] = float(info['площадь строения'])

    def __get_condition(self):
        if 'ремонт' in info:
            data['condition'] = sf.get_condition(info['ремонт'])

    def __get_balcony(self):
        if 'балкон/лоджия' in info:
            data['loggia'] = True
            data['balcony'] = True

    def __get_bathroom(self):
        if 'санузел' in info:
            data['bathroom'] = sf.get_bathroom(info['санузел'])

    def __get_rent_fields(self):
        if 'бытовая техника' in info:
            data['refregirator'] = True
            # data['kitchen_furniture'] = True
            # data['living_room_furniture'] = True
            data['washer'] = True
            data['dishwasher'] = True
            data['tv'] = True
            data['air_conditioning'] = True

        if 'можно с детьми' in info:
            data['with_children'] = True

        if 'можно с животными' in info:
            data['with_animals'] = True


if __name__ == '__main__':
    irr_url = 'https://khabarovsk.irr.ru/real-estate/apartments-sale/secondary/4-komn-kvartira-lermontova-ul-advert704617154.html'
    X = IrrParser()
    params = {
        'source': 'irr',
        'url': irr_url,
        'ip': '193.124.182.208'
    }
    pprint(X.get_data(params))
