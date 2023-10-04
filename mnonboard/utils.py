import os
import json
import subprocess
from paramiko import SSHClient
from scp import SCPClient
import urllib.parse as urlparse
import xmltodict
from pathlib import Path

from mnonboard.defs import SCHEDULES, NAMES_DICT
from mnonboard import NODE_PATH_REL, CUR_PATH_ABS, LOG_DIR, HARVEST_LOG_NAME, HM_DATE, L
from mnonboard.info_chx import cn_subj_lookup, local_subj_lookup, enter_schedule, orcid_name, set_role

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

def get_or_create_subj(loc, value, cn_url, title='unspecified subject', name=None):
    """
    Get an existing subject using their ORCiD or create a new one with the specified values.
    Search is conducted first at the given coordinating node URL, then locally.
    If no subject is found, a new record is created in the local opersist instance.

    Args:
        loc (str): Location of the opersist instance.
        value (str): Subject value (unique subject id, such as orcid or member node id).
        cn_url (str): The base URL of the rest API with which to search for the given subject.
        title (str): The subject's role in relation to the database.
        name (str or bool): Subject name (human readable).
    """
    if name:
        # we are probably creating a node record
        L.info('Creating a node subject.')
    else:
        # name was not given. look up the orcid record in the database
        name = cn_subj_lookup(subj=value, cn_url=cn_url)
        if not name:
            # if the name is not in either database, we will create it; else it's already there and we ignore it
            L.info('%s does not exist at %s. Need a name for local record creation...' % (value, cn_url))
            # ask the user for a name with the associated position and ORCiD record
            name = orcid_name(value, title)
    # finally, use opersist to create the subject
    local_subj_lookup(loc=loc, subj=value, name=name)
    # then use opersist to set the subject's role
    if title in ('default_owner', 'default_submitter'):
        set_role(loc=loc, title=title, value=value)
    return name

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
    while True:
        i = input('Do you wish to restart the mnlite service? (Y/n) ')
        if i.lower() == 'n':
            break
        elif i.lower() in ['y', '']:
            L.info('Restarting mnlite systemctl service...')
            try:
                subprocess.run(['sudo', 'systemctl', 'restart', 'mnlite.service'], check=True)
                L.info('Done.')
                break
            except subprocess.CalledProcessError as e:
                L.error('Error restarting mnlite system service. Is it installed on your system? Error text:\n%s' % (e))
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
        else:
            L.error('Invalid input at mnlite prompt: %s' % (i))
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

def ask_continue(msg: str):
    """
    A user input loop in which the user is prompted whether they want to continue.

    :param str msg: The message to display at the prompt.
    """
    while True:
        i = input(msg + ' (Y/n) ')
        if i.lower() in 'y':
            # this also implicitly matches an empty string (i.e. user presses enter)
            L.info('Continuing.')
            break
        elif (i.lower() in 'n'):
            L.info('Exiting.')
            exit(1)
        else:
            L.info('User has not entered "y" or "n".')
            print('You have entered an incorrect value. Please enter "y" to continue or "n" to quit.')
            continue

def create_names_xml(loc, node_id, names):
    """
    Format subject XML documents and return list of names.

    Args:
        loc (str): Location (dir) to write file to.
        node_id (str): Node id of current MN.
        names (dict): Dict of subject names with ORCiD as index.

    Returns:
        files (list): List of files written.
    """
    # make dir
    loc = os.path.join(loc, 'xml')
    try:
        os.makedirs(loc, exist_ok=True)
    except OSError as e:
        L.error('OSError creating XML directory: %s' % (e))
        exit(1)
    except Exception as e:
        L.error('%s creating XML directory: %s' % (repr(e), e))
        exit(1)
    # format NAMES_XML
    node_id = node_id.split(':')[-1]
    files = []
    for id in names:
        namesplit = names[id].split()
        first, last = namesplit[0], namesplit[-1]
        xd = NAMES_DICT
        xd['ns2:person']['subject'] = id
        xd['ns2:person']['givenName'] = first
        xd['ns2:person']['familyName'] = last
        fn = os.path.join(loc, '%s_%s%s.xml' % (node_id, first[0], last))
        with open(fn, 'w') as f:
            xmltodict.unparse(xd, output=f)
        L.debug('XML path: %s' % fn)
        files.append(fn)
    return files

def write_cmd_to(fn, cmd, desc=None, mode='a'):
    """
    """
    desc = f"# {desc}\n" if desc else ""
    with open(fn, mode) as f:
        f.write(f"{desc}{cmd}\n")

def start_ssh(server: str, node_id, loc: str, ssh: bool=True):
    """
    """
    server = server.split('https://')[1].split('/')[0]
    node_id = node_id.split(':')[-1]
    xml_dir = '~/d1_xml/%s' % (node_id)
    local_xml_dir = f'{loc}/xml'
    mkdir_cmd = 'mkdir -p %s' % (xml_dir)
    cd_cmd = 'cd %s' % xml_dir
    op = f'connection to {server}'
    if not ssh:
        return None, local_xml_dir, node_id
    try:
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(server)
        L.info('Running "%s" on %s' % (mkdir_cmd, server))
        op = f'mkdir on {server}'
        ssh.exec_command(mkdir_cmd)
        L.info('Running "%s" on %s' % (cd_cmd, server))
        op = f'cd on {server}'
        ssh.exec_command(cd_cmd)
        return ssh, xml_dir, node_id
    except Exception as e:
        L.error('%s running %s. Details: %s' % (repr(e), op, e))
        return None, local_xml_dir, node_id

