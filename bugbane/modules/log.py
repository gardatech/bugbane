# Copyright 2022 Garda Technologies, LLC. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Originally written by Valery Korolyov <fuzzah@tuta.io>

import os
import sys
import logging
import logging.handlers
from logging import LogRecord, Logger

# custom log levels between INFO and DEBUG
VERBOSE1 = 19
VERBOSE2 = 18
VERBOSE3 = 17

# custom log level below DEBUG for tracing
TRACE = 9

# env variables specfy paths to log files
LOGFILE_PATH = os.getenv("LOGFILE")
TRACE_LOGFILE_PATH = os.getenv("TRACE_LOGFILE")


def get_first_logger(loggername, verbosity_level) -> Logger:
    """
    This method setups logging options like custom log levels
    and returns new instance of Logger.
    Call this from script entrypoint.
    Other modules should create logger as usual:
    ```
    import logging
    log = logging.getLogger(__name__)
    ```
    """

    log_level = _verb_level_to_log_level(verbosity_level)
    _setup_logging(log_level)
    logger = logging.getLogger(loggername)
    logger.debug("Logging initialized")
    return logger


def _verb_level_to_log_level(verbosity_level: int):
    """
    Convert program verbosity level from ArgumentParser.parse_args()
    to logging library log level
    """

    if not verbosity_level or verbosity_level < 1:
        return logging.INFO

    if verbosity_level > 4:
        return TRACE

    mapping = {
        4: logging.DEBUG,
        3: VERBOSE3,
        2: VERBOSE2,
        1: VERBOSE1,
    }
    return mapping[verbosity_level]


def _setup_logging(log_level: int):
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)

    _add_log_level_method(VERBOSE1, "VERBOSE1")
    _add_log_level_method(VERBOSE2, "VERBOSE2")
    _add_log_level_method(VERBOSE3, "VERBOSE3")
    _add_log_level_method(TRACE, "TRACE")

    console_formatter = ConditionalFormatter("%(message)s")
    logfile_formatter = ConditionalFormatter("%(asctime)s | %(name)30s | %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if LOGFILE_PATH:  # same as console, but with date & name
        # 512 Kb
        logfile_handler = logging.handlers.RotatingFileHandler(
            filename=LOGFILE_PATH, maxBytes=512000, backupCount=0
        )
        logfile_handler.setLevel(log_level)
        logfile_handler.setFormatter(logfile_formatter)
        logger.addHandler(logfile_handler)

    if TRACE_LOGFILE_PATH:  # same as console, but with date & name and uses TRACE level
        # 512 Kb
        dbg_logfile_handler = logging.handlers.RotatingFileHandler(
            filename=TRACE_LOGFILE_PATH, maxBytes=512000, backupCount=0
        )
        dbg_logfile_handler.setLevel(TRACE)
        dbg_logfile_handler.setFormatter(logfile_formatter)
        logger.addHandler(dbg_logfile_handler)

    # logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def _add_log_level_method(level: int, levelname: str):
    logging.addLevelName(level, levelname)

    def logmethod(self: Logger, message, *args, **kwargs):
        if self.isEnabledFor(level):
            self._log(level, message, args, **kwargs)

    setattr(logging.Logger, levelname.lower(), logmethod)


class ConditionalFormatter(logging.Formatter):
    def format(self, record: LogRecord):
        fmt = self._style._fmt
        try:
            if record.levelno == TRACE:
                self._style._fmt = fmt.replace(
                    "%(message)s",
                    "%(levelname)s: in %(funcName)s() at %(filename)s:%(lineno)d: %(message)s",
                )
            elif record.levelno >= logging.WARNING or record.levelno <= logging.DEBUG:
                self._style._fmt = fmt.replace(
                    "%(message)s",
                    "%(levelname)s: %(message)s",
                )
            res = super().format(record)
        finally:
            self._style._fmt = fmt

        return res
