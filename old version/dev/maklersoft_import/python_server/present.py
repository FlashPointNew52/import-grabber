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


class PresentParser:

    def __get_html(self, params):
        url = params['url']
        source = params['source']
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
            'sourceMedia': 'present_site',
            'sourceUrl': parameters['url'],
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
            'mortgages' : False
        }

        global soup
        global breadcrumbs
        global info
        soup = BeautifulSoup(html_code, 'lxml').find('body')

        tag_breadcrumbs = soup.find('div', class_='breadcrumbs')
        breadcrumbs = tag_breadcrumbs.get_text().lower().replace(' ', '').replace('\n', '').split("»")

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
            self.__get_rent_fields()

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
        dmy = findall(r'\w+', info_date)
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
            date_time['month'] = sf.get_month(dmy[1])
            date_time['year'] = dmy[2]
            date_time['hour'] = now_date.hour
            date_time['minute'] = now_date.minute

        date = datetime(int(date_time['year']), int(date_time['month']), int(date_time['day']), date_time['hour'],
                        int(date_time['minute']))
        msc_date = date - timedelta(hours=7)
        unix_date = int(time.mktime(msc_date.timetuple()))

        return unix_date

    def __get_address(self):
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
        address_line = "";
        if 'улица/переулок' in info:
            addressBlock['street'] = info['улица/переулок']
        elif 'улица' in info:
            addressBlock['street'] = info['улица']
        elif 'местоположение' in info:
            addressBlock['street'] = info['местоположение']
        address_line = address_line + " " + addressBlock['street']
        if 'населенный пункт' in info:
            position = info['населенный пункт'].split(',')
            if len(position) == 1:
                addressBlock['city'] = str(position[0])
            else:
                for item in position:
                    if 'село' in item or 'c.' in item:
                        addressBlock['city'] = item

                addressBlock['city'] = addressBlock['city'].replace(' ','').replace(',','').replace('пгт', '')
        address_line = address_line + " " + addressBlock['city'];
        data['description'] = address_line
        return addressBlock;


    def __get_type_novelty(self):
        try:
            if breadcrumbs[6] == 'новыеквартиры':
                data['objectStage'] = sf.get_object_stage('сдан')
                return True

            if 'новые квартиры' in info:
                if info['новые квартиры'].lower() == 'да':
                    data['objectStage'] = sf.get_object_stage('сдан')
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
                return sf.get_OTC('аренда')
            else:
                if sf.get_OTC(breadcrumbs[2]) == 'rent':
                    data['rentType'] = 'long'
                return sf.get_OTC(breadcrumbs[2])
        except IndexError:
            if sf.get_OTC(breadcrumbs[2]) == 'rent':
                data['rentType'] = 'long'
            return sf.get_OTC(breadcrumbs[2])

    def __get_category_code(self):
        return sf.get_CC(breadcrumbs[3])

    def __get_building_type(self):
        if breadcrumbs[3] == 'жилая':
            return sf.get_BT(data['buildingClass'])

        elif breadcrumbs[3] == 'участкиидачи':
            return sf.get_BT('dacha_land')

        elif breadcrumbs[3] == 'коммерческая' or breadcrumbs[3] == 'гаражи':
            if 'вид объекта' in info:
                if sf.get_BT(data['typeCode']):
                    return sf.get_BT(data['typeCode'])
                else:
                    data['typeCode'] = 'other'
                    return sf.get_BT('other')
            else:
                data['typeCode'] = 'other'
                return sf.get_BT('other')

    def __get_building_class(self):
        if breadcrumbs[3] == 'жилая':
            return sf.get_BC(data['typeCode'])
            # if findall('комнаты,малосемейки', breadcrumbs[4]):
            #     if 'объект аренды' in info:
            #         return sf.get_BC(info['объект аренды'])
            #     else:
            #         return sf.get_BC('экономкласс')
            #
            # elif findall('малосемейки', breadcrumbs[4]):
            #     return sf.get_BC(breadcrumbs[4])
            #
            # elif findall('дома', breadcrumbs[4]):
            #     if 'объект продажи' in info:
            #         return sf.get_BC(info['объект продажи'])
            #     elif 'объект аренды' in info:
            #         return sf.get_BC(info['объект аренды'])
            #     else:
            #         return sf.get_BC('экономкласс')
            #
            # elif findall('квартиры', breadcrumbs[4]) or findall('комнаты', breadcrumbs[4]):
            #     if 'планировка' in info:
            #         return sf.get_BC(info['планировка'])
            #     else:
            #         return sf.get_BC('экономкласс')

        elif breadcrumbs[3] == 'коммерческая' or breadcrumbs[3] == 'гаражи':
            return sf.get_BC('а')

        elif breadcrumbs[3] == 'участкиидачи':
            return None

    def __get_type_code(self):
        if breadcrumbs[3] == 'жилая':
            if 'количество комнат' in info:
                if findall('дол', info['количество комнат']):
                    return sf.get_TC('доля')

            if breadcrumbs[4] == 'малосемейки' or breadcrumbs[4] == 'комнаты':
                return sf.get_TC('комната')

            elif breadcrumbs[4] == 'дома':
                if 'объект продажи' in info:
                    return sf.get_TC(info['объект продажи'])
                else:
                    return sf.get_TC('дом')

            elif breadcrumbs[4] == 'квартиры':
                return sf.get_TC(breadcrumbs[4])

            elif breadcrumbs[4] == 'комнаты,малосемейки':
                if 'объект аренды' in info:
                    return sf.get_TC(info['объект аренды'])
                else:
                    return sf.get_TC('комната')

        elif breadcrumbs[2] == 'сдам' and breadcrumbs[3] == 'коммерческая':
            data['typeCode'] = sf.get_TC(breadcrumbs[4])
            if 'вид объекта' in info:
                if sf.get_TC(info['вид объекта']):
                    return sf.get_TC(info['вид объекта'])
                else:
                    return data['typeCode']

        elif breadcrumbs[3] == 'коммерческая':
            if 'вид объекта' in info:
                if sf.get_TC(info['вид объекта']):
                    return sf.get_TC(info['вид объекта'])
                else:
                    return sf.get_TC('другое')

        elif breadcrumbs[3] == 'участкиидачи':
            return sf.get_TC('дачныйземельныйучасток')

        elif breadcrumbs[3] == 'гаражи':
            return sf.get_TC('другое')

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
                if item.find('a', href=compile('tel:')):
                    number = re.sub(r'\D', '', item.text)
                    if number.startswith('8') and len(number) == 11:
                        number = number.replace('8', '7', 1)
                    elif len(number) == 6:
                        number = '74212' + number
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
            tag_photos = check_tag_photos.find_all('div', class_='image-flex mb-1')
            data['photoUrl'] = []
            for photo in tag_photos:
                data['photoUrl'].append('https://present-dv.ru' + photo.find('a')['href'])

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
            if findall(pattr, info['балкон/лоджия']):
                data['balcony'] = True

            pattr = 'лоджия'
            if findall(pattr, info['балкон/лоджия']):
                data['loggia'] = True

            if findall('без', info['балкон/лоджия']):
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
            data['bathroom'] = sf.get_bathroom(info['туалет (санузел)'])

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
            data['roomsScheme'] = sf.get_room_scheme(scheme)

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
            data['condition'] = sf.get_condition(info['состояние'])
        else:
            return None

    def __get_house_type(self):
        if 'материал стен' in info:
            data['houseType'] = sf.get_house_type(info['материал стен'])

    def __get_other_fields(self):
        if 'отопление' in info:
            data['central_heating'] = True
        if 'водоснабжение' in info:
            data['water_supply'] = True
        if 'расстояние до города (км)' in info:
            data['distance'] = info['расстояние до города (км)'].replace('км', '').rstrip() + ' км'

    def __get_rent_fields(self):
        if 'на длительный срок' in info:
            if findall('да', info['на длительный срок'].lower()):
                data['rentType'] = 'long'

        if 'комплектация' in info:
            if findall('полностью', info['комплектация'].lower()):
                data['complete'] = True
                data['living_room_furniture'] = True
                data['kitchen_furniture'] = True
                data['couchette'] = True
                data['dishes'] = True
                data['refrigerator'] = True
                data['washer'] = True
                data['microwave_oven'] = True
                data['air_conditioning'] = True
                data['dishwasher'] = True
                data['tv'] = True

            else:
                data['complete'] = False

            if 'холодильник' in info:
                if findall('да', info['холодильник'].lower()):
                    data['refrigerator'] = True
                else:
                    data['refrigerator'] = False

            if 'стиральная машина' in info:
                if findall('да', info['стиральная машина'].lower()):
                    data['washer'] = True
                else:
                    data['washer'] = False

            if 'кондиционер' in info:
                if findall('да', info['кондиционер'].lower()):
                    data['air_conditioning'] = True
                else:
                    data['air_conditioning'] = False

            if 'телевизор' in info:
                if findall('да', info['телевизор'].lower()):
                    data['tv'] = True
                else:
                    data['tv'] = False

        if 'можно с домашними питомцами' in info:
            if findall('да', info['можно с домашними питомцами'].lower()):
                data['with_animals'] = True
            else:
                data['with_animals'] = False

        if '+ счетчики' in info:
            data['electrific_pay'] = True
            data['water_pay'] = True
            data['gas_pay'] = True

        if 'количество спальных мест' in info:
            data['couchette'] = True

    def __get_mediator_company(self):
        if 'агентство' in info:
            if info['агентство'].lower() == 'да':
                data['mediatorCompany'] = 'Агентство'


# if __name__ == '__main__':
#     present_url = "https://present-dv.ru/present/notice/view/3774238"
#     X = PresentParser()
#
#     params = {
#             'source': 'present-dv',
#             'url': present_url,
#             'ip': '193.124.180.185'
#     }
#
#     pprint(X.get_data(params))
