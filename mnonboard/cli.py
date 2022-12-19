import os, sys
import getopt

import utils
import info_chx
from defs import CFG, HELP_TEXT
from mnonboard import L
from mnonboard import node_path

def run(cfg):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """
    fields = utils.default_json()
    if cfg['mode'] == 'user':
        # do the full user-driven info gathering process
        ufields, dbinfo = info_chx.user_input()
        fields = info_chx.transfer_info(ufields)
    else:
        # grab the info from a json
        fields = utils.load_json(cfg['json_file'])
        info_chx.input_test(fields)
    # now we're cooking
    # get the node path using the end of the path in the 'subject' field
    loc = node_path(fields['node']['subject'].split('/')[-1])
    # initialize a repository there
    utils.init_repo(loc)
    for f in ('default_owner', 'default_submitter'):
        name = info_chx.orcid_name(fields[f], f)
        utils.new_subject(loc, name, fields[f])


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
