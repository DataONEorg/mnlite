# Operation

## Sitemap crawl configuration sample

Node configuration (`NODE_DIR/node.json`):

```json
{
    "node": {
        "node_id": "urn:node:mnTestHD",
        "state": "up",
        "name": "Harvard Dataverse",
        "description": "The Harvard Dataverse Repository is a free data repository open to all researchers from any discipline, both inside and outside of the Harvard community, where you can share, archive, cite, access, and explore research data. Each individual Dataverse collection is a customizable collection of datasets (or a virtual repository) for organizing, managing, and showcasing datasets.",
        "base_url": "https://so.test.dataone.org/mnTestHD",
        "schedule": {
            "hour": "*",
            "day": "*",
            "min": "*/3",
            "mon": "*",
            "sec": "0",
            "wday": "?",
            "year": "*"
        },
        "subject": "CN=urn:node:mnTestHD,DC=dataone,DC=org",
        "contact_subject": "http://orcid.org/0000-0001-5828-6070"
    },
    "content_database": "sqlite:///content.db",
    "log_database": "sqlite:///eventlog.db",
    "data_folder": "data",
    "created": "2023-08-14T14:35:09+0000",
    "default_submitter": "http://orcid.org/0000-0001-5828-6070",
    "default_owner": "http://orcid.org/0000-0001-5828-6070",
    "spider": {
        "sitemap_urls": [
            "https://raw.githubusercontent.com/DataONEorg/mnlite/develop/tests/testHDsitemap.xml"
        ]
    }
}
```

Sync script (`NODE_DIR/sync_content.sh`):

```bash
#!/bin/bash

NODE="mnTestHD"

HOME_DIR="/home/mnlite"
MNLITE_DIR="${HOME_DIR}/WORK/mnlite"
NODE_DIR="${MNLITE_DIR}/instance/nodes/${NODE}"

ENV_DIR="${HOME_DIR}/.virtualenvs/mnlite"
LOG_DIR="/var/log/mnlite"

cd "${MNLITE_DIR}"
source "${ENV_DIR}/bin/activate"
LOG_FILE="${LOG_DIR}/${NODE}-crawl.log"
mkdir -p ${LOG_DIR}
touch ${LOG_FILE}
echo "${date} Start crawl on: ${NODE} logfile: ${LOG_FILE}" >> ${LOG_FILE}
scrapy crawl --logfile=${LOG_FILE} JsonldSpider -s STORE_PATH=${NODE_DIR}
echo "${date} End crawl on ${NODE}" >> ${LOG_FILE}
```

Settings file (`NODE_DIR/settings.json`):

```json
{
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1,
    "DOWNLOAD_DELAY": 1,
    "LOG_LEVEL": "DEBUG"
}
```


## API crawl configuration sample

Use `node.json` for source URL(s) in `spider.sitemap_urls`, even when the source is an API endpoint.

Example `node.json` snippet (see above for full example):

```json
{
  ...
  "spider": {
    "sitemap_urls": [
      "https://example.org/api/datasets"
    ]
  }
}
```

Select the spider class in `settings.json`.

### API with explicit "next" URL in response body

```json
{
  "SPIDER_CLASS": "APIJsonldSpider",
  "api_records_path": "items",
  "api_next_path": "next",
  "api_jsonld_field": "jsonld",
  "api_url_field": "url",
  "api_modified_field": "modified"
}
```

### API with fixed page size and incremental `page` parameter

```json
{
  "SPIDER_CLASS": "APIJsonldSpider",
  "api_records_path": "items",
  "api_jsonld_field": "jsonld",
  "api_url_field": "url",
  "api_modified_field": "modified",
  "api_page_param": "page",
  "api_start_page": 1,
  "api_stop_status_codes": [404]
}
```

In page-parameter mode, mnlite requests page 1, 2, 3, ... and stops either when it receives a stop status (e.g. 404) or when a successful page returns no records.
The query URLs are built as: `https://example.org/api/datasets?page=1`, `?page=2`, etc.

### Working example: Polar Data Catalogue

The PDC API at `https://polardata.ca/api/metadata?page=0` returns a schema.org
`ItemList` where each element is a `ListItem` wrapping a `Dataset`. The `@context`
is placed once on the envelope, not on individual records — the spider automatically
propagates it down to each extracted `Dataset`.

`node.json` — spider section:

```json
"spider": {
  "sitemap_urls": [
    "https://polardata.ca/api/metadata"
  ]
}
```

`settings.json`:

```json
{
  "SPIDER_CLASS": "APIJsonldSpider",
  "api_records_path": "itemListElement",
  "api_jsonld_field": "item",
  "api_url_field": "item.url",
  "api_modified_field": "item.dateModified",
  "api_page_param": "page",
  "api_start_page": 0,
  "api_stop_status_codes": [404, 204]
}
```

The spider requests `?page=0`, `?page=1`, ... until an empty page or a 404 is received.
