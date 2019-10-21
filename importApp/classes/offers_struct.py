def get_month(x):
    month = {
        'января': 1,
        'февраля': 2,
        'марта': 3,
        'апреля': 4,
        'мая': 5,
        'июня': 6,
        'июля': 7,
        'августа': 8,
        'сентября': 9,
        'октября': 10,
        'ноября': 11,
        'декабря': 12,
        'янв': 1,
        'фев': 2,
        'мар': 3,
        'апр': 4,
        'май': 5,
        'июн': 6, 
        'июл': 7,
        'авг': 8,
        'сен': 9,
        'окт': 10,
        'ноя': 11,
        'дек': 12,
    }

    try:
        return month.get(x.lower(), None)
    except AttributeError:
        return None


def get_OTC(x):
    offerTypeCode = {
        'продам': 'sale',
        'сдам': 'rent',
        'продажа': 'sale',
        'аренда': 'rent',
        'купить': 'sale',
        'снять': 'rent',
    }

    try:
        return offerTypeCode.get(x.lower(), None)
    except AttributeError:
        return None


def get_CC(x):
    categoryCode = {
        'жилая': 'rezidential',
        'коммерческая': 'commersial',
        'участкиидачи': 'land',
        'гаражи': 'commersial',

        'квартиры': 'rezidential',
        'квартира': 'rezidential',
        'посуточная аренда квартир': 'rezidential',
        'комнаты': 'rezidential',
        'коммерческая недвижимость': 'commersial',
        'дома': 'rezidential',
        'дачи': 'land',
        'коттеджи': 'land',
        'посуточная аренда домов': 'rezidential',
        'земельные участки': 'land',

        'квартир': 'rezidential',
        'дом': 'rezidential',
        'коттедж': 'land',
        'посуточно': 'rezidential',
        'помещений': 'commersial',
        'земельных': 'land',
        'дач': 'land',
    }

    try:
        return categoryCode.get(x.lower(), None)
    except AttributeError:
        return None


def get_BT(x):
    buildingType = {
        'elite': 'multisection_house',
        'business': 'multisection_house',
        'economy': 'multisection_house',
        'improved': 'multisection_house',
        'brezhnev': 'multisection_house',
        'khrushchev': 'multisection_house',
        'stalin': 'multisection_house',
        'old_fund': 'multisection_house',

        'small_apartm': 'corridor_house',
        'dormitory': 'corridor_house',
        'gostinka': 'corridor_house',

        'individual': 'multisection_house',

        'apartment': 'multisection_house',
        'room': 'multisection_house',
        'share': 'multisection_house',

        'house': 'lowrise_house',
        'cottage': 'lowrise_house',
        'townhouse': 'lowrise_house',
        'duplex': 'lowrise_house',



        'dacha_land': 'agricultural_land',



        'hotel': 'gpurpose_place',
        'restaurant': 'gpurpose_place',
        'cafe': 'gpurpose_place',
        'sport_building': 'gpurpose_place',

        'shop': 'market_place',
        'shops_center': 'market_place',
        'shop_entertainment': 'market_place',

        'cabinet': 'office',
        'office_space': 'office',
        'office_building': 'office',
        'business_center': 'office',

        'manufacture_building': 'production_place',
        'warehouse_space': 'production_place',
        'industrial_enterprise': 'production_place',
        'other': 'production_place',
    }

    try:
        return buildingType.get(x.lower(), None)
    except AttributeError:
        return None


def get_BC(x):
    buildingClass = {
        'элиткласс': 'elite',
        'бизнескласс': 'business',
        'экономкласс': 'economy',
        'улучшенная': 'improved',
        'улучшенная планировка': 'improved',
        'новая': 'improved',
        'брежневка': 'brezhnev',
        'хрущевка': 'khrushchev',
        'сталинка': 'stalin',
        'старыйфонд': 'old_fund',

        'малосемейки': 'small_apartm',
        'малосемейка': 'small_apartm',
        'общежитие': 'dormitory',
        'гостинка': 'gostinka',

        'индивидуальная': 'individual',
        'индивидуальная планировка': 'individual',

        'таунхаус': 'townhouse',
        'дуплекс': 'duplex',
        'коттедж': 'cottage',
        'дом': 'house',
        'таунхаусы': 'townhouse',
        'коттеджи': 'cottage',
        'дома': 'house',

        'share': 'economy',
        'room': 'economy',
        'apartment': 'economy',
        'townhouse': 'townhouse',
        'duplex': 'duplex',
        'cottage': 'cottage',
        'house': 'house',

        'дачи': None,
        'дача': None,


        # На английском
        'a': 'A',
        'a+': 'A+',
        'b': 'B',
        'b+': 'B+',
        'c': 'C',
        'c+': 'C+',

        # На русском
        'а': 'A',
        'а+': 'A+',
        'б': 'B',
        'б+': 'B+',
        'с': 'C',
        'с+': 'C+'

    }
    try:
        return buildingClass.get(x.lower(), None)
    except AttributeError:
        return None


