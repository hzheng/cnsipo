# -*- coding: utf-8 -*-

"""
Shared by all main scripts
"""

import os
import sys
import inspect
import logging
import logging.config
import re
import socket
import ConfigParser

import requests


LOGGER_NAME = "patent"


def fallback_logger(stream=sys.stdout):
    logger = logging.getLogger('_FALLBACK_')
    logger.addHandler(logging.StreamHandler(stream))
    return logger


def get_logger():
    frame = inspect.stack()[1]
    caller_file = inspect.getmodule(frame[0]).__file__
    main_name = re.search("(\w+)\.py", caller_file).group(1)
    log_conf_file = os.path.join(main_name + "-logging.conf")
    if not os.path.exists(log_conf_file):
        sys.stderr.write("WARNING: log configuration file {} does NOT exist,"
                         " use stdout instead.\n"
                         .format(log_conf_file))
        return fallback_logger()
        # sys.exit(1)

    try:
        logging.config.fileConfig(log_conf_file)
        return logging.getLogger(LOGGER_NAME)
    except ConfigParser.Error as e:
        sys.stderr.write("logger configuration error - {}\n".format(e))
        sys.exit(1)


class ContentError(Exception):
    """Content error"""
    pass


FORGIVEN_ERROR = (requests.exceptions.HTTPError,
                  requests.exceptions.ConnectionError,
                  requests.exceptions.Timeout,
                  socket.timeout,
                  socket.error,
                  ContentError)


DETAIL_KINDS = ['detail', 'transaction']
