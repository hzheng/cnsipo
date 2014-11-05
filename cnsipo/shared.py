# -*- coding: utf-8 -*-

"""
Shared by all main scripts
"""

__author__ = "Hui Zheng"
__copyright__ = "Copyright 2014 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"

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


def get_logger():
    frame = inspect.stack()[1]
    caller_file = inspect.getmodule(frame[0]).__file__
    main_name = re.search("(\w+)\.py", caller_file).group(1)
    log_conf_file = os.path.join(main_name + "-logging.conf")
    if not os.path.exists(log_conf_file):
        sys.stderr.write("log configuration file {} does NOT exist\n"
                .format(log_conf_file))
        sys.exit(1)

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
