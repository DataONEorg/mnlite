

# MNLite

MNLite is a light weight implementation of a Tier-1 DataONE Member Node. It is implemented using Python 3.8+ with [Flask](https://flask.palletsprojects.com/en/1.1.x/), [Scrapy](https://scrapy.org/), [SQLAlchemy](https://www.sqlalchemy.org/), and several other libraries.

## Function

### Overview

MNLite operates as a kind of translating, caching proxy to help DataONE catalog datasets described following the [Science-On-Schema.org](https://science-on-schema.org/) guidelines. 

![](mnlite_01.svg)

MNLite sits between a data repository and the DataONE Coordinating Nodes. It crawls repository landing pages by following sitemaps and extracts JSON-LD metadata from the landing pages. The metadata is parsed, validated, canonicalized, and stored in a persistent cache. 

MNLite exposes a Tier-1 DataONE Member Node API, so a Coordinating Node can discover and retrieve the metadata for subsequent indexing to support discovery and replication for longevity.

### Internal

![](mnlite_02.svg)

MNLite retrieves dataset landing pages from a repository. Any JSON-LD blocks are extracted from the landing pages and filtered to include only `schema.org/Dataset` descriptions that are valid and include the expected properties.

The JSON-LD is transformed in shape to make subsequent processing simpler. The content remains unchanged.
