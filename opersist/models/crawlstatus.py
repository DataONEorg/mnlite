import logging
import os
import time
import ojson as json
import dateparser
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import sqlalchemy.exc
import sqlalchemy.event

class CrawlInfo(opersist.models.Base):
    '''
    Info about a crawl
    
    id
    sitemap_url
    scrapy_stats - JSON
    '''
    __tablename__ = "crawlinfo"
    _id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        doc="Integer key for a crawl",
    )
    sitemap_url = sqlalchemy.Column(
        sqlalchemy.String,
        index=True,
        default=None,
        doc="Sitemap crawled",
    )
    scrapy_stats = sqlalchemy.Column(
        sqlalchemy.JSON(sqlalchemy.String),
        default={},
        doc="Statistics returned by the Scrapy engine",
    )

class CrawlStatus(opersist.models.Base):
    '''
    Status of a crawl operation

    crawl_id
    url
    timestamp
    status
    info - JSON
    '''
    __tablename__ = "crawlstatus"

    url = sqlalchemy.Column(
        sqlalchemy.String,
        primary_key=True,
        doc="URL harvested"
    )
    t = sqlalchemy.Column(
        sqlalchemy.DateTime(timezone=True),
        default=opersist.utils.dtnow,
        doc="When the content was accessed",
    )
    status = sqlalchemy.String(
        index=True,
        default="UNKNOWN",
        doc="Status string for response"
    )
    info = sqlalchemy.Column(
        sqlalchemy.JSON(sqlalchemy.String),
        default = None,
        doc="Information about the item retrieval"
    )
    crawl_info_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey("crawlinfo._id")
    )
    crawl_info = sqlalchemy.orm.relationship("CrawlInfo", foreign_keys=[crawl_info_id])

