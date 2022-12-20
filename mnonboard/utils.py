import os
import json
import subprocess

from defs import DEFAULT_JSON
from mnonboard import L, NODE_PATH_REL, CUR_PATH_ABS, LOG_DIR, HARVEST_LOG_NAME

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
            j = json.load(f)
            L.info('File loaded from %s' % loc)
            return j
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
            json.dump(jf, f, indent=4)
            L.info('File written to %s' % loc)
            return
    except FileExistsError as e:
        L.error('File exists - %s' % e)
        exit(1)
    except Exception as e:
        L.error('Error: %s' % e)
        exit(1)

def dumps_json(js):
    """
    Quick and dirty way to output formatted json.
    """
    print(json.dumps(js, indent=2))

def node_path(nodepath=NODE_PATH_REL, curpath=CUR_PATH_ABS, nodedir=''):
    """
    Get the absolute path of the nodes directory where new members will go.
    Currently the nodes directory lives at `../instance/nodes/` (relative to
    the mnonboard dir that this file is in).
    """
    return os.path.abspath(os.path.join(curpath, '../', nodepath, nodedir))

def init_repo(loc):
    '''
    Initialize a new instance using opersist.
    '''
    try:
        subprocess.run(['opersist', '-f', loc, 'init'], check=True)
    except Exception as e:
        L.error('opersist init command failed (node folder: %s): %s' % (loc, e))
        exit(1)

def new_subject(loc, name, value):
    try:
        subprocess.run(['opersist', '-f', loc, 'sub', '-n', '"%s"' % name, '-s', value], check=True)
    except Exception as e:
        L.error('opersist subject creation command failed for %s (%s): %s' % (name, value, e))
        exit(1)

def restart_mnlite():
    """
    Subprocess call to restart the mnlite system service. Requires sudo.
    """
    subprocess.run(['sudo', 'systemctl', 'restart', 'mnlite.service'], check=True)

def harvest_data(loc, mn_name):
    """
    
    """
    log_loc = os.path.join(LOG_DIR, mn_name + HARVEST_LOG_NAME)
    subprocess.run(['scrapy', 'crawl', 'JsonldSpider', '-s',
                    'STORE_PATH=%s' % loc, '>', log_loc, '2>&1'])
