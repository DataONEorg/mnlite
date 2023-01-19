import os
import json
import subprocess

from defs import SCHEDULES
from mnonboard import NODE_PATH_REL, CUR_PATH_ABS, LOG_DIR, HARVEST_LOG_NAME, HM_DATE, L
from mnonboard.info_chx import cn_subj_lookup, local_subj_lookup, enter_schedule, orcid_name

def load_json(loc):
    """
    Load json from file.

    Args:
        loc (str): File location of the json file to be loaded.

    Returns:
        j (str): Serialized json file contents.
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

    Args:
        loc (str): File location where the json file is to be written.
        jf (dict): Dictionary to be written as json.

    Returns:
        (No variable is returned)
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

def save_report(rep_str, loc, format='.csv'):
    """
    Output a validation report for a set of metadata.

    Args:
        rep_str (str): Report string to be written.
        loc (str): File location where the report file is to be written.
        jf (dict): File extension (default: .csv).
    """
    fn = os.path.join(loc, 'report-%s%s' % (HM_DATE, format))
    L.info('Writing report to %s' % (fn))
    with open(fn, 'w') as f:
        f.write(rep_str)
    L.info('Done.')

def dumps_json(js):
    """
    Quick and dirty way to output formatted json.

    Args:
        js (dict): Dictionary to be written as json.
    """
    print(json.dumps(js, indent=2))

def node_path(nodepath=NODE_PATH_REL, curpath=CUR_PATH_ABS, nodedir=''):
    """
    Get the absolute path of the nodes directory where new members will go.
    Currently the nodes directory lives at `../instance/nodes/` (relative to
    the mnonboard dir that this file is in).

    Args:
        nodepath (str): Location of the nodes directory relative to the project directory (default: 'instance/nodes/').
        curpath (str): Current absolute path of this function (default: os.path.dirname(os.path.abspath(__file__))).
        nodedir (str): Name of the node directory (example: 'HAKAI_IYS'; default: '')

    Returns:
        (str): Absolute path of the node directory
    """
    return os.path.abspath(os.path.join(curpath, '../', nodepath, nodedir))

def init_repo(loc):
    '''
    Initialize a new instance using opersist.

    Args:
        loc (str): Location of the member node directory in which to initialize an opersist instance.
    '''
    try:
        L.info('Using opersist to init new member node folder: %s' % loc)
        subprocess.run(['opersist',
                        '--folder=%s' % (loc),
                        'init'], check=True)
    except Exception as e:
        L.error('opersist init command failed (node folder: %s): %s' % (loc, e))
        exit(1)

def new_subj(loc, name, value):
    """
    Create new subject in the database using opersist.

    Args:
        loc (str): Location of the opersist instance.
        name (str): Subject name (human readable).
        value (str): Subject value (unique subject id, such as orcid or member node id).
    """
    try:
        L.info('opersist creating new subject. Name: %s Value: %s Location: %s' % (name, value, loc))
        subprocess.run(['opersist',
                        '--folder=%s' % (loc),
                        'sub',
                        '--operation=create',
                        '--name=%s' % name,
                        '--subj=%s' % value], check=True)
    except Exception as e:
        L.error('opersist subject creation command failed for %s (%s): %s' % (name, value, e))
        exit(1)

def get_or_create_subj(loc, value, cn_url, title='unspecified subject', name=False):
    """
    Get an existing subject using their ORCiD or create a new one with the specified values.
    Search is conducted first at the given coordinating node URL, then locally.
    If no subject is found, a new record is created in the local opersist instance.

    Args:
        loc (str): Location of the opersist instance.
        value (str): Subject value (unique subject id, such as orcid or member node id).
        cn_url (str): The base URL of the rest API with which to search for the given subject.
        name (str or bool): Subject name (human readable).
    """
    create = False
    if name:
        # we are probably creating a node record
        L.info('Creating a node subject.')
        create = True
    else:
        # name was not given. look up the orcid record in the database
        name = cn_subj_lookup(subj=value, cn_url=cn_url)
        if not name:
            name = local_subj_lookup(subj=value, loc=loc)
        if not name:
            # if the name is not in either database, we will create it; else it's already there and we ignore it
            L.info('%s does not exist either locally or at %s. Will create a record. Need a name first...' % (value, cn_url))
            # ask the user for a name with the associated position and ORCiD record
            name = orcid_name(value, title)
            create = True
    if create:
        # finally, use opersist to create the subject (sloppy, could create it directly, but this does the same thing)
        new_subj(loc, name, value)

def set_schedule():
    """
    Ask the user what schedule on which they would like to run scrapes.
    Options are: monthly, daily, and every 3 minutes.

    Returns:
        (dict): Dictionary entry formatted based on the chosen schedule option.
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
    Args:
        loc (str): Location of the opersist instance.
        mn_name (str): Name of the member node (used to name the crawl log).
    """
    log_loc = os.path.join(LOG_DIR, mn_name + HARVEST_LOG_NAME)
    L.info('Starting scrapy crawl, saving to %s' % (loc))
    L.info('scrapy log location is %s' % (log_loc))
    try:
        subprocess.run(['scrapy', 'crawl', 'JsonldSpider',
                        '--set=STORE_PATH=%s' % loc,
                        '--logfile=%s' % log_loc],
                        check=True)
        L.info('scrapy crawl complete.')
    except Exception as e:
        L.error('Error running scrapy: %s' % e)

def limit_tests(num_things):
    """
    Ask the user to limit the number of tests to run on a given set of metadata.
    This will execute if the user decides to try and test more than 500 metadata objects.
    The prompt will ask them if they wish to limit the number, then return a
    number based on their decision.

    Args:
        num_things (int): Initial number of things to test.

    Returns:
        num_things (int): Modified number of things to test.
    """
    while True:
        i = input('Testing more than 500 objects is not recommended due to performance concerns.\n\
This may take several minutes and use critical server resources. (est: %s min)\n\
Are you sure you want to test all %s metadata objects in this set? (y/N): ' % (round(num_things/500), num_things))
        if (i.lower() in 'n') or (i.lower() in ''):
            L.info('User has chosen enter a new number of objects to test.')
            while True:
                n = input('Please enter a new number of metadata objects to test: ')
                try:
                    num_things = int(n)
                    break
                except ValueError as e:
                    L.error('User has not entered a number ("%s")' % n)
            if num_things <= 500:
                L.info('User has chosen to test %s metadata objects.' % num_things)
                break
        else:
            L.info('User has chosen to continue testing %s objects.' % (num_things))
            break
    return num_things
