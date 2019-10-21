import requests
import special_function as sf
import top_secret as ts
import time
import datetime
from bs4 import BeautifulSoup
from pprint import pprint
from re import findall
from datetime import datetime


class FarpostParser:

    def __get_html(self, params):
        source = params['source']
        url = params['url']
        ip = params['ip']

        attempt = 1
        delay_sec = 0.5
        while attempt <= 5:
            self.req = requests.get(url, headers=ts.get_headers(source), cookies=ts.cook_for_ip(source, ip))
            if self.req.status_code == requests.codes.ok:
                return self.req.text
            else:
                attempt += 1
                time.sleep(delay_sec)
        exit()

    def get_data(self, parameters):
        html_code = self.__get_html(parameters)

        global data
        data = {
            'id': None,
            'source_media': None,
            'source_url': None,
            'add_date': None,
            'offer_type_code': None,
            'type_code': None,
            'phones_import': None,

            'category_code': None,
            'building_type': None,
            'building_class': None,
            'address': None,
            # 'location_lat': None,
            # 'location_lon': None,
            'new_building': None,
            'object_stage': 'ready'
        }

        global soup
        global breadcrumbs
        global info
        soup = BeautifulSoup(html_code, 'lxml').find('body')

        breadcrumbs = []
        tag_breadcrumbs = soup.find_all('span', itemprop='name')

        for crumb in tag_breadcrumbs:
            breadcrumbs.append(crumb.get_text().lower())

        # pprint(breadcrumbs)

        info = self.__get_info()

        data['id'] = self.__get_id()
        data['source_media'] = 'farpost'
        data['source_url'] = parameters['url']
        data['add_date'] = self.__get_date()
        data['offer_type_code'] = self.__get_offer_type_code()
        data['type_code'] = self.__get_type_code()
        data['category_code'] = self.__get_category_code()
        data['phones_import'] = self.__get_phones(parameters)
        data['address'] = self.__get_address()

        # Обязательные поля, но возможны значения по умолчанию

        # data['building_class'] = self.__get_building_class()
        # data['building_type'] = self.__get_building_type(data['type_code'])
        # data['new_building'] = self.__get_type_novelty()
        # # data['object_stage'] = self.__get_object_stage()
        #
        # # Прочие поля
        # self.__get_price()
        # self.__get_photo_url()
        # # self.__get_email()
        # # self.__get_balcony()
        # self.__get_source_media_text()
        # self.__get_rooms_count()
        # self.__get_floor()
        # self.__get_square()
        # # self.__get_condition()
        # self.__get_house_type()
        # self.__get_mediator_company()

        return data

    def __get_id(self):
        now_date = datetime.today()
        date_create = datetime(now_date.year, now_date.month, now_date.day, now_date.hour,
                               now_date.minute, now_date.second)

        unix_id = int(time.mktime(date_create.timetuple()))

        return unix_id

    def __get_info(self):
        info = {}
        all_info = soup.find_all('div', class_='field viewbull-field__container')

        for unit in all_info:
            key = unit.find(class_='label').get_text().lower()
            value = unit.span.get_text().replace('\t', '').replace('\n', '').replace('\xa0', '').replace(
                'Подробности о '
                'доме ', '')
            info[key] = value

        # pprint(info)
        return info

    def __get_date(self):
        tag_date = soup.find('span', class_='viewbull-header__actuality')
        info_date = tag_date.get_text()
        dmy = findall(r'\w+', info_date)

        date_time = {
            'day': None,
            'month': None,
            'year': None,
            'hour': '12',
            'minute': '00',
            'second': '00'
        }

        if dmy[2] == 'вчера':
            date_time['day'] = datetime.now().day - 1
            date_time['month'] = datetime.now().month
            date_time['year'] = datetime.now().year
            date_time['hour'] = dmy[0]
            date_time['minute'] = dmy[1]

        elif dmy[2] == 'сегодня':
            date_time['day'] = datetime.now().day
            date_time['month'] = datetime.now().month
            date_time['year'] = datetime.now().year
            date_time['hour'] = dmy[0]
            date_time['minute'] = dmy[1]

        else:
            date_time['day'] = dmy[2]
            date_time['month'] = sf.get_month(dmy[3])
            date_time['year'] = datetime.now().year
            date_time['hour'] = dmy[0]
            date_time['minute'] = dmy[1]

        date = datetime(int(date_time['year']), int(date_time['month']), int(date_time['day']), int(date_time['hour']), int(date_time['minute']))

        unix_date = int(time.mktime(date.timetuple()))

        return unix_date

    def __get_address(self):
        return info['адрес']

    def __get_offer_type_code(self):
        offer_type = breadcrumbs[2].split(' ')

        return sf.get_OTC(offer_type[0])

    def __get_category_code(self):
        if breadcrumbs[2] == 'продажа домов и коттеджей':
            return sf.get_CC(self.category_in_title())

        category = breadcrumbs[2].split(' ')

        return sf.get_CC(category[1])

    def __category_in_title(self):
        tag_title = soup.find('span', attrs={'data-field': 'subject', 'class': 'inplace'})
        title_text = tag_title.get_text().lower()

        house = 'дом'
        cottage = 'коттедж'

        if findall(house, title_text):
            return house
        elif findall(cottage, title_text):
            return cottage

    def __get_building_class(self):
        return None

    def __get_building_type(self):
        return None

    def __get_type_code(self):
        return None

    def __get_phones(self, params):
        source = params['source']
        ip = params['ip']

        tag_id = soup.find('div', class_='actionsHeader')
        id_seller = tag_id.div.get_text().replace("№", '')

        ajax_url = "https://www.farpost.ru/bulletin/" + id_seller + "/ajax_contacts?&ajax=1&"
        ajax_req = requests.get(ajax_url, headers=ts.get_headers(source), cookies=ts.cook_for_ip(source, ip))
        ajax_html = ajax_req.text
        ajax_soup = BeautifulSoup(ajax_html, 'lxml')

        phones = []
        tag_number = ajax_soup.find_all('div', class_="new-contacts__td new-contact__phone")
        if tag_number:
            for phone in tag_number:
                phones.append(phone.get_text().replace('\t', '').replace('\n', '').replace('+7', '8'))

            return phones
        else:
            while not ajax_soup.find('div', class_='new-contacts__td new-contact__phone'):
                pprint(ajax_soup.find('style'))
                print('Из файла:', ts.cook_for_ip(source, ip))
                print("№1: ", ajax_req.cookies)
                cook1 = {
                    'ring': ajax_req.cookies['PHPSESSID']
                }
                # pprint(cook1)
                ts.set_cookies(source, ip, cook1)
                captcha_code = str(input("Введите капчу: "))
                ajax_url += ('captcha_code='+captcha_code)
                ajax_req = requests.get(ajax_url, headers=ts.get_headers(source), cookies=ts.cook_for_ip(source, ip))
                print("№2: ", ajax_req.cookies)
                ajax_html = ajax_req.text
                ajax_soup = BeautifulSoup(ajax_html, 'lxml')

            pprint(ajax_soup.find('div', class_='new-contacts__td new-contact__phone'))

            return None


if __name__ == '__main__':
    farpost_url ="https://www.farpost.ru/khabarovsk/realty/sell_flats/2-komnatnaja-v-centre-goroda-65322555.html"

    X = FarpostParser()
    params = {
            'source': 'farpost',
            'url': farpost_url,
            'ip': '193.124.180.185'
    }
    pprint(X.get_data(params))

