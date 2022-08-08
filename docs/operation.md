# MN Lite Operations 

MN Lite collects schema.org content from a source, and registers it in a local sqlite database, do be served via the DataONE API.

Harvesting is implemented as a scrapy crawler[^scrapy]. Given a sitemap, crawls and adds discovered `SO:Dataset` entries to the persistence store.

[^scrapy]: https://docs.scrapy.org/en/latest/index.html

## DataONE production and testing hosts

- Test server: so.test.dataone.org
    - Environment: ~vieglais
    - Virtual env: mnlite
- Production server: sonode.dataone.org
    - Environment: ``~mnlite`
    - Virtual env: `mnlite`

## Testing

- Prerequisite: Content follows SOSO guidelines
    - Validation: https://shacl-playground.zazuko.com/
    - [SOSO SHACL file](https://github.com/ESIPFed/science-on-schema.org/blob/develop/validation/shapegraphs/soso_common_v1.2.3.ttl)

## Production Deployment

1. Log in to sonode.dataone.org (or so.test.dataone.org for testing)
2. `sudo su - mnlite`
3. `workon mnlite`
4. `cd WORK/mnlite`
5. Initialize a new repository: `opersist -f instance/nodes/HAKAI_IYS init`
6. Create a contact subject: `opersist -f instance/nodes/HAKAI_IYS sub -o create -n "Brett Johnson" -s "http://orcid.org/0000-0001-9317-0364"`
7. Create a node subject: `opersist -f instance/nodes/HAKAI_IYS sub -o create -n "HAKAI_IYS" -s "urn:node:HAKAI_IYS"`
8. Edit the node.json document to set the contact and node id and other metadata details like description
    - `vim instance/nodes/mnTestHAKAI_IYS/node.json`
```json
{
  "node": {
    "node_id": "urn:node:HAKAI_IYS",
    "state": "up",
    "name": "International Year of the Salmon Catalogue",
    "description": "The repository contains data collected and rescued by the International Year of the Salmon project facilitated by the North Pacific Anadromous Fish Commission. The repository primarily contains physical and biogeochemical oceanographic data and fisheries trawl catch data describing salmon abundance and environmental conditions in the North Pacific Ocean collected from research expeditions in 2019, 2020, and 2022.",
    "base_url": "https://sonode.dataone.org/HAKAI_IYS/",
    "schedule": {
      "hour": "*",
      "day": "*",
      "min": "1,11,21,31,41,51",
      "mon": "*",
      "sec": "5",
      "wday": "?",
      "year": "*"
    },
    "subject": "urn:node:HAKAI_IYS",
    "contact_subject": "http://orcid.org/0000-0001-9317-0364"
  },
  "content_database": "sqlite:///content.db",
  "log_database": "sqlite:///eventlog.db",
  "data_folder": "data",
  "created": "2022-08-05T17:50:36+0000",
  "default_submitter": "http://orcid.org/0000-0001-9317-0364",
  "default_owner": "http://orcid.org/0000-0001-9317-0364",
  "spider": {
    "sitemap_urls":[
      "https://iys.hakai.org/sitemap/sitemap.xml"
    ]
  }
}

```
9. `sudo systemctl restart mnlite`
    - Node document is available from https://sonode.dataone.org/HAKAI_IYS/v2/node
11. Run first harvest
    - `scrapy crawl JsonldSpider  -s STORE_PATH=instance/nodes/HAKAI_IYS > /var/log/mnlite/HAKAI_IYS-crawl-01.log 2>&1`
12. Set up a cron job for harvest
- To use the venv, need to be sure to use bash and not sh
- `crontab -e`
```
SHELL=/bin/bash
20 * * * * cd ~/WORK/mnlite && workon mnlite && scrapy crawl JsonldSpider -s STORE_PATH=instance/nodes/HAKAI_IYS >> /var/log/mnlite/HAKAI_IYS-crawl-01.log 2>&1
```

## Register node in production and approve node

14. SSH to cn-ucsb-1.dataone.org (or cn-stage-ucsb-1.test.dataone.org for testing)

Execute the following commands on the CN.

### Add the user to the accounts service

15. Create an XML doc for the subject of this format:
```xml
$ cat hakai-bjohnson.xml
<?xml version="1.0" encoding="UTF-8"?>
<ns2:person xmlns:ns2="http://ns.dataone.org/service/types/v1">
  <subject>http://orcid.org/0000-0001-9317-0364</subject>
  <givenName>Brett</givenName>
  <familyName>Johnson</familyName>
  <verified>false</verified>
