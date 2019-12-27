from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
import json
from django.views.generic import View
from elasticsearch import Elasticsearch
from managePanel.classes import mediaCity, media
import managePanel.classes.mappings as mappings
import time

es = Elasticsearch()


def settings(request):
    return render(request, 'managePanel/index.html')


def settingsCities(request):
    elasticData = {
        'citiesIndex': es.indices.exists(index='cities')
    }

    if elasticData['citiesIndex']:
        results = es.search(index='cities', filter_path=['hits.total.value,hits.hits._id,hits.hits._source.cityCode,hits.hits._source.cityName, hits.hits._source.timeZone'])
        elasticData['counts'] = results['hits']['total']['value']
        if elasticData['counts'] > 0:
            elasticData['count'] = len(results['hits']['hits'])
            elasticData['cities'] = []
            for data in results['hits']['hits']:
                ms = mediaCity.MediaCity(data['_source']['cityCode'], data['_source']['cityName'], data['_source']['timeZone'])
                ms.id = data['_id']
                elasticData['cities'].append(ms)
    return render(request, 'managePanel/cities.html', context={'elasticData': elasticData})


class SettingsMediaList(View):
    def get(self, request):
        elasticData = {
            'mediasIndex': es.indices.exists(index='medias')
        }
        if elasticData['mediasIndex']:
            results = es.search(index='medias', filter_path=['hits.total.value,hits.hits._id,hits.hits._source.code,hits.hits._source.name'])
            elasticData['counts'] = results['hits']['total']['value']
            if elasticData['counts'] > 0:
                elasticData['count'] = len(results['hits']['hits'])
                elasticData['medias'] = []
                for data in results['hits']['hits']:
                    ms = media.Media(data['_source']['code'], data['_source']['name'])
                    ms.id = data['_id']
                    elasticData['medias'].append(ms)
        return render(request, 'managePanel/medialist.html', context={'elasticData': elasticData})


class SettingsMediasImport(View):
    def get(self, request):

        elasticData = {
            'mediasImportIndex': es.indices.exists(index='medias_import')
        }
        if elasticData['mediasImportIndex']:
            medias = es.search(index='medias', filter_path=['hits.hits._source.*'])
            cities = es.search(index='cities', filter_path=['hits.hits._source.*'])
            elasticData['medias'] = []
            elasticData['cities'] = []
            for data in medias['hits']['hits']:
                elasticData['medias'].append(media.Media(data['_source']['code'], data['_source']['name']))
            for data in cities['hits']['hits']:
                elasticData['cities'].append(media.Media(data['_source']['cityCode'], data['_source']['cityName']))
            results = es.search(index='medias_import', filter_path=[])
            elasticData['counts'] = results['hits']['total']['value']
            if elasticData['counts'] > 0:
                elasticData['count'] = len(results['hits']['hits'])
                elasticData['mediasImport'] = []
                for data in results['hits']['hits']:
                    elasticData['mediasImport'].append(data)
        return render(request, 'managePanel/mediasImport.html', context={'elasticData': elasticData})


class SettingsElastic(View):
    def get(self, request):
        elasticData = {
            'source_dataIndex': es.indices.exists(index='source_data')
        }
        if elasticData['source_dataIndex']:
            data = es.search(index='source_data', filter_path=['hits.hits._*', 'hits.total.value'])
            elasticData['count'] = data['hits']['total']['value']
            if elasticData['count'] > 0:
                elasticData['source_data'] = data['hits']['hits']

        return render(request, 'managePanel/elastic.html', context={'elasticData': elasticData})


class CreateIndex(View):
    def post(self, request):
        mapping = mappings.get_map(request.POST.get('index'))
        es.indices.create(index=request.POST.get('index'), body=mapping)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))


class DeleteIndex(View):
    def post(self, request):
        es.indices.delete(index=request.POST.get('index'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))


class DeleteData(View):
    def post(self, request):
        es.delete(request.POST.get('index'), request.POST.get('objId'))
        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")


class AddCity(View):
    def post(self, request):
        ms = mediaCity.MediaCity(request.POST.get('code'), request.POST.get('name'), request.POST.get('tz'))
        es.index('cities', ms.__dict__, "city", request.POST.get('id'))
        es.reindex
        time.sleep(1)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))


class AddMedia(View):
    def post(self, request):
        ms = media.Media(request.POST.get('code'), request.POST.get('name'))
        es.index('medias', ms.__dict__, "media", request.POST.get('id'))
        es.reindex
        time.sleep(1)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER','/'))


class AddMediaImport(View):
    def post(self, request):
        jsonData = json.loads(request.body.decode('utf-8'));

        # ms = media.Media(request.POST.get('code'), request.POST.get('name'))
        es.index('medias_import', jsonData, "import_unit")
        # es.reindex
        time.sleep(1)
        return HttpResponse(json.loads(request.body.decode('utf-8')))

class SetActiveMedia(View):
    def post(self, request):
        jsonData = es.get('medias_import', request.POST.get('objId'))
        newvl = 'notActive'
        if(request.POST.get('value') == newvl):
            newvl = 'active'
        jsonData['_source']['city'][0]['state'] = newvl
        es.index('medias_import', jsonData['_source'], "import_unit", request.POST.get('objId'))
        es.reindex
        time.sleep(1)
        return HttpResponse("<KFFF")
