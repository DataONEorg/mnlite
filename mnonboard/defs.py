from mnonboard import __version__

ORCID_PREFIX = 'http://orcid.org/'
SHACL_URL = 'https://raw.githubusercontent.com/ESIPFed/science-on-schema.org/master/validation/shapegraphs/soso_common_v1.2.3.ttl'
NODE_ID_PREFIX = 'urn:node:'

CFG = {
    'info': 'user',
    'json_file': 'node.json',
    'cn_url': 'https://cn-stage.test.dataone.org/cn',
    'mode': 'testing',
    'check_files': 5,
    'local': False,
}

CN_SRVR = {
    'production': 'cn.dataone.org',
    'testing': 'cn-stage.test.dataone.org'
}

CN_SRVR_BASEURL = 'https://%s/cn'

HELP_TEXT = """DataONE member node onboard script
%s NCEAS/Ian Nesbitt

Usage: cli [ OPTIONS ]
where OPTIONS := {
    -c | --check=[ NUMBER ]
            number of random metadata files to check for schema.org compliance
    -d | --dump=[ FILE ]
            dump default member node json file to configure manually
    -h | --help
            display this help message
    -i | --init
            initialize a new member node from scratch
    -l | --load=[ FILE ]
            initialize a new member node from a json file
    -P | --production
            run this script in production mode (uses the D1 cn API in searches)
    -L | --local
            run this script in local mode (will not scrape the remote site for new metadata)
}
""" % __version__

FIELDS = {
    'node': {
        'node_id': ['Member node_id (must be unique): ', None],
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

SHACL_ERRORS = {
  'essential': {
    # load errors
    'ShapeLoadError': 'Shape graph must load correctly',
    'JSONDecodeError': 'Metadata files must be properly formatted json-ld',
    # science-on-schema.org violations
    'soso:IDShape': 'Dataset must have an ID',
    # schema.org violations
    'SO:Dataset-description': 'Dataset must have a description',
    'SO:Dataset-identifier': 'Dataset identifiers must be a URL, Text or PropertyValue',
    'SO:Dataset-name': 'Name is required for a Dataset',
    'SO:Dataset-url': 'Dataset requires a URL for the location of a page describing the dataset',
  },
  'optional': {
    # science-on-schema.org violations
    'soso:DatasetNS1Shape': 'Expecting SO namespace of <http://schema.org/> not <https://schema.org/>',
    'soso:DatasetNS2Shape': 'Expecting SO namespace of <http://schema.org/> not <https://schema.org/>',
    'soso:DatasetNS3Shape': 'Expecting SO namespace of <http://schema.org/> not <https://schema.org/>',
    # schema.org violations
    'SO:Dataset-isAccessibleForFree': 'It is recommended that a Dataset indicates accessibility for free or otherwise',
    'SO:Dataset-keywords': 'A Dataset should include descriptive keywords as literals or DefinedTerm',
    'SO:Dataset-sameAs': 'It is recommended that a Dataset includes a sameAs URL',
    'SO:Dataset-version': 'Dataset must have a version as Literal or Number',
    # SO coordinates
    'schema:GeoCoordinates-longitude': 'It is recommended that a Dataset has a longitude coordinate in WGS-84 format',
    'schema:GeoCoordinates-latitude': 'It is recommended that a Dataset has a latitude coordinate in WGS-84 format',
  },
  'internal': {
    # errors we at NCEAS had testing data
    'ConstraintLoadError': 'Constraints must load correctly',
    'ReportableRuntimeError': 'No errors can occur at runtime',
    'FileNotFoundError': 'Files must exist in the location specified',
  }
}

NAMES_DICT = {
    'ns2:person': {
        '@xmlns:ns2': 'http://ns.dataone.org/service/types/v1',
        'subject': '',
        'givenName': '',
        'familyName': '',
        'verified': 'false'
    }
}
