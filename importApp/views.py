from django.shortcuts import render
from django.views.generic import View
from elasticsearch import Elasticsearch
from multiprocessing import Process, current_process, Event
from datetime import datetime, timedelta
from importApp.classes import proxy
from importApp.classes.avito import AvitoParser as avito
from importApp.classes.present import PresentParser as present_site
from importApp.classes.irr import IrrParser as irr
from importApp.classes.cian import CianParser as cian
import threading, time, json
import traceback


es = Elasticsearch()

filler = None
fillerEvent = None
parserList = None
parserListEvent = None
proxyGetter = None
proxyGetterEvent = None
parserObj = {
    "avito": None,
    "present_site": None,
    "irr": None
}

parserObjEvent = {
    "avito": None,
    "present_site": None,
    "irr": None
}

class Main(View):
    def get(self, request):
        data = None
        if(request.GET.get('link')):
            try:
                data = es.search(index='results_list',
                                    body={
                                            "query": {
                                                "query_string" : {
                                                    "default_field": "sourceUrl",
                                                    "query" :  "\"" + request.GET.get('link') + "\"",
                                                }
                                            }
                                        },
                                 filter_path=['hits.hits._*', 'hits.total.value'])
            except Exception as ex:
                print("Error", traceback.format_exc())

        return render(request, 'index.html', context={'data': data, 'action': '/info'})

class Execute(View):
    def get(self, request):
        data = None
        if(request.GET.get('link')):
            try:

                data = es.update_by_query(index='results_list',
                                 body=request.GET.get('link'))
            except Exception as ex:
                print("Error", traceback.format_exc())

        return render(request, 'index.html', context={'data': data, 'action': '/execute'})


class Test(View):
    def get(self, request):
        mediaRes = None
        data = request.GET.get('link')
        if(data):
            try:
                json_acceptable_string = data.replace("'", "\"")
                data = json.loads(json_acceptable_string)
                if request.GET.get('type') and request.GET.get('type') == 'data':
                    mediaRes = globals()[data['media']]().get_data(data)
                elif request.GET.get('type') and request.GET.get('type') == 'list':
                    mediaRes = globals()[data['media']]().parseList(data)
            except BaseException as ex:
                mediaRes = ex
            except Exception as ex:
                mediaRes = traceback.format_exc()

        return render(request, 'index.html', context={'data': mediaRes, 'link': data, 'action': '/test'})


class FindHistory(View):
    def get(self, request):
        data = None
        if(request.GET.get('link')):
            try:
                data = es.search(index='urls_history',
                                        body={
                                            "query": {
                                                "query_string" : {
                                                    "default_field": "\"" + "data" + "\"",
                                                    "query" :  request.GET.get('link'),
                                                }
                                            }
                                        },
                                 filter_path=['hits.hits._*', 'hits.total.value'])
            except Exception as ex:
                print("Error", traceback.format_exc())

        return render(request, 'index.html', context={'data': data, 'action': '/findHistory'})


class Control(View):
    def get(self, request):
        data = {}

        if filler:
            data['filler'] = filler.is_alive()
        else: data['filler'] = False

        if parserList:
            data['parserList'] = parserList.is_alive()
        else: data['parserList'] = False

        if proxyGetter:
            data['proxyGetter'] = proxyGetter.is_alive()
        else: data['proxyGetter'] = False


        data['parserObj'] = parserObj

        return render(request, 'importApp/import.html', context={'data': data})

class ProxyList(View):
    def get(self, request):
        elasticData = {
            'proxy_listIndex': es.indices.exists(index='proxy_list')
        }
        if elasticData['proxy_listIndex']:
            data = es.search(index='proxy_list', filter_path=['hits.hits._*', 'hits.total.value'])
            elasticData['count'] = data['hits']['total']['value']
            if elasticData['count'] > 0:
                elasticData['proxy_list'] = data['hits']['hits']

        return render(request, 'importApp/proxy.html', context={'elasticData': elasticData})

class Errors(View):
    def get(self, request):
        elasticData = {
            'errorsIndex': es.indices.exists(index='errors')
        }
        if elasticData['errorsIndex']:
            data = es.search(index='errors', filter_path=['hits.hits._*', 'hits.total.value']
            # ,
                            # body={
                            #     "query": {
                            #         "bool": {
                            #             "must": [
                            #                 {"match": {"media": "avito"}},
                            #             ]
                            #         }
                            #     }
                            # }
             )
            elasticData['count'] = data['hits']['total']['value']
            if elasticData['count'] > 0:
                elasticData['errors'] = data['hits']['hits']

        return render(request, 'importApp/errors.html', context={'elasticData': elasticData})

