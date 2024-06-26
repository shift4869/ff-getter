import argparse
import logging.config
from logging import INFO, getLogger
from pathlib import Path

from ff_getter.core import Core
from ff_getter.log_message import Message as Msg

logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
for name in logging.root.manager.loggerDict:
    if "ff_getter" not in name:
        getLogger(name).disabled = True

logger = getLogger(__name__)
logger.setLevel(INFO)

prevent_multiple_run_path = Path(__file__).parent / "./prevent_multiple_run"


def main() -> None:
    logger.info(Msg.HORIZONTAL_LINE())
    logger.info(Msg.APPLICATION_START())
    parser = None
    try:
        parser = argparse.ArgumentParser(
            description="Following/Follower get.", epilog="require config file for ./config/ff_getter_config.json"
        )
        parser.add_argument(
            "--disable-notification",
            action="store_true",
            help="Notification after process run. Set this option, then don't notify after process run.",
        )
        parser.add_argument(
            "--disable-after-open",
            action="store_true",
            help="Result file open after process run. Set this option, then don't open file after process run.",
        )
        parser.add_argument(
            "--reserved-file-num",
            type=int,
            help="Number of result file reserved. Greater than, then move to backup directory after process run.",
        )
    except Exception as e:
        parser.print_help()
        logger.error(e)
        exit(-1)

    try:
        if not prevent_multiple_run_path.exists():
            prevent_multiple_run_path.touch()
            core = Core(parser)
            core.run()
        else:
            logger.warning(Msg.APPLICATION_MULTIPLE_RUN())
    except Exception as e:
        logger.error(e)
    finally:
        prevent_multiple_run_path.unlink(missing_ok=True)
    logger.info(Msg.APPLICATION_DONE())
    logger.info(Msg.HORIZONTAL_LINE())


if __name__ == "__main__":
    main()
