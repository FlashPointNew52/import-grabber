from datetime import datetime, timedelta
import secrettools as ts
from time import sleep


if __name__ == '__main__':
    print('Proxy-updater is running...')
    ts.get_proxy_list()
    current_date = datetime.now()
    while True:
        if current_date + timedelta(minutes=10) <= datetime.now():
            ts.get_proxy_list()
            current_date = datetime.now()
            print('Update successful! Date:{date}'.format(date=current_date))
        sleep(300)