class Results(View):
    def get(self, request):
        elasticData = {
            'results_listIndex': es.indices.exists(index='results_list')
        }
        if elasticData['results_listIndex']:
            data = es.search(index='results_list', filter_path=['hits.hits._*', 'hits.total.value'])
            elasticData['count'] = data['hits']['total']['value']
            if elasticData['count'] > 0:
                elasticData['results_list'] = data['hits']['hits']

        return render(request, 'importApp/results.html', context={'elasticData': elasticData})

class Statistic(View):
    def get(self, request):
        elasticData = {
            'resource_urlsIndex': es.indices.exists(index='resource_urls')
        }
        if elasticData['resource_urlsIndex']:
            data = es.search(index='resource_urls',
                             filter_path=['hits.hits._*', 'hits.total.value']
                             # ,body={
                             #         "query": {
                             #             "bool": {
                             #                 "must": [
                             #                     {"match": {"media": "present_site"}},
                             #                 ]
                             #             }
                             # }}
            )
            elasticData['countUrls'] = data['hits']['total']['value']
            if elasticData['countUrls'] > 0:
                elasticData['resource_urls'] = data['hits']['hits']

        return render(request, 'importApp/statistic.html', context={'elasticData': elasticData})

class History(View):
    def get(self, request):
        elasticData = {
            'urls_historyIndex': es.indices.exists(index='urls_history')
        }
        if elasticData['urls_historyIndex']:
            data = es.search(index='urls_history', filter_path=['hits.hits._*', 'hits.total.value'])
            elasticData['count'] = data['hits']['total']['value']
            if elasticData['count'] > 0:
                elasticData['urls_history'] = data['hits']['hits']

        return render(request, 'importApp/history.html', context={'elasticData': elasticData})


