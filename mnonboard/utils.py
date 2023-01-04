import os
import json
import subprocess

from defs import SCHEDULES
from mnonboard import L, NODE_PATH_REL, CUR_PATH_ABS, LOG_DIR, HARVEST_LOG_NAME
from mnonboard.info_chx import record_lookup, enter_schedule

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
        L.info('Using opersist to init new member node folder: %s' % loc)
        subprocess.run(['opersist', '-f', loc, 'init'], check=True)
    except Exception as e:
        L.error('opersist init command failed (node folder: %s): %s' % (loc, e))
        exit(1)

def new_subject(loc, name, value):
    """
    Create new subject in the database using opersist.
    """
    try:
        L.info('opersist creating new subject. Name: %s Value: %s Location: %s' % (name, value, loc))
        subprocess.run(['opersist', '-f', loc, 'sub', '-n', '"%s"' % name, '-s', value], check=True)
    except Exception as e:
        L.error('opersist subject creation command failed for %s (%s): %s' % (name, value, e))
        exit(1)

def get_or_create_subj(loc, name, value, cn_url):
    """
    Get an existing subject using their ORCiD or create a new one with the specified values.
    """
    if not record_lookup(value, cn_url):
        new_subject(loc, name, value)

def set_schedule():
    """
    
    """
    s = enter_schedule()
    return SCHEDULES[s]

def restart_mnlite():
    """
    Subprocess call to restart the mnlite system service. Requires sudo.
    """
    L.info('Restarting mnlite systemctl service...')
    try:
        subprocess.run(['sudo', 'systemctl', 'restart', 'mnlite.service'], check=True)
        L.info('Done.')
    except subprocess.CalledProcessError as e:
        L.error('Error restarting mnlite system service. Is it installed on your system? Error text:\n%s' % (e))
        while True:
            print('mnlite was not restarted.')
            i = input('Do you wish to continue? (Y/n) ')
            if i.lower() == 'n':
                L.info('User has chosen to abort setup after mnlite restart failed.')
                exit(1)
            elif i.lower() in ['y', '']:
                L.info('User has chosen to continue after mnlite restart failed.')
                break
            else:
                L.error('Invalid input at mnlite failure continue prompt: %s' % (i))
                print('You have selected an invalid option.')

def harvest_data(loc, mn_name):
    """
    
    """
    log_loc = os.path.join(LOG_DIR, mn_name + HARVEST_LOG_NAME)
    L.info('Starting scrapy crawl, saving to %s' % (loc))
    L.info('scrapy log location is %s' % (log_loc))
    subprocess.run(['scrapy', 'crawl', 'JsonldSpider',
                    '--set=STORE_PATH=%s' % loc,
                    '--logfile=%s' % log_loc],
                    check=True)
    L.info('scrapy crawl complete.')
