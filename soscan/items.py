# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SoscanItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    status = scrapy.Field()
    time_retrieved = scrapy.Field()
    time_loc = scrapy.Field()
    time_modified = scrapy.Field()
    jsonld = scrapy.Field()

    