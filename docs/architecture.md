# Architecture

`MNLite` is composed of three principle components: A [`scrapy`](https://scrapy.org/) crawler (`SOScan`), a [`Flask`](https://flask.palletsprojects.com/en/2.0.x/) `HTTP` server and a hybrid SQL-filesystem persistence (`OPersist`). {numref}`mnlite_context`.

```{uml} diagrams/mnlite_context.puml
---
name: mnlite_context
caption: |
  `MNLite` is a JSON-LD crawler that persists extracted content to 
  a local data store and provides a web based user interface and 
  exposes a DataONE Tier-1 Member Node API.
---
```

The principle purpose of `MNLite` is to crawl a dataset collection, gather the presented [JSON-LD](https://www.w3.org/TR/json-ld11/) [`schema.org/Dataset`](https://schema.org/Dataset) metadata, and make the content accessible to the [DataONE infrastructure](https://search.dataone.org/) through a read-only DataONE [Member Node](https://dataoneorg.github.io/api-documentation/apis/MN_APIs.html) service interface.

A single installation of MNLite may harvest from several collections and present each of these as individual Member Node instances.


## Functional Components

The MNLite application is composed of three main functional groups ({numref}`mnlite_container`). The simple web interface is the only publicly exposed component. It provides a mechanism for viewing the harvest content. A crawler called `SOSCan` and based on [Scrapy](https://scrapy.org/) is used to parse [`sitemap.xml`](https://www.sitemaps.org/protocol.html) documents presented by a collection and retrieve JSON-LD from therein referenced landing pages. The crawled content is stored in a persistence layer called `OPersist` (Object Persist). The persistence layer keeps track of details such as the origin of each object (i.e. JSON-LD document), when it was retrieved, and details such as checksums computed on the normalized and un-normalized forms. The persistence layer uses a combination of the file system and an SQL database (SQLite and Postgres are tested) for object storage and metadata.  

```{uml} diagrams/mnlite_container.puml
---
name: mnlite_container
caption: |
  `MNLite` has three main functional elements: 1) `scrapy` is a web harvesting 
  framework that has been customized to traverse a site desribed by sitemap.xml 
  documents and extract JSON-LD metadata from referened pages; 2) `OPersist` is
  a persistence layer for JSON-LD that computes various system level metadata
  properties for JSON-LD documents and stores the content; 3) `MNLite` is a 
  light-weight DataONE Member Node Tier-1 implementation that enables harvest of 
  content in OPersist by DataONE Coordinating Nodes. 
---
```

## Component Detail

`SOScan` is a `Scrapy` implementation customized to crawl `sitemap.xml` documents to retrieve a list of landing page in JSON-LD or HTML containing JSON-LD that in turn contains [`schema.org/Dataset`](https://schema.org/Dataset) entries that conform with the [Science-on-schema.org](https://science-on-schema.org/) guidelines..  

```{uml} diagrams/mnlite_component_soscan.puml
---
name: mnlite_soscan
caption: |
  Major components of the `SOScan` harvesting functionality.
---
```

---- 

MNLite is implemented as a [Flask](https://flask.palletsprojects.com/en/2.0.x/) web application running as a [`uWSGI`](https://uwsgi-docs.readthedocs.io/en/latest/) service under [`nginx`](https://www.nginx.com/). It presents content available in the OPersist data store 

```{uml} diagrams/mnlite_component_mnlite.puml
---
name: mnlist_mnlite
caption: |
  MNLite web application components.
---
```

