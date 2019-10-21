import multiprocessing
import time
import socket
import threading
import json

from datetime import datetime
from sys import argv
from re import findall
from urllib import parse
from pprint import pprint

from avito import AvitoParser as AP
from cian import CianParser as CP
from irr import IrrParser as IRRP
from mirkvartir import MirKvarParser as MKP
from present import PresentParser as PP
from yandex import YandexParser as YP


def worker_thread(serversocket):
    while True:
        clientsocket, (client_address, client_port) = serversocket.accept()

        try:
            path = clientsocket.recv(2048).decode()
        except OSError:
            clientsocket.send("error: wrong path")
            break

        check_path, path = path.split('?')
        data = None
        message = None
        if findall('/get_media_data', check_path):
            raw_path = path.split()[0]
            params_size = len(raw_path.split('&'))
            if params_size == 2:
                query_path = '/get_media_data?' + raw_path
                query_url = \
                parse.parse_qs(parse.urlparse(query_path).query)['url'][0]
                query_ip = \
                parse.parse_qs(parse.urlparse(query_path).query)['ip'][0]
                query_source = query_url.split('/')[2].replace('www','').replace('.ru', '').replace('.', '')
                params = {
                    'source': query_source,
                    'url': query_url,
                    'ip': query_ip,
                }
                print('Start get_data. URL: ', query_url, ' IP: ', query_ip)

                try:
                    if params['source'] == 'present-dv':
                        params['source'] = 'present-dv'
                        data = PP().get_data(params)

                    elif params['source'] == 'avito':
                        params['source'] = 'avito'
                        data = AP().get_data(params)

                    elif findall('cian', params['source']):
                        params['source'] = 'cian'
                        data = CP().get_data(params)

                    elif findall('mirkvartir', params['source']):
                        params['source'] = 'mkv'
                        data = MKP().get_data(params)

                    elif findall('irr', params['source']):
                        params['source'] = 'irr'
                        data = IRRP().get_data(params)

                    elif findall('yandex', params['source']):
                        params['source'] = 'yandex'
                        data = YP().get_data(params)

                except SystemExit as e:
                    message = "{src}-script error!".format(src=params['source'].title())
                    clientsocket.send(json.dumps("error:" + params['url'] + ' ' + str(e), ensure_ascii=False).encode())
                except Exception as e:
                    message = "{src}-script error!".format(src=params['source'].title())
                    clientsocket.send(json.dumps("error:" + params['url'] + ' ' + str(e), ensure_ascii=False).encode())
        if data:
            print('Done. Date:{date} | URL: '.format(date=datetime.now()), check_path)
            json_data = json.dumps(data, ensure_ascii=False).encode()
            clientsocket.send(json_data)

        else:
            print(message + ' URL: {url}\n'.format(url=query_url))
            clientsocket.send(json.dumps("error:" + message, ensure_ascii=False).encode())

        clientsocket.close()


def worker_process(serversocket):
    NUMBER_OF_THREADS = 5
    for _ in range(NUMBER_OF_THREADS):
        thread = threading.Thread(target=worker_thread, args=(serversocket,))
        thread.daemon = True
        thread.start()

    while True:
        time.sleep(.100)


def run_server(host='localhost', port=9000):
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    serversocket.bind((host, port))
    serversocket.listen(25)
    print('Run server: http://{0}:{1}'.format(host, port))
    NUMBER_OF_PROCESS = multiprocessing.cpu_count()
    for _ in range(NUMBER_OF_PROCESS):
        process = multiprocessing.Process(target=worker_process, args=(serversocket,))
        process.daemon = True
        process.start()

    while True:
        time.sleep(.100)


if __name__ == "__main__":
    HOST = 'localhost'
    try:
        PORT = int(argv[1])
    except IndexError:
        PORT = 9000

    run_server(HOST, PORT)
