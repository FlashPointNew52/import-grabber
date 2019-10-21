import requests, time
from datetime import datetime
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from random import randint
from user_agent import generate_user_agent

es = Elasticsearch()


def get_proxy_list():
    req = requests.get('https://free-proxy-list.net/', headers={'user-agent': generate_user_agent(device_type="desktop",
                                                                                   os=('mac', 'linux'))})
    html_code = req.text
    soup = BeautifulSoup(html_code, 'lxml').find('tbody')
    tag_ip = soup.find_all('tr', limit=3000)
    if tag_ip:
        for row in tag_ip:
            if row.find(class_='hx').text == 'no':
                ip = row.find('td').text
                port = row.find('td').find_next_sibling().text
                if ip and port:
                    results = es.search(index='proxy_list',
                                     body={
                                         "query": {
                                             "bool": {
                                                 "must": [
                                                     {"match": {"ip": ip}},
                                                     {"match": {"port": port}},
                                                 ]
                                             }
                                         }
                                     }, filter_path=['hits.hits._id*', 'hits.total.value'])
                    total = results['hits']['total']['value']
                    id = None
                    if total > 0:
                        id = results['hits']['hits'][0]['_id']
                    es.index('proxy_list', {"ip": ip, "port": port, "date": datetime.today()}, "_doc", id)

def set_proxy():
    results = es.search(index='proxy_list',
                        filter_path=['hits.hits.*', 'hits.total.value'], size=100, from_=0)
    if results['hits']['total']['value'] > 100:
        total = 100
    else:
        total = results['hits']['total']['value']
    rand_num = randint(0, total-1)
    proxy={}
    http_prox = 'http://{ip}:{port}'.format(ip=results['hits']['hits'][rand_num]['_source']['ip'],
                                            port=results['hits']['hits'][rand_num]['_source']['port'])
    https_prox = 'https://{ip}:{port}'.format(ip=results['hits']['hits'][rand_num]['_source']['ip'],
                                              port=results['hits']['hits'][rand_num]['_source']['port'])
    proxy['http'], proxy['https'] = http_prox, https_prox
    return proxy

def get_headers(source):
    headers = {
        'avito':{
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'upgrade-insecure-requests': '1',
            'user-agent': generate_user_agent(device_type="desktop",
                                              os=('mac', 'linux'))
        },
        'farpost':{
            'user-agent': generate_user_agent(device_type="desktop",
                                              os=('mac', 'linux')),
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'upgrade-insecure-requests': '1',
        },
        'cian':{
            'user-agent': generate_user_agent(device_type="desktop",
                                              os=('mac', 'linux')),
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'connection': 'keep-alive',
            # 'content-type': 'application/json',
        },
        'present_site':{
            'user-agent': generate_user_agent(device_type="desktop",
                                              os=('mac', 'linux')),
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'connection': 'keep-alive',
        },
        'yandex':{
            'User-Agent': generate_user_agent(device_type="desktop",
                                              os=('mac', 'linux')),
            'Content-Type': 'text/plain;charset=UTF-8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        },
        'irr':{
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': generate_user_agent(device_type="desktop", os=('mac', 'linux')),
            'connection': 'keep-alive',
            'accept-encoding': 'gzip, deflate, br'
        },
        'mkv':{
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'User-Agent': generate_user_agent(device_type="desktop", os=('mac', 'linux')),
            'connection': 'keep-alive',
            'accept-encoding': 'gzip, deflate, br'
        }
    }

    return headers[source]
