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
    if cfg['info'] == 'user':
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
        utils.get_or_create_subj(loc=loc,
                                 name=names[f+'_name'],
                                 value=fields[f],
                                 cn_url=cfg['cn_url'])
    f = 'contact_subject'
    # add subject for technical contact (step 6)
    utils.get_or_create_subj(loc=loc,
                             name=names[f+'_name'],
                             value=fields['node'][f],
                             cn_url=cfg['cn_url'])
    # add node as a subject (step 7)
    utils.get_or_create_subj(loc=loc,
                             name=end_node_subj,
                             value=fields['node']['node_id'],
                             cn_url=cfg['cn_url'])
    # set the update schedule
    fields['node']['schedule'] = utils.set_schedule()
    # okay, now overwrite the default node.json with our new one (step 8)
    utils.save_json(loc=os.path.join(loc, 'node.json'), jf=fields)
    # restart the mnlite process to pick up the new node.json (step 9)
    utils.restart_mnlite()
    # run scrapy to harvest metadata (step 10)
    utils.harvest_data(loc, end_node_subj)
    # now run tests
    data_chx.test_mdata(loc)


def main():
    """
    Uses getopt to set config values in order to call run().
    """
    # get arguments
    try:
        opts = getopt.getopt(sys.argv[1:], 'hiPd:l:',
            ['help', 'init', 'production', 'dump=', 'load=']
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
            utils.save_json(a, utils.default_json())
            exit(0)
        if o in ('-l', '--load'):
            # load from json file
            CFG['info'] = 'json'
            CFG['json_file'] = a
    L.info('running mnonboard in %s mode. data gathering from: %s. cn_url: %s' % (CFG['mode'],
                                                                                  CFG['info'],
                                                                                  CFG['cn_url']))
    run(CFG)


if __name__ == '__main__':
    main()
