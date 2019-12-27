def get_map(index):
    mappings = {
        'results_list': {
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 3,
                "max_regex_length": 100000
            },
            "mappings":{
                "properties": {
                    "location_hash": {
                        "type": "geo_point"
                    },
                    "addDate": {
                        "type": "date"
                    },
                    "changeDate": {
                        "type": "date"
                    },
                    "sourceUrl": {
                        "type": "keyword"
                    }
                }
            }
        },
        'source_data': {
            "settings": {
                "number_of_shards" : 5
            },
            "mappings":{
                "properties": {
                    "link": {
                        "type": "keyword"
                    },
                    "city": {
                        "type": "keyword"
                    },
                    "media": {
                        "type": "keyword"
                    }
                }
            }
        },
        'urls_history': {
            "settings": {
                "number_of_shards" : 5
            },
            "mappings":{
                "properties": {
                    "data": {
                        "type": "keyword"
                    },
                    "media": {
                        "type": "keyword"
                    }
                }
            }
        },
        'proxy_list': {
            "settings": {
                "number_of_shards" : 5
            },
            "mappings":{
                "properties": {
                    "ip": {
                        "type": "keyword"
                    },
                    "port": {
                        "type": "keyword"
                    }
                }
            }
        }
    }

    return mappings.get(index)