def get_TC(x):
    typeCode = {
        'доля': 'share',
        'комната': 'room',
        'комнаты': 'room',
        'комната в квартире': 'room',
        'комната в общежитии': 'room',
        'комната в малосемейке': 'room',
        'комнаты,малосемейки': 'room',
        'малосемейка': 'room',
        'квартира': 'apartment',
        'квартиры': 'apartment',
        'дом': 'house',
        'дома': 'house',
        'коттедж': 'cottage',
        'коттеджи': 'cottage',
        'таунхаус': 'townhouse',
        'таунхаусы': 'townhouse',
        'дуплекс': 'duplex',

        'дача': 'dacha_land',
        'дачи': 'dacha_land',
        'участок': 'dacha_land',
        'дачныйземельныйучасток': 'dacha_land',
        'садовыйземельныйучасток': 'garden_land',
        'огородныйземельныйучасток': 'cultivate_land',


        'отель' : 'hotel',
        'гостиница': 'hotel',
        'ресторан': 'restaurant',
        'кафе': 'cafe',
        # 'помещение общественного питания': 'cafe???',
        'спортивный зал': 'sport_building',
        'спортивное сооружение': 'sport_building',
        'магазин': 'shop',
        'торговое помещение': 'shop',
        'торговый центр': 'shop_center',
        'тогово-развлекательный центр': 'shop_entertainment',
        'кабинет': 'cabinet',
        'офис': 'office_space',
        'офисное помещение': 'office_space',
        'офисное здание': 'office_building',
        'бизнес-центр': 'business_center',
        'бизнес центр': 'business_center',
        'производственное помещение': 'manufacture_building',
        'складское помещение': 'warehouse_space',
        'склад': 'warehouse_space',
        'база': 'warehouse_space',
        'промышленное предприятие': 'industrial_enterprice',
        'другое': 'other',
        'здание': 'other',
        'производственные помещения': 'manufacture_building',
        'производство': 'manufacture_building',
        'офисные помещения': 'office_space',

        'здания': 'other',
        'помещенияподавтобизнес': 'other',
        'торговыеплощади': 'shop_center',
        'склады,базы': 'warehouse_space',
        'офисныепомещения': 'office_space',
        'помещенияподсферууслуг': 'other',
        'помещениясвободногоназначения': 'other',
        'помещение свободного назначения': 'other',
        'псн': 'other',
        'производственныепомещения': 'manufacture_building',
    }
    try:
        return typeCode.get(x.lower(), None)
    except AttributeError:
        return None


def get_condition(x):
    condition = {
        'после строителей': 'rough',
        'соцремонт': 'social',
        'социальный ремонт': 'social',
        'сделан ремонт': 'repaired',
        'хорошее': 'repaired',
        'отличное': 'repaired',
        'евроремонт': 'euro',
        'дизайнерский ремонт': 'designer',
        'дизайнерский': 'designer',
        'требуется ремонт': 'need',

        'удовлетворительное': 'other',
        'косметический': 'other',
        'обычный ремонт': 'other',
        'после ремонта': 'other',
        'без ремонта': 'other',
        'требуется капитальный ремонт': 'other',
        'требуется косметический ремонт': 'other',
        'ветхий': 'other'
    }

    try:
        return condition.get(x.lower(), 'other')
    except AttributeError:
        return 'other'


def get_bathroom(x):
    bathroom = {
        'нет': 'no',
        'раздельный санузел': 'splited',
        'раздельный': 'splited',
        'совмещенный': 'combined',
        'совмещенный санузел': 'combined',
        'совмещённый': 'combined',
        'совмещённый санузел': 'combined',
    }

    try:
        return bathroom.get(x.lower(), "other")
    except AttributeError:
        return 'other'


def get_house_type(x):
    house_type = {
        'панельный': 'panel',
        'панель': 'panel',
        'панельное': 'panel',
        'деревянный': 'wood',
        'деревянное': 'wood',
        'дерево': 'wood',
        'брус': 'wood',
        'шлакоблочный': 'cinder block',
        'шлакоблочное': 'cinder block',
        'кирпичный': 'brick',
        'кирпичное': 'brick',
        'кирпич': 'brick',
        'блочный': 'cinder block',
        'блочное': 'cinder block',
        'блок': 'cinder block',
        'монолитный': 'monolithic',
        'монолит': 'monolithic',
        'монолитное': 'monolithic',
        'монолитный бетон': 'monolithic',
        'монолитно-кирпичный': 'monolithic_brick',
        'монолит-кирпич': 'monolithic_brick',
        'кирпично-монолитное': 'monolithic_brick',
    }

    try:
        return house_type.get(x.lower(), 'other')
    except AttributeError:
        return 'other'


def get_room_scheme(x):
    room_scheme = {
        'свободная планировка': 'free',
        'смежные': 'adjoining',
        'раздельные': 'separate',
        'смежно-раздельные': 'adjoin_separate',
        'студия': 'studio',
        'студии': 'studio',
        'другое': 'other',
    }

    try:
        return room_scheme.get(x.lower(), 'other')
    except AttributeError:
        return 'other'


def get_object_stage(x):
    object_stage = {
        'в стадии проекта': 'project',
        'строящийся объект': 'building',
        'сданный объект': 'ready',
        'сдан': 'ready',
        'сдача': 'building',
    }

    try:
        return object_stage.get(x.lower(), 'ready')
    except AttributeError:
        return 'ready'
