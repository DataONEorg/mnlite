# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import logging
import copy
import sqlalchemy.exc
import opersist
import scrapy.exceptions


class SoscanPersistPipeline:
    def __init__(self, db_url):
        self._op = opersist.OPersist()

        self.db_url = db_url
        self.merge_existing = True
        self.logger = logging.getLogger("SoscanPersist")
        self._engine = None
        self._session = None
        self._engine = soscan.models.getEngine(self.db_url)

    @classmethod
    def from_crawler(cls, crawler):
        db_url = crawler.settings.get("DATABASE_URL", None)
        return cls(db_url)

    def open_spider(self, spider):
        self.logger.debug("open_spider")
        self._op.open(allow_create=True)
        if self._engine is None:
            return
        self._session = soscan.models.getSession(self._engine)
        # If the spider does not have a lastmod_filter, then
        # get the most recent lastmod from the database, and
        # set the spider lastmod_filter to that time. A re-harvest
        # can be done by setting the lastmod property to an old
        # date.
        if spider.lastmod_filter is None:
            rec = (
                self._session.query(soscan.models.SOContent)
                .order_by(soscan.models.SOContent.time_loc.desc())
                .first()
            )
            spider.lastmod_filter = rec.time_loc
            self.logger.debug("Set crawl start date to: %s", rec.time_loc)

    def close_spider(self, spider):
        self.logger.debug("close_spider")
        if self._session is not None:
            self._session.close()

    def process_item(self, item, spider):
        try:
            soitem = soscan.models.SOContent(
                url=item["url"],
                http_status=item["status"],
                time_retrieved=item["time_retrieved"],
                time_loc=item["time_loc"],
                time_modified=item["time_modified"],
                jsonld=item["jsonld"],
            )
            exists = self._session.query(soscan.models.SOContent).get(soitem.url)
            if exists:
                self.logger.debug("EXISTING content: %s", soitem.url)
                if self.merge_existing:
                    try:
                        merged = self._session.merge(soitem)
                        self._session.commit()
                    except Exception as e:
                        self.logger.warning(
                            "Could not merge '%s' because %s", soitem.url, e
                        )
            else:
                self.logger.debug("NEW content: %s", soitem.url)
                try:
                    self._session.add(soitem)
                    self._session.commit()
                except sqlalchemy.exc.IntegrityError as e:
                    self.logger.warning("Could not add '%s' because %s", soitem.url, e)
        except Exception as e:
            self.logger.error(e)
        return item
