import socket
import threading
import json
import secrettools as ts

from sys import argv
from re import findall
from urllib import parse
from pprint import pprint
from time import sleep

from avito import AvitoParser as AP
from cian import CianParser as CP
from irr import IrrParser as IRRP
from mirkvartir import MirKvarParser as MKP
from present import PresentParser as PP
from yandex import YandexParser as YP


def client_handler(client: socket.socket):
    mutex = threading.Lock()
    path = client.recv(2048).decode()
    mutex.acquire()
    check_path, path = path.split('?')
    data = None
    message = None
    if findall('/get_media_data', check_path):
        raw_path = path.split()[0]
        params_size = len(raw_path.split('&'))
        if params_size == 2:
            query_path = '/get_media_data?' + raw_path
            query_url = parse.parse_qs(parse.urlparse(query_path).query)['url'][0]
            query_ip = parse.parse_qs(parse.urlparse(query_path).query)['ip'][0]
            query_source = query_url.split('/')[2].replace('www', '').replace('.ru', '').replace('.', '')
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

                elif findall('irr', params['source']):
                    params['source'] = 'irr'
                    data = IRRP().get_data(params)

                elif findall('yandex', params['source']):
                    params['source'] = 'yandex'
                    data = YP().get_data(params)

            except SystemExit:
                message = "{src}-script error!".format(src=params['source'].title())

            if data:
                print('Done. URL: ', query_url, ' IP: ', query_ip)
                pprint(data)
                # input()
                json_data = json.dumps(data, ensure_ascii=False).encode()
                client.send(json_data)

            else:
                print(message + ' URL: {url}\n'.format(url=query_url))

    client.close()
    mutex.release()


def run_server(host='localhost', port=9000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    sock.bind((host, port))
    sock.listen(128)
    print('Run server: http://{0}:{1}'.format(host, port))
    try:
        while True:
            client_sock, addr = sock.accept()
            # print('Connected: ', addr)
            client_thread = threading.Thread(
                target=client_handler,
                args=(client_sock,))
            client_thread.daemon = True
            client_thread.start()
            sleep(0.5)

    except KeyboardInterrupt:
        print("Shutting down")

    finally:
        sock.close()


if __name__ == "__main__":
    ts.get_proxy_list()
    HOST = 'localhost'
    try:
        PORT = int(argv[1])
    except IndexError:
        PORT = 9000
    run_server(HOST, PORT)
