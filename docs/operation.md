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


## Registration with DataONE

Register the node (assumes node document is available at `./mnTestNODE.xml`: 
```
sudo curl --cert /etc/dataone/client/private/urn_node_cnSandboxUCSB1.pem \
-X POST \
-F 'node=@mnTestNODE.xml' \
"https://cn-sandbox-ucsb-1.test.dataone.org/cn/v2/node"
```

Update registration for an already registered node:
```
sudo curl --cert /etc/dataone/client/private/urn_node_cnSandboxUCSB1.pem \
-X PUT \
-F 'node=@mnTestNODE.xml' \
"https://cn-sandbox-ucsb-1.test.dataone.org/cn/v2/node/urn:node:mnTestNODE"
```

Adjust the node properties for the `CN_*` entries:
```
```

Approve the node:
```
sudo java -jar /usr/share/dataone-cn-os-core/d1_cn_approve_node.jar
```

