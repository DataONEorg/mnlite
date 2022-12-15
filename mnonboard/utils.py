import json
import subprocess

from defs import DEFAULT_JSON
from mnonboard import L

def default_json():
    """
    A function that spits out a json file to be used in onboarding.
    """
    L.info('Loading default json template.')
    return json.loads(DEFAULT_JSON)

def load_json(loc):
    """
    Load json from file.
    """
    L.info('Loading member node json from %s' % loc)
    try:
        with open(loc, 'r') as f:
            json.load(f)
            L.info('File loaded from %s' % loc)
            return
    except FileNotFoundError as e:
        L.error('File does not exist - %s' % e)
        exit(1)
    except Exception as e:
        L.error('Error: %s' % e)
        exit(1)

def save_json(loc, jf):
    """
    Output json to file.
    """
    L.info('Writing member node json to %s' % loc)
    try:
        with open(loc, 'w') as f:
            json.dump(jf, f)
            L.info('File written to %s' % loc)
            return
    except FileExistsError as e:
        L.error('File exists - %s' % e)
        exit(1)
    except Exception as e:
        L.error('Error: %s' % e)
        exit(1)

def init_repo(loc):
    '''
    Initialize a new instance using opersist.
    '''
    try:
        assert subprocess.call('opersist -f %s init' % (loc)) == 0
    except AssertionError as e:
        L.error('opersist command failed: %s' % e)
        exit(1)
