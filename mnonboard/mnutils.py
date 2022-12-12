import json
import pyshacl

def default_json():
	"""
	A function that spits out a json file to be used in onboarding.
	"""
    jstr = r'''{
  "node": {
    "node_id": "",
    "state": "up",
    "name": "",
    "description": "",
    "base_url": "",
    "schedule": {
      "hour": "*",
      "day": "*",
      "min": "0,10,20,30,40,50",
      "mon": "*",
      "sec": "0",
      "wday": "?",
      "year": "*"
    },
    "subject": "",
    "contact_subject": ""
  },
  "data_folder": "data",
  "content_database": "sqlite:///content.db",
  "log_database": "sqlite:///eventlog.db",
  "created": "",
  "default_submitter": "",
  "default_owner": "",
  "spider": {
    "sitemap_urls":[
      ""
    ]
  }
}
'''
    return json.loads(jstr)
