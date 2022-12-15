import os, sys
import subprocess
import getopt

import utils
import info_chx
from defs import CFG, HELP_TEXT
from mnonboard import L
from opersist.cli import getOpersistInstance


def init_repo(loc):
    '''
    Initialize a new instance using opersist.
    '''
    subprocess.call('opersist -f %s' % (loc))


def run(cfg):
    """
    Wrapper around opersist that simplifies the process of onboarding a new
    member node to DataONE.
    """
    if cfg['load_json'] is False:
        # do the full user-driven info gathering process
        fields = info_chx.user_input()
    else:
        # grab the info from a json
        fields = utils.load_json(cfg['json_file'])
        info_chx.input_test(fields)


def main():
    """
    Uses getopt to set config values in order to call run().
    """
    # get arguments
    try:
        opts = getopt.getopt(sys.argv[1:], 'hid:l:',
            ['help', 'init', 'dump=' 'load=']
            )[0]
    except Exception as e:
        L.error('Error: %s' % e)

if __name__ == '__main__':
    main() # type: ignore
