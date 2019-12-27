from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json, re
from datetime import datetime, timedelta
from django.views.generic import View
from elasticsearch import Elasticsearch
from managePanel.classes import mediaCity, media
import time

es = Elasticsearch()

@csrf_exempt
def offers_list(request):
    source_media = {
        "((авито)|(avito))": "avito",
        "((из рук в руки)|(ирр)|(irr))": "irr",
        "((презент архив)|(архив))": "present_site",
        "((презент сайт)|(презент)|(present))": "present_site",
        "((фарпост)|(farpost))": "farpost",
        "((циан)|(cian))": "cian"
    }

    page = 0
    per_page = 30

    jsonData = json.loads(request.body);
    if jsonData.get('page'):
        page = int(jsonData.get('page'))
    if jsonData.get('per_page'):
        per_page = int(jsonData.get('per_page'))

    sort = jsonData.get('sort')
    search_area = jsonData.get('search_area')
    query = jsonData.get('query')
    rangeFilters = jsonData.get('rangeFilters')
    filter = jsonData.get('filter')
    agent = jsonData.get('agent')

    # print(rangeFilters)
    # print(filter)
    # print(sort)
    # print(agent)

    body = {
        'query': {
            'bool': {
                'must': [],
                'must_not': [],
                'should': [],
                'filter': None
            }
        },
        'sort': [],
        'size': per_page,
        'from': per_page * page
    }

    if filter:
        # filter = json.loads(filter)

        for fltr in filter:
            if filter[fltr] != 'all':
                if fltr == "changeDate" or fltr == "addDate":
                    dt_now = datetime.today()
                    res = datetime(dt_now.year, dt_now.month, dt_now.day, 0, 0, 0) -  timedelta(days=int(filter[fltr]))

                    unix_date = int(time.mktime(res.timetuple()))
                    body['query']['bool']['must'].append({
                                    'range': {
                                        fltr: {
                                            'gte': unix_date
                                        }
                                    }
                        });
                else:
                    body['query']['bool']['must'].append({'term': {fltr: filter[fltr]}})

    if rangeFilters:
        # rangeFilters = json.loads(rangeFilters)
        for fltr in rangeFilters:
            if fltr.get('arrayVal') and len(fltr['arrayVal']) > 0:
                values = []
                if fltr['fieldName'] == "phones":
                    new_query = {'bool': {'should': []}}
                    for val in fltr['arrayVal']:
                        new_query['bool']['should'].append({
                            "match" : {
                                "phonesArray" : {
                                    "query": val,
                                    "operator": "OR",
                                    "boost": 1.0
                                }
                            }
                        })
                    body['query']['bool']['must'].append(new_query)
                elif fltr['fieldName'] == "mediatorCompany":
                    new_query = {'bool': {'should': []}}
                    for val in fltr['arrayVal']:
                        new_query['bool']['should'].append({
                            "match" : {
                                "phonesArray" : {
                                    "query": val,
                                    "operator": "OR",
                                    "boost": 1.0
                                }
                            }
                        })

                        body['query']['bool']['must_not'].append(new_query)

                    if fltr['exactVal'] == 0:
                        body['query']['bool']['must_not'].append({ 'exists': { "field": "mediatorCompany"}})
                    else:
                        body['query']['bool']['must'].append({ 'exists': { "field": "mediatorCompany"}})
                else:
                    for val in fltr['arrayVal']:
                       values.append({
                           "term": { fltr['fieldName']: val }
                       })

                    if len(values):
                        body['query']['bool']['must'].append(
                                {
                                    "bool": {
                                        "minimum_should_match": 1,
                                        "should": values,
                                    }
                                }
                        )
            elif fltr.get('exactVal'):
                body['query']['bool']['must'].append(
                    {
                        "term": {
                            fltr['fieldName']: fltr['exactVal']
                        }
                    }
                )
            else:
               if fltr.get('lowerVal') and fltr.get('upperVal'):
                   body['query']['bool']['must'].append(
                       {
                           'range': {
                               fltr['fieldName']: {
                                   'gte': fltr['lowerVal'],
                                   'lte': fltr['upperVal']
                               }
                           }
                       }
                   )
               elif fltr.get('lowerVal'):
                   body['query']['bool']['must'].append(
                       {
                           'range': {
                               fltr['fieldName']: {
                                   'gte': fltr['lowerVal']
                               }
                           }
                       }
                   )
               elif fltr.get('upperVal'):
                   body['query']['bool']['must'].append(
                       {
                           'range': {
                               fltr['fieldName']: {
                                   'lte': fltr['upperVal']
                               }
                           }
                       }
                   )

    if search_area and len(search_area):
        body['query']['bool']['filter'] = {
                'geo_polygon': {
                    'location_hash': {
                        'points': json.loads(search_area)
                    }
                }
            }

    for regs in source_media:
        res = re.findall(regs, query)
        if len(res) > 0:
            body['query']['bool']['must'].append({
                                                    'term': {
                                                        'sourceMedia':  source_media[regs]
                                                    }
                                                })
            query = re.sub(res[0][0], '', query)
    query = query.strip()
    if query != '' and len(query) > 2:
        body['query']['bool']['must'].append( {
            "match" : {
                "tags" : {
                    "query" : query,
                    "operator": "AND"
                }
            }
        })

        body['query']['bool']['should'].append( {
            "match" : {
                "address" : {
                    "query": query,
                    "operator": "OR",
                    "boost": 4.0
                }
            }
        })

        body['query']['bool']['should'].append( {
            "match" : {
                "description" : {
                    "query": query,
                    "operator": "OR",
                    "boost": 1.0
                }
            }
        })

    if sort:
        # sort = json.loads(sort)
        for str in sort:
            body['sort'].append({str: sort[str]})
    else:
        body['sort'].append({'addDate': { 'order' : 'DESC' }})

    data = es.search(index='results_list', filter_path=['hits.hits._*', 'hits.total.value'], body=body)

    return HttpResponse(json.dumps(data['hits']), content_type="application/json")
