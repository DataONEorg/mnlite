import os
import logging

from opersist.cli import LOG_LEVELS, LOG_DATE_FORMAT, LOG_FORMAT

logging.basicConfig(
    level=LOG_LEVELS.get("INFO", logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
)
L = logging.getLogger("main")
