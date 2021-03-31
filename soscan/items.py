# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SoscanItem(scrapy.Item):
    '''
    Set all the properties on a json-ld thing.

    All properties that need to be preserved in the database etc should be set here
    '''
    url = scrapy.Field()
    status = scrapy.Field() #http status
    time_retrieved = scrapy.Field()
    time_loc = scrapy.Field() # From the sitemap, if available
    time_modified = scrapy.Field() # From the HTTP response header, if available
    time_dsmodified = scrapy.Field() #dateModified value in JSON-LD object, if availale
    jsonld = scrapy.Field() # The JSON-LD object (de-serialized)
    normalized = scrapy.Field() # the normalized JSON-LD object
    identifier = scrapy.Field() # PID to be used for the item
    series_id = scrapy.Field() # Series ID to be used for the item
    alt_identifiers = scrapy.Field() # alternative identifiers extracted from the item
    format_id = scrapy.Field()
