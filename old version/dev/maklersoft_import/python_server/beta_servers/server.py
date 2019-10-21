#!/usr/bin/env python3
from sys import argv
from socketserver import ThreadingMixIn
import json
import requests
from re import findall
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib import parse
from pprint import pprint
import top_secret as ts
from present_parser_V2 import PresentParser as PP
from avito_parser_V2 import AvitoParser as AV
from cian_parser_V2 import CianParser as CP
from irr_parser_V2 import IrrParser as IRRP
from yandex_parser import YandexParser as YP


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class Serv(BaseHTTPRequestHandler):

    def do_GET(self):
        message = None
        data = None

        if self.path == '/favicon.ico':
            pass

        else:
            path = self.path.split('?')[0]
            if path == '/get_media_data':

                params_size = len(self.path.split('?'))

                if params_size == 2 and self.path.split('?')[1] != '':

                    try:
                        query_path = self.path
                        query_url = parse.parse_qs(parse.urlparse(query_path).query)['url'][0]
                        query_ip = parse.parse_qs(parse.urlparse(query_path).query)['ip'][0]
                        query_source = query_url.split('/')[2].replace('www', '').replace('.ru', '').replace('.', '')

                        if requests.get(query_url).status_code != requests.codes.ok:
                            message = "Invalid url!\r\n"

                        else:
                            params = {
                                'source': query_source,
                                'url': query_url,
                                'ip': query_ip,
                            }

                            if params['source'] == 'present-dv':
                                try:
                                    data = PP().get_data(params)
                                except SystemExit:
                                    message = "Present-script error!\r\n"

                            elif params['source'] == 'avito':
                                try:
                                    data = AV().get_data(params)
                                except SystemExit:
                                    message = "Avito-script error!\r\n"

                            elif findall('cian', params['source']):
                                try:
                                    data = CP().get_data(params)
                                except SystemExit:
                                    message = "Cian-script error!\r\n"

                            elif findall('irr', params['source']):
                                params['source'] = 'irr'
                                try:
                                    data = IRRP().get_data(params)
                                except SystemExit:
                                    message = "IRR-script error!\r\n"

                            elif findall('yandex', params['source']):
                                params['source'] = 'yandex'
                                try:
                                    data = YP().get_data(params)
                                except SystemExit:
                                    message = "Yandex-script error!\r\n"

                            else:
                                message = "Params not found!\r\n"

                    except KeyError:
                        message = "Params is not full!\r\n"

                else:
                    message = "Params is null!\r\n"

            else:
                message = "Path not found!\r\n"

            if data:
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                json_data = json.dumps(data, ensure_ascii=False).encode()
                self.wfile.write(json_data)

            else:
                self.send_response(404)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()


if __name__ == '__main__':
    ts.get_proxy_list()
    # PORT_LIST = (9000, 8080)
    HOST = 'localhost'
    # PORT = 9000

    # print('Run server: http://{0}:{1}'.format(HOST, PORT))
    # serv = HTTPServer((HOST, PORT), Serv)
    # serv.serve_forever()
    PORT = int(argv[1])
    print('Run server: http://{0}:{1}'.format(HOST, PORT))
    server = ThreadedHTTPServer((HOST, PORT), Serv)
    server.allow_reuse_address = True
    server.serve_forever()




