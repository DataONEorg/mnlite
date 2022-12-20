import os
import logging
from datetime import datetime

from opersist.cli import LOG_LEVELS, LOG_DATE_FORMAT, LOG_FORMAT

__version__ = 'v0.0.1'

LOG_DIR = '/var/log/mnlite/'
LOG_NAME = 'mnonboard-%s.log' % datetime.now().strftime('%Y-%m-%d')
LOG_LOC = os.path.join(LOG_DIR, LOG_NAME)

def start_logging():
    logging.basicConfig(
        level=LOG_LEVELS.get("INFO", logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
    )
    l = logging.getLogger("main")
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    # this initializes logging to file
    f = logging.FileHandler(LOG_LOC)
    f.setLevel('INFO')
    f.setFormatter(formatter)
    # warnings also go to file
    # initialize logging
    l.addHandler(f)
    return l

L = start_logging()
L.info('----- mnonboard %s start -----' % __version__)

# absolute path of current file
CUR_PATH_ABS = os.path.dirname(os.path.abspath(__file__))

# relative path from root of mnlite dir to nodes directory
NODE_PATH_REL = 'instance/nodes/'

def node_path(nodepath=NODE_PATH_REL, curpath=CUR_PATH_ABS, nodedir=''):
    """
    Get the absolute path of the nodes directory where new members will go.
    Currently the nodes directory lives at `../instance/nodes/` (relative to
    the mnonboard dir that this file is in).
    """
    return os.path.abspath(os.path.join(curpath, '../', nodepath, nodedir))
