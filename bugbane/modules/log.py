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
LOGFILE_PATH = os.getenv("BB_LOGFILE")
TRACE_LOGFILE_PATH = os.getenv("BB_TRACEFILE")


def set_as_logger_class(new_logger_class):
    """
    Decorator to set wrapped class as base logger class in logging library.
    The wrapped class should be inherited from Logger.
    """

    logging.setLoggerClass(new_logger_class)
    return new_logger_class


@set_as_logger_class
class BugBaneLogger(Logger):
    """
    Custom logger class:
        1. Has more log levels and log methods:
            verbose1, verbose2 and verbose3: between INFO and DEBUG
            trace: below DEBUG for tracing (messages include line number and function name)
        2. Log level prefix is not printed for the following levels:
            info, verbose1, verbose2, verbose3.
        3. Environment variables BB_LOGFILE and BB_TRACEFILE can be used to specify
            files to also log to.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLevel(logging.NOTSET)

        self.console_handler = None
        self.logfile_handler = None
        self.tracefile_handler = None

        self.console_formatter = ConditionalFormatter("%(message)s")
        self.logfile_formatter = ConditionalFormatter(
            "%(asctime)s | %(name)30s | %(message)s"
        )

        self.create_handlers()

        self.set_verbosity_level(verbosity_level=0)

    def set_verbosity_level(self, verbosity_level: int):
        log_level = self._verb_level_to_log_level(verbosity_level)

        if self.console_handler is None:
            self.create_handlers()

        handlers = [self.console_handler, self.logfile_handler, self.tracefile_handler]

        for handler in handlers:
            if handler is not None:
                handler.setLevel(log_level)

    def create_handlers(self):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.console_formatter)
        self.addHandler(console_handler)
        self.console_handler = console_handler

        # logfile_handler is same as console_handler, but with date & name
        if self.logfile_handler is None and LOGFILE_PATH:
            logfile_handler = logging.handlers.RotatingFileHandler(
                filename=LOGFILE_PATH,
                maxBytes=512000,
                backupCount=0,  # 512 Kb logfile size
            )
            logfile_handler.setLevel(logging.INFO)
            logfile_handler.setFormatter(self.logfile_formatter)
            self.addHandler(logfile_handler)
            self.logfile_handler = logfile_handler

        # tracefile_handler is same as console, but with date & name and uses TRACE level
        if self.tracefile_handler is None and TRACE_LOGFILE_PATH:
            tracefile_handler = logging.handlers.RotatingFileHandler(
                filename=TRACE_LOGFILE_PATH,
                maxBytes=512000,
                backupCount=0,  # 512 Kb logfile size
            )
            tracefile_handler.setLevel(TRACE)
            tracefile_handler.setFormatter(self.logfile_formatter)
            self.addHandler(tracefile_handler)
            self.tracefile_handler = tracefile_handler

    def _verb_level_to_log_level(self, verbosity_level: int):
        """
        Convert program verbosity level from ArgumentParser.parse_args()
        to logging library log level.
        """

        if (verbosity_level or 0) < 1:
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

    def verbose1(self, message, *args, **kwargs):
        if self.isEnabledFor(VERBOSE1):
            self._log(VERBOSE1, message, *args, **kwargs)

    def verbose2(self, message, *args, **kwargs):
        if self.isEnabledFor(VERBOSE2):
            self._log(VERBOSE2, message, *args, **kwargs)

    def verbose3(self, message, *args, **kwargs):
        if self.isEnabledFor(VERBOSE3):
            self._log(VERBOSE3, message, *args, **kwargs)

    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, message, *args, **kwargs)


def get_verbose_logger(logger_name: str, verbosity_level: int) -> BugBaneLogger:
    """
    Returns BugBaneLogger with loglevel set up to match `verbosity_level`,
    passed from e.g. argparse.ArgumentParser.
    """
    logger: BugBaneLogger = getLogger(logger_name)
    logger.set_verbosity_level(verbosity_level)
    logger.debug("Logging initialized")
    return logger


def getLogger(logger_name: str) -> BugBaneLogger:
    """Replacement for logging.getLogger(). Returns BugBaneLogger."""
    logger: BugBaneLogger = logging.getLogger(logger_name)  # type: ignore
    assert isinstance(logger, BugBaneLogger)
    return logger


class ConditionalFormatter(logging.Formatter):
    """
    Custom logging formatter with format settings for different log levels.
    For example it doesn't use 'INFO:' prefix.
    """

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
