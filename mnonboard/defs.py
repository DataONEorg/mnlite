

DEFAULT_JSON = r'''{
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

FIELDS = {
    'node_id': ['Member node identifier (must be unique): ', None],
    'name': ['Repository name: ', None],
    'description': ['Repository description: ', None],
    'base_url': ['Base URL of repository: ', None],
    'contact_subject_name': ['Repository technical contact name: ', None],
    'contact_subject': ["Technical contact's ORCiD number: ", None],
    'default_submitter_name': ['Repository submitter name: ', None],
    'default_submitter': ["Submitter's ORCiD number: ", None],
    'default_owner_name': ['Repository owner name: ', None],
    'default_owner': ["Owner's ORCiD number: ", None],
    'num_sitemap_urls': ['Number of sitemap URLs (need at least 1): ', None],
}

FILL_FIELDS = [
    'node_id',
    'node',
    'description',
    'base_url',
    'contact_subject',
    'default_submitter',
    'default_owner',
    'sitemap_urls'
]

SITEMAP_URLS = {
    0: '',
}