class Jobs(View):
    def get(self, request):
        if request.GET.get('filler'):
            if request.GET.get('filler') == 'true':
                global fillerEvent
                global filler
                self.startFiller()
            else:
                self.stopFiller()
        elif request.GET.get('list_parser'):
            if request.GET.get('list_parser') == 'true':
                self.startParserList()
            else:
                self.stopParserList()
        elif request.GET.get('obj_parser') and request.GET.get('state'):
            if request.GET.get('state') == 'true':
                self.startParserObj(request.GET.get('obj_parser'))
            else:
                self.stopParserObj(request.GET.get('obj_parser'))
        elif request.GET.get('proxy_getter'):
            if request.GET.get('proxy_getter') == 'true':
                self.startProxyGetter()
            else:
                self.stopProxyGetter()
        return render(request, 'importApp/import.html', context={})

    def startFiller(self):
        global fillerEvent
        global filler
        fillerEvent = Event()
        filler = Process(target=self.doFiller, name='Filler links', args=(fillerEvent, ))
        filler.start()

    def stopFiller(self):
        global fillerEvent
        global filler
        fillerEvent.set()
        filler.join()

    def startParserList(self):
        global parserListEvent
        global parserList
        parserListEvent = Event()
        parserList = Process(target=self.doParserList, name='Parser list links', args=(parserListEvent, ))
        parserList.start()

    def stopParserList(self):
        global parserListEvent
        global parserList
        parserListEvent.set()
        parserList.join()

    def startParserObj(self, source):
        global parserObjEvent
        global parserObj
        parserObjEvent[source] = Event()
        parserObj[source] = Process(target=self.doParserObj, name='Parser objects ' + source, args=(parserObjEvent[source], source, ))
        parserObj[source].start()

    def stopParserObj(self, source):
        global parserObjEvent
        global parserObj
        parserObjEvent[source].set()
        parserObj[source].join()

    def startProxyGetter(self):
        global proxyGetterEvent
        global proxyGetter
        proxyGetterEvent = Event()
        proxyGetter = Process(target=self.doGetProxy, name='Proxy Getter', args=(proxyGetterEvent, ))
        proxyGetter.start()

    def stopProxyGetter(self):
        global proxyGetterEvent
        global proxyGetter
        proxyGetterEvent.set()
        proxyGetter.join()

    def doGetProxy(self, event):
        current_date = datetime.now() - timedelta(minutes=10)
        proc_name = current_process().name
        print("Starting \"" + proc_name + "\"")
        pause = 0.5
        while not event.wait(pause):
            pause = 300
            if current_date + timedelta(minutes=10) <= datetime.now():
                proxy.get_proxy_list()
                current_date = datetime.now()
        print("Stopping \"" + proc_name + "\"")

    def doFiller(self, event):
        proc_name = current_process().name
        print("Starting \"" + proc_name + "\"")
        pause = 0.5
        while not event.wait(pause):
            pause = 1800
            results = es.search(index='medias_import',
                                body={
                                    "query": {
                                        "bool": {
                                            "must": [
                                                {"match": {"city.state": "active"}},
                                            ]
                                        }
                                    }
                                }, filter_path=['hits.hits._source', 'hits.total.value']
                                )
            total = results['hits']['total']['value']
            if total > 0:
                for res in results['hits']['hits']:
                    val = res['_source']
                    data = {
                        'media': val['media']
                    }
                    for city in val['city']:
                        if city['state'] == 'active':
                            data['city'] = city['code']
                            data['pages'] = city['pages']
                            data['pause'] = city['pause']
                            data['url'] = city['url']
                            for link in city['links']:
                                data['link'] = link['link']
                                results = es.search(index='source_data',
                                                    body={
                                                        "query": {
                                                            "bool": {
                                                                "must": [
                                                                    {"match": {"link": data['link']}},
                                                                    {"match": {"city": data['city']}},
                                                                    {"match": {"media": data['media']}},
                                                                ]
                                                            }
                                                        }
                                                    }, filter_path=['hits.hits._source', 'hits.total.value', 'hits.hits._id'])
                                if results['hits']['total']['value'] == 0:
                                    es.index('source_data', data)
        print("Stopping \"" + proc_name + "\"")


    def doParserList(self, event):
        proc_name = current_process().name
        print("Starting \"" + proc_name + "\"")
        pause = 0.5
        while not event.wait(pause):
            try:
                pause = 5
                results = es.search(index='source_data', filter_path=['hits.hits._source', 'hits.total.value', 'hits.hits._id'])

                total = results['hits']['total']['value']
                if total > 0:
                    for res in results['hits']['hits']:
                        try:
                            mediaFunc = globals()[res['_source']['media']]().parseList(res['_source'])
                            es.delete('source_data', res['_id'])
                        except Exception as ex:
                            print("Error", traceback.format_exc())
            except Exception as ex:
                print("Error", traceback.format_exc())

        print("Stopping \"" + proc_name + "\"")


    def doParserObj(self, event, source):
        proc_name = current_process().name
        print("Starting \"" + proc_name + "\"")
        pause = 0.5
        while not event.wait(pause):
            try:
                pause = 5
                results = es.search(index='resource_urls',
                                    body={
                                        "query": {
                                            "bool": {
                                                "must": [
                                                    {"match": {"media": source}}
                                                ]
                                            }
                                        }
                                    },
                                    filter_path=['hits.hits._source', 'hits.total.value', 'hits.hits._id'], size=10, from_=0)

                total = results['hits']['total']['value']
                if total > 0:
                    treads = []
                    for res in results['hits']['hits']:
                        thread = Process(target=self.doParseMedia, args=(res, ))
                        # thread.daemon = True
                        treads.append(thread)
                        thread.start()
                    for tr in treads:
                        tr.join()
                    es.reindex
            except Exception as ex:
                print("Error", traceback.format_exc())
        print("Stopping \"" + proc_name + "\"")


    def doParseMedia(self, args):
        try:
            mediaRes = globals()[args['_source']['media']]().get_data(args['_source'])
            if mediaRes:
                if mediaRes != 'CLOSED':
                    es.index('results_list', mediaRes)
                es.delete('resource_urls', args['_id'])
            if args['_source'].get('pause_source'):
                time.sleep(int(args['_source']['pause_source']))
            else:
                time.sleep(3)
        except BaseException as ex:
            if str(ex) == "DELETED" or str(ex) == 'CLOSED':
                es.delete('resource_urls', args['_id'])
        except Exception as ex:
            es.index('errors',
                     {
                        'media': args['_source']['media'],
                        'link': args['_source']['link'],
                        'date': datetime.today(),
                        'error': traceback.format_exc()
                    }, 'results'
            )
