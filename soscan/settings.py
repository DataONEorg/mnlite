# Scrapy settings for soscan project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "soscan"

SPIDER_MODULES = ["soscan.spiders"]
NEWSPIDER_MODULE = "soscan.spiders"

DATABASE_URL = "postgresql+psycopg2://soscanrw@localhost/soscan"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'soscan (+https://dataone.org/)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Setting fingerprinter implementation to avoid deprecation warning
# https://docs.scrapy.org/en/latest/topics/request-response.html#request-fingerprinter-implementation
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

REACTOR_THREADPOOL_MAXSIZE = 8

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 1
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_REQUESTS_PER_IP = 1

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
  'Accept': 'application/ld+json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    "soscan.middlewares.SoscanSpiderMiddleware": 543,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "soscan.middlewares.SoscanDownloaderMiddleware": 543,
    "scrapy.downloadermiddlewares.redirect.RedirectMiddleware": 543,
    "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": 543,
}

# Whether the Redirect middleware will be enabled
REDIRECT_ENABLED = True

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "soscan.sonormalizepipeline.SoscanNormalizePipeline": 500,
    "soscan.opersistpipeline.OPersistPipeline": 1000,
    #'soscan.pipelines.SoscanPersistPipeline': 1000,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 2
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = True

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 60
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = [500, 501, 502, 503, 510]
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