</ns2:person>
```

16. Create and validate the subject in the accounts service
- `$ curl -s --cert /etc/dataone/client/private/urn_node_cnStageUCSB1.pem -F person=@hakai-bjohnson.xml -X POST "https://cn-stage.test.dataone.org/cn/v2/accounts"`
- `$ curl -s --cert /etc/dataone/client/private/urn_node_cnStageUCSB1.pem -X PUT  "https://cn-stage.test.dataone.org/cn/v2/accounts/verification/http%3A%2F%2Forcid.org%2F0000-0001-9317-0364"`

18. Download the node capabilities doc and register the node, and then approve the node in DataONE
- `$ curl "https://sonode.dataone.org/HAKAI_IYS/v2/node" > hakai-node.xml`
- `$ sudo curl --cert /etc/dataone/client/private/urn_node_cnStageUCSB1.pem -X POST -F 'node=@hakai-node.xml' "https://cn-stage-ucsb-1.test.dataone.org/cn/v2/node"`

```
$ sudo /usr/local/bin/dataone-approve-node
Choose the number of the Certificate to use
0)	urn_node_cnStageUCSB1.pem
1)	urn:node:cnStageUCSB1.pem
0
[ WARN] 2022-05-05 03:27:54,071 (CertificateManager:<init>:203) FileNotFound: No certificate installed in the default location: /tmp/x509up_u0
May 05, 2022 3:27:54 AM com.hazelcast.client.LifecycleServiceClientImpl
INFO: HazelcastClient is STARTING
May 05, 2022 3:27:54 AM com.hazelcast.client.LifecycleServiceClientImpl
INFO: HazelcastClient is CLIENT_CONNECTION_OPENING
May 05, 2022 3:27:54 AM com.hazelcast.client.LifecycleServiceClientImpl
INFO: HazelcastClient is CLIENT_CONNECTION_OPENED
May 05, 2022 3:27:54 AM com.hazelcast.client.LifecycleServiceClientImpl
INFO: HazelcastClient is STARTED
Pending Nodes to Approve
0) urn:node:mnStageORC1	1) urn:node:mnStageLTER	2) urn:node:mnStageCDL	3) urn:node:USGSCSAS
4) urn:node:ORNLDAAC	5) urn:node:mnTestTFRI	6) urn:node:mnTestUSANPN	7) urn:node:TestKUBI
8) urn:node:EDACGSTORE	9) urn:node:mnTestDRYAD	10) urn:node:DRYAD	11) urn:node:mnTestGLEON
12) urn:node:mnDemo11	13) urn:node:mnTestEDORA	14) urn:node:mnTestRGD	15) urn:node:mnTestIOE
16) urn:node:mnTestNRDC	17) urn:node:mnTestNRDC1	18) urn:node:mnTestPPBIO	19) urn:node:mnTestUIC
20) urn:node:mnTestFEMC	21) urn:node:mnTestHAKAI_IYS
Type the number of the Node to verify and press enter (return):
21
Do you wish to approve urn:node:mnTestHAKAI_IYS (Y=yes,N=no,C=cancel)
Y
Node Approved in LDAP
Hazelcast Node Topic published to. Approval Complete
```

:tada: :tada: :tada:

