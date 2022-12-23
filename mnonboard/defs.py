from mnonboard import __version__

ORCID_PREFIX = 'https://orcid.org/'

CFG = {
    'info': 'user',
    'json_file': 'node.json',
    'cn_url': 'https://cn-stage.test.dataone.org/cn',
    'mode': 'staging',
}

HELP_TEXT = """DataONE member node onboard script
%s NCEAS/Ian Nesbitt

Usage: cli [ OPTIONS ]
where OPTIONS := {
    -h | --help
            display this help message
    -i | --init
            initialize a new member node from scratch
    -l | --load
            initialize a new member node from a json file
    -d | --dump
            dump default member node json file to configure manually
}
""" % __version__

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
    'node': {
        'node_id': ['Member node identifier (must be unique): ', None],
        'name': ['Repository name: ', None],
        'description': ['Repository description: ', None],
        'base_url': ['Base URL of repository: ', None],
        'subject': ['Path of repository: ', None],
        'contact_subject_name': ['Repository technical contact name: ', None],
        'contact_subject': ["Technical contact's ORCiD number: ", None],
    },
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

SITEMAP_URLS = []

SCHEDULES = {
    # monthly on the 1st at 00:30
    1: {
      "hour": "0",
      "day": "1",
      "min": "30",
      "mon": "*",
      "sec": "0",
      "wday": "?",
      "year": "*"
    },
    # daily at 00:10
    2: {
      "hour": "0",
      "day": "*",
      "min": "10",
      "mon": "*",
      "sec": "0",
      "wday": "?",
      "year": "*"
    },
    # every three minutes
    3: {
      "hour": "*",
      "day": "*",
      "min": "*/3",
      "mon": "*",
      "sec": "0",
      "wday": "?",
      "year": "*"
    }
}