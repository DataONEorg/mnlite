import os
import sonormal
import pyld
import email.utils
import json
import soscan.items
import soscan.utils

class RawJsonLDSpider(soscan.spiders.ldsitemapspider.LDSitemapSpider):

    name = "RawJsonLDSpider"

    def parse(self, response, **kwargs):
        options = {
            "extractAllScripts": True,
            "json_parse_strict": False,
        }
        jsonld = pyld.jsonld.load_html(response.body, response.url, None, options)
        if len(jsonld) > 0:
            item = soscan.items.JsonLDItem()
            item['time_loc'] = response.meta.get('loc_timestamp', None)
            item['source'] = response.meta.get('loc_source', None)
            item['changefreq'] = response.meta.get('loc_changefreq', None)
            item['priority'] = response.meta.get('loc_priority', None)
            item['jsonld'] = jsonld
            item['elapsed'] = response.meta.get('download_latency', None)
            yield item
        else:
            yield None

