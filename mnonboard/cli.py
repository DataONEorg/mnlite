import os, sys
import getopt

import utils
import info_chx
import data_chx
from defs import CFG, HELP_TEXT
from mnonboard import L

def run(cfg):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """
    fields = utils.default_json()
    names = {}
    if cfg['mode'] == 'user':
        # do the full user-driven info gathering process
        ufields, names = info_chx.user_input()
        fields = info_chx.transfer_info(ufields)
    else:
        # grab the info from a json
        fields = utils.load_json(cfg['json_file'])
        info_chx.input_test(fields)
        # still need to ask the user for some names
        f = 'contact_subject'
        names[f+'_name'] = info_chx.orcid_name(fields['node'][f], f)
        for f in ('default_owner', 'default_submitter'):
            names[f+'_name'] = info_chx.orcid_name(fields[f], f)
    # now we're cooking
    # get the node path using the end of the path in the 'subject' field (differs from operation.md documentation)
    end_node_subj = fields['node']['subject'].split('/')[-1]
    loc = utils.node_path(nodedir=end_node_subj)
    # initialize a repository there (step 5)
    utils.init_repo(loc)
    for f in ('default_owner', 'default_submitter'):
        # add a subject for owner and submitter (may not be necessary)
        utils.new_subject(loc=loc, name=names[f+'_name'], value=fields[f])
    f = 'contact_subject'
    # add subject for technical contact (step 6)
    utils.new_subject(loc=loc, name=names[f+'_name'], value=fields['node'][f])
    # add node as a subject (step 7)
    utils.new_subject(loc=loc, name=end_node_subj, value=fields['node']['node_id'])
    # okay, now overwrite the default node.json with our new one (step 8)
    utils.save_json(loc=os.path.join(loc, 'node.json'), jf=fields)
    # restart the mnlite process to pick up the new node.json (step 9)
    utils.restart_mnlite()
    # run scrapy to harvest metadata (step 10)
    utils.harvest_data(loc, end_node_subj)
    # now run tests
    data_chx.test_mdata()


def main():
    """
    Uses getopt to set config values in order to call run().
    """
    # get arguments
    try:
        opts = getopt.getopt(sys.argv[1:], 'hid:l:',
            ['help', 'init', 'dump=', 'load=']
            )[0]
    except Exception as e:
        L.error('Error: %s' % e)
        print(HELP_TEXT)
        exit(1)
    for o, a in opts:
        if o in ('-h', '--help'):
            print(HELP_TEXT)
            exit(0)
        if o in ('-i', '--init'):
            # do data gathering
            CFG['mode'] = 'user'
            run(CFG)
        if o in ('-d', '--dump'):
            # dump default json to file
            utils.save_json(a, utils.default_json())
        if o in ('-l', '--load'):
            # load from json file
            CFG['mode'] = 'json'
            CFG['json_file'] = a
            run(CFG)


if __name__ == '__main__':
    main()
