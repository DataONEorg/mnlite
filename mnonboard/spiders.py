from scrapy import Spider
from scrapy.crawler import CrawlerProcess

from mnonboard import L

class OrcidSpider(Spider):
    name = "orcid_name_spider"
    allowed_domains = ["orcid.org"]
    logging = L

    def parse(self, response):
        self.orcid_name = response.xpath('//h1[@class="name orc-font-heading-small"]/text()').extract()
        self.logging.info('Found name from ORCiD record: %s' % self.orcid_name)
