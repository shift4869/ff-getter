# coding: utf-8
import argparse
import logging.config
from logging import INFO, getLogger

from ffgetter.Core import Core

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    if __name__ not in name:
        getLogger(name).disabled = True
    
logger = getLogger(__name__)
logger.setLevel(INFO)

if __name__ == "__main__":
    parser = None
    try:
        parser = argparse.ArgumentParser(
            description="Following/Follower get.",
            epilog="require config file for ./config/config.ini"
        )
        parser.add_argument("--after-open",
                            action="store_true",
                            help="result file open after process run.")
        parser.add_argument("--notification",
                            action="store_false",
                            help="notification reply post after process run.")
        args = parser.parse_args()
    except Exception as e:
        parser.print_help()
        logger.error(e)
        exit(-1)

    try:
        core = Core()
        core.run()
    except Exception as e:
        logger.error(e)
