import os
import logging
from datetime import datetime

from opersist.cli import LOG_LEVELS, LOG_DATE_FORMAT, LOG_FORMAT
from mnlite.mnode import DEFAULT_NODE_CONFIG

DEFAULT_JSON = DEFAULT_NODE_CONFIG

__version__ = 'v0.0.1'

FN_DATE = datetime.now().strftime('%Y-%m-%d')
HM_DATE = datetime.now().strftime('%Y-%m-%d-%H%M')
YM_DATE = datetime.now().strftime('%Y-%m')
LOG_DIR = '/var/log/mnlite/'
LOG_NAME = 'mnonboard-%s.log' % (FN_DATE)
LOG_LOC = os.path.join(LOG_DIR, LOG_NAME)

HARVEST_LOG_NAME = '-crawl-%s.log' % YM_DATE

def start_logging(name=__name__):
    """
    Initialize logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    s = logging.StreamHandler()
    s.setLevel(logging.INFO)
    s.setFormatter(formatter)
    # this initializes logging to file
    f = logging.FileHandler(LOG_LOC)
    f.setLevel(logging.DEBUG)
    f.setFormatter(formatter)
    # warnings also go to file
    # initialize logging
    logger.addHandler(s) # stream
    logger.addHandler(f) # file
    return logger

L = start_logging()
L.info('----- mnonboard %s start -----' % __version__)

# absolute path of current file
CUR_PATH_ABS = os.path.dirname(os.path.abspath(__file__))

# relative path from root of mnlite dir to nodes directory
NODE_PATH_REL = 'instance/nodes/'

def default_json(fx='Unspecified'):
    """
    A function that spits out a json file to be used in onboarding.
    """
    L.info('%s function loading default json template.' % (fx))
    return DEFAULT_JSON