def upload_xml(ssh: SSHClient, files: list, node_id: str, loc: str, server: str=None):
    """
    Format subject XML documents and return list of names.
    cmd_fn = f"{loc}/commands.sh"

    Args:
        files (list): List of files to upload.
    """
    op = ''
    target_dir = f'~/d1_xml/{node_id}/'
    try:
        op = 'mkdir on remote server'
        if ssh:
            with SCPClient(ssh.get_transport()) as scp:
                op = 'scp to remote server'
                L.info('Copying files to remote %s : %s' % (target_dir, files))
                scp.put(files=files, remote_path=target_dir)
        else:
            cmd_fn = f"{loc}/commands.sh"
            write_cmd_to(fn=cmd_fn, cmd=f'mkdir -p {target_dir}', desc='# Copy xml files from so server to cn', mode='w')
            write_cmd_to(fn=cmd_fn, cmd=f'cd {target_dir}')
            for f in files:
                command = f"scp {server}:{f} {target_dir}"
                write_cmd_to(fn=cmd_fn, cmd=command)
    except Exception as e:
        L.error('%s running %s. Details: %s' % (repr(e), op, e))
        exit(1)

def create_subj_in_acct_svc(ssh: SSHClient, cert: str, files: list, cn: str, loc: str):
    """
    """
    cmd_fn = f"{loc}/commands.sh"
    for f in files:
        f = os.path.split(f)[1]
        command = 'sudo curl -s --cert %s -F person=@%s -X POST %s/v2/accounts' % (
            cert, f, cn
        )
        if ssh:
            L.info('Creating subject: %s' % (command))
            ssh.exec_command(command)
        else:
            L.debug(f'Command: {command}')
            L.info(f'Writing cmd to {cmd_fn}: subject creation')
            write_cmd_to(fn=cmd_fn, cmd=command, desc=f"Create subject: {f}")

def validate_subj_in_acct_svc(ssh: SSHClient, cert: str, names: dict, cn: str, loc: str):
    """
    """
    cmd_fn = f"{loc}/commands.sh"
    for n in names:
        orcid_urlenc = urlparse.quote(n, safe='-')
        command = 'sudo curl -s --cert %s -X PUT %s/v2/accounts/verification/%s' % (
            cert, cn, orcid_urlenc
        )
        if ssh:
            L.info('Validating subject: %s' % (command))
            ssh.exec_command(command)
        else:
            L.debug(f'Command: {command}')
            L.info(f'Writing cmd to {cmd_fn}: subject validation')
            write_cmd_to(fn=cmd_fn, cmd=command, desc=f"Validate subject: {n}")

def dl_node_capabilities(ssh: SSHClient, baseurl: str, node_dir: str, node_id: str, loc: str):
    """
    """
    cmd_fn = f"{loc}/commands.sh"
    node_filename = '%s/%s-node.xml' % (node_dir, node_id)
    command = 'sudo curl "https://%s/%s/v2/node" > %s' % (baseurl, node_id, node_filename)
    if ssh:
        L.info('Downloading node capabilities: %s' % (command))
        ssh.exec_command(command)
    else:
        L.info(f'Writing cmd to {cmd_fn}: node capabilities')
        L.debug(f'Command: {command}')
        write_cmd_to(fn=cmd_fn, cmd=command, desc=f"Download {node_id} node capabilities")
    return node_filename

def register_node(ssh: SSHClient, cert: str, node_filename: str, cn: str, loc: str):
    """
    """
    cmd_fn = f"{loc}/commands.sh"
    node_filename = os.path.split(node_filename)[1]
    mn = node_filename.split('-')[0]
    command = """sudo curl --cert %s -X POST -F 'node=@%s' "%s/v2/node" """ % (
        cert, node_filename, cn
    )
    if ssh:
        L.info('Registering node: %s' % (command))
        ssh.exec_command(command)
    else:
        L.info(f'Writing cmd to {cmd_fn}: node registration')
        L.debug(f'Command: {command}')
        write_cmd_to(fn=cmd_fn, cmd=command, desc=f"Register {node_filename} with CN")

def approve_node(ssh: SSHClient, script_loc: str, loc: str):
    """
    """
    cmd_fn = f"{loc}/commands.sh"
    command = 'sudo %s' % (script_loc)
    if ssh:
        L.info('Starting approval script: %s' % (command))
        ssh.exec_command(command)
    else:
        L.info(f'Writing to {cmd_fn}: node approval')
        write_cmd_to(fn=cmd_fn, cmd=command, desc="Approve node with CN (interactive script)")
