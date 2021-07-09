# Operations

Collecting content from a source.

Implemented as a scrapy crawler[^scrapy]. Given a sitemap, crawls and adds discovered `SO:Dataset` entries to the persistence store.

Settings are in `settings.py`

```
workon mnlite
scrapy crawl JsonldSpider  -s STORE_PATH=instance/nodes/mn_3
```

To count sitemap loc entries only:

```
scrapy crawl JsonldSpider -s STORE_PATH=instance/nodes/mnTestDRYAD -L INFO -a count_only=1
```


[^scrapy]: https://docs.scrapy.org/en/latest/index.html