import os
import logging

from opersist.cli import LOG_LEVELS, LOG_DATE_FORMAT, LOG_FORMAT

logging.basicConfig(
    level=LOG_LEVELS.get("INFO", logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
)
L = logging.getLogger("main")

# absolute path of current file
CUR_PATH_ABS = os.path.dirname(os.path.abspath(__file__))

# relative path to nodes directory
NODE_PATH_REL = 'instance/nodes/'

def node_path(nodepath=NODE_PATH_REL, curpath=CUR_PATH_ABS):
    """
    Get the absolute path of the nodes directory where new members will go.
    Currently the nodes directory lives at `../instance/nodes/` (relative to
    the mnonboard dir that this file is in).
    """
    return os.path.abspath(os.path.join(CUR_PATH_ABS, '../', NODE_PATH_REL))
