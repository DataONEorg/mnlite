import os, sys
import getopt
import time

from mnonboard import utils
from mnonboard import info_chx
from mnonboard import data_chx
from mnonboard import cn
from mnonboard.defs import CFG, HELP_TEXT, SO_SRVR, CN_SRVR, CN_SRVR_BASEURL, CN_CERT_LOC, APPROVE_SCRIPT_LOC
from mnonboard import default_json, L

def run(cfg):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.

    Args:
        cfg (dict): Dict containing config variables.
    """
    # auth
    if not cfg['token']:
        cfg['token'] = os.environ.get('D1_AUTH_TOKEN')
    if not cfg['token']:
        print('Your DataONE auth token is missing. Please enter it here and/or store it in the env variable "D1_AUTH_TOKEN".')
        cfg['token'] = info_chx.req_input('Please enter your DataONE authentication token: ')
    DC = cn.init_client(cn_url=cfg['cn_url'], auth_token=cfg['token'])
    if cfg['info'] == 'user':
        # do the full user-driven info gathering process
        ufields = info_chx.user_input()
        fields = info_chx.transfer_info(ufields)
    else:
        # grab the info from a json
        fields = utils.load_json(cfg['json_file'])
        info_chx.input_test(fields)
        # still need to ask the user for some names
    # now we're cooking
    # get the node path using the end of the path in the 'subject' field (differs from operation.md documentation)
    end_node_subj = fields['node']['node_id'].split(':')[-1]
    loc = utils.node_path(nodedir=end_node_subj)
    # initialize a repository there (step 5)
    utils.init_repo(loc)
    names = {}
    for f in ('default_owner', 'default_submitter', 'contact_subject'):
        # add a subject for owner and submitter (may not be necessary if they exist already)
        # add subject for technical contact (step 6)
        val = fields[f] if f not in 'contact_subject' else fields['node'][f]
        name = utils.get_or_create_subj(loc=loc, value=val, cn_url=cfg['cn_url'], title=f)
        # store this for a few steps later
        names[val] = name
    # set the update schedule and set the state to up
    fields['node']['schedule'] = utils.set_schedule()
    fields['node']['state'] = 'up'
    # okay, now overwrite the default node.json with our new one (step 8)
    utils.save_json(loc=os.path.join(loc, 'node.json'), jf=fields)
    # add node as a subject (step 7) 
    utils.get_or_create_subj(loc=loc, value=fields['node']['node_id'],
                             cn_url=cfg['cn_url'],
                             name=end_node_subj)
    # restart the mnlite process to pick up the new node.json (step 9)
    utils.restart_mnlite()
    # run scrapy to harvest metadata (step 10)
    if not cfg['local']:
        utils.harvest_data(loc, end_node_subj)
    # now run tests
    data_chx.test_mdata(loc, num_tests=cfg['check_files'])
    # create xml to upload for validation (step 15)
    files = utils.create_names_xml(loc, node_id=fields['node']['node_id'], names=names)
    # uploading xml (proceed to step 14 and ssh to find xml in ~/d1_xml)
    ssh, work_dir, node_id = utils.start_ssh(server=cfg['cn_url'], node_id=fields['node']['node_id'])
    time.sleep(0.5)
    utils.upload_xml(ssh=ssh, files=files, target_dir=work_dir)
    # create and validate the subject in the accounts service (step 16)
    utils.create_subj_in_acct_svc(ssh=ssh, cert=CN_CERT_LOC, files=files, cn=cfg['cn_url'])
    utils.validate_subj_in_acct_svc(ssh=ssh, cert=CN_CERT_LOC, names=names, cn=cfg['cn_url'])
    # download the node capabilities and register the node
    node_filename = utils.dl_node_capabilities(ssh=ssh, baseurl=SO_SRVR[cfg['mode']], node_dir=work_dir, node_id=node_id)
    utils.register_node(ssh=ssh, cert=CN_CERT_LOC, node_filename=node_filename, cn=cfg['cn_url'])
    #utils.approve_node(ssh=ssh, script_loc=APPROVE_SCRIPT_LOC)
    # close connection
    ssh.close()

def main():
    """
    Uses getopt to set config values in order to call run().

    Returns:
        (dict): Config variable dict to use in run().
    """
    # get arguments
    try:
        opts = getopt.getopt(sys.argv[1:], 'hiPvLd:l:c:',
            ['help', 'init', 'production', 'verbose', 'local' 'dump=', 'load=', 'check=']
            )[0]
    except Exception as e:
        L.error('Error: %s' % e)
        print(HELP_TEXT)
        exit(1)
    for o, a in opts:
        if o in ('-h', '--help'):
            # help
            print(HELP_TEXT)
            exit(0)
        if o in ('-i', '--init'):
            # do data gathering
            CFG['info'] = 'user'
        if o in ('-P', '--production'):
            # production case
            CFG['cn_url'] = CN_SRVR_BASEURL % CN_SRVR['production']
            CFG['mode'] = 'production'
        else:
            # testing case
            CFG['cn_url'] = CN_SRVR_BASEURL % CN_SRVR['testing']
            CFG['mode'] = 'testing'
        if o in ('-d', '--dump'):
            # dump default json to file
            utils.save_json(a, default_json())
            exit(0)
        if o in ('-l', '--load'):
            # load from json file
            CFG['info'] = 'json'
            CFG['json_file'] = a
        if o in ('-c', '--check'):
            try:
                CFG['check_files'] = int(a)
            except ValueError:
                if a == 'all': # this should probably not be used unless necessary!
                    CFG['check_files'] = a
                else:
                    L.error('Option -c (--check) requires an integer number of files to check.')
                    print(HELP_TEXT)
                    exit(1)
        if o in ('-L', '--local'):
            CFG['local'] = True
            L.info('Local mode (-L) will not scrape the remote site and will only test local files.')
    L.info('running mnonboard in %s mode.\n\
data gathering from: %s\n\
cn_url: %s\n\
metadata files to check: %s' % (CFG['mode'],
                                CFG['info'],
                                CFG['cn_url'],
                                CFG['check_files']))
    try:
        run(CFG)
    except KeyboardInterrupt:
        print()
        L.error('Caught KeyboardInterrupt, quitting...')
        exit(1)

if __name__ == '__main__':
    main()
