import os, sys
import getopt

from utils import load_json, node_path, init_repo, get_or_create_subj, \
    save_json, restart_mnlite, harvest_data, set_schedule
from info_chx import user_input, transfer_info, input_test
from data_chx import test_mdata
from defs import CFG, HELP_TEXT
from mnonboard import default_json, L

def run(cfg):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """
    if cfg['info'] == 'user':
        # do the full user-driven info gathering process
        ufields = user_input()
        fields = transfer_info(ufields)
    else:
        # grab the info from a json
        fields = load_json(cfg['json_file'])
        input_test(fields)
        # still need to ask the user for some names
    # now we're cooking
    # get the node path using the end of the path in the 'subject' field (differs from operation.md documentation)
    end_node_subj = fields['node']['subject'].split('/')[-1]
    loc = node_path(nodedir=end_node_subj)
    # initialize a repository there (step 5)
    init_repo(loc)
    for f in ('default_owner', 'default_submitter', 'contact_subject'):
        # add a subject for owner and submitter (may not be necessary if they exist already)
        # add subject for technical contact (step 6)
        val = fields[f] if f not in 'contact_subject' else fields['node'][f]
        get_or_create_subj(loc=loc, value=val, cn_url=cfg['cn_url'], title=f)
    # add node as a subject (step 7) 
    get_or_create_subj(loc=loc, value=fields['node']['node_id'],
                             cn_url=cfg['cn_url'],
                             name=end_node_subj)
    # set the update schedule and set the state to up
    fields['node']['schedule'] = set_schedule()
    fields['node']['state'] = 'up'
    # okay, now overwrite the default node.json with our new one (step 8)
    save_json(loc=os.path.join(loc, 'node.json'), jf=fields)
    # restart the mnlite process to pick up the new node.json (step 9)
    restart_mnlite()
    # run scrapy to harvest metadata (step 10)
    if not cfg['local']:
        harvest_data(loc, end_node_subj)
    # now run tests
    test_mdata(loc, num_tests=cfg['check_files'])


def main():
    """
    Uses getopt to set config values in order to call run().
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
            CFG['cn_url'] = 'https://cn.dataone.org/cn'
        if o in ('-d', '--dump'):
            # dump default json to file
            save_json(a, default_json())
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
