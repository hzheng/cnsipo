# -*- coding: utf-8 -*-

"""
Retrieve patent ID's
"""


__author__ = "Hui Zheng"
__copyright__ = "Copyright 2014 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"

import requests
import re
import os
import sys
from optparse import OptionParser

from utils import retry, JobQueue, threaded
from shared import get_logger, ContentError, FORGIVEN_ERROR

URL = 'http://epub.sipo.gov.cn/patentoutline.action'
DELAY = 3
RETRIES = 1000
PAGE_SIZE = 20
KINDS = ['fmgb', 'fmsq', 'syxx', 'wgsq']

logger = get_logger()


@retry(FORGIVEN_ERROR, tries=RETRIES, delay=2*DELAY, backoff=2, logger=logger)
def init_params(year, kind, input_dir):
    if not os.path.isdir(input_dir):
        os.makedirs(input_dir)
    logger.info("init with year: {}, kind: {}".format(year, kind))

    params = {
            'showType': 0,
            'selected': kind,
            'pageSize': PAGE_SIZE,
            'numSortMethod': 0,
            'strWord': "申请日=BETWEEN['{0}','{0}']".format(year),
            'pageNow': 1,
            }
    params["num" + kind.upper()] = 0 # important
    try:
        input_file = "{}/{}-{}.html".format(input_dir, kind, year)
        if os.path.exists(input_file):
            logger.debug("retreiving page from cache file: {}".format(
                input_file))
        else:
            logger.debug("retreiving page from web and write to: {}".format(
                input_file))
            resp = requests.post(URL, params=params)
            with open(input_file, 'w') as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
        with open(input_file, 'r') as f:
            page = f.read()
            keys = dict(re.findall("ksjs\.(.*)\.value = \"(.+)\"", page))
            params['strLicenseCode'] = keys['strLicenseCode'] #necessary?
            num_str = "num" + kind.upper()
            count = params[num_str] = keys[num_str]
            count = int(count)
            pages = count / PAGE_SIZE
            if count % PAGE_SIZE:
                pages += 1
            return params, pages
    except KeyError:
        raise ContentError()
    except FORGIVEN_ERROR as e:
        logger.debug("FAIL(may retry) with the year: {}, kind: {}({})".format(
            year, kind, e))
        raise
    except Exception as e:
        logger.error("FAIL(no retry) with the year: {}, kind: {}({})".format(
            year, kind, e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error("{}|{}|{}".format(exc_type, fname, exc_tb.tb_lineno))
        raise


@retry(FORGIVEN_ERROR, tries=RETRIES, delay=DELAY, backoff=1, logger=logger)
def query(params, year, page_now, dirname, timeout, dry_run=False):
    params = dict(params)
    params['pageNow'] = page_now
    dirname = "{}/{}".format(dirname, year)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    output_path = os.path.join(dirname, str(page_now))
    if os.path.exists(output_path):
        logger.debug("SKIP with year: {}, page_now: {}".format(year, page_now))
        return

    logger.debug("doing with year: {}, page_now: {}".format(year, page_now))
    if dry_run:
        return

    try:
        resp = requests.post(URL, params=params, timeout=timeout)
        if resp.status_code != requests.codes.ok:
            raise Exception("bad status code: {}".format(resp.status_code))

        #with open('out1/'+ year + '_' + str(page_now) + '.html', 'w') as f:
            #for chunk in resp.iter_content(CHUNK_SIZE):
                #f.write(chunk)
        with open(output_path, 'w') as f:
            for patent_id in set(
                    re.findall("javascript:zl_xm\('([^']*)'", resp.text)):
                f.write("{}\n".format(patent_id))
        logger.info("DONE with year: {}, page#: {}".format(year, page_now))
    except FORGIVEN_ERROR as e:
        logger.debug("FAIL(may retry) with the year: {}, page#: {}({})".format(
            year, page_now, e))
        raise
    except Exception as e:
        logger.error("FAIL(no retry) with the year: {}, page#: {}({})".format(
            year, page_now, e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error("{}|{}|{}".format(exc_type, fname, exc_tb.tb_lineno))
        raise


def main(argv=None):
    usage = "usage: %prog [options] year"
    parser = OptionParser(usage)

    parser.add_option("-k", "--kind", dest="kind", type="int", default="1",
            help="patent type(1-4)")
    parser.add_option("-i", "--input-dir", dest="input_dir", default="input",
            help="input directory(save downloaded pages)")
    parser.add_option("-o", "--output-dir",
            dest="output_dir", default="output",
            help="output directory")
    parser.add_option("-t", "--threads", dest="threads", default="20",
            help="number of threads")
    parser.add_option("-T", "--timeout", dest="timeout", default="5",
            help="connection timeout")
    parser.add_option("-s", "--start", dest="start", default="1",
            help="start page")
    parser.add_option("-e", "--end", dest="end", default="-1",
            help="end page")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
            help="show what would have been done")
    (options, args) = parser.parse_args(argv)
    if len(args) == 0:
        parser.error("missing arguments")

    year = args[0]
    input_dir = options.input_dir
    output_dir = options.output_dir
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    try:
        kind = KINDS[options.kind - 1]
    except:
        parser.error("kind should be an integer between 1 and {}". format(
            len(KINDS)))

    dry_run = options.dry_run
    timeout = int(options.timeout)
    params, pages = init_params(year, kind, input_dir)
    start = int(options.start)
    end = int(options.end)
    if end < 0:
        end = pages
    job_queue = JobQueue(1 if dry_run else int(options.threads))
    with threaded(job_queue):
        for i in range(start, end + 1):
            job_queue.add_task(query, params, year, i,
                    dirname=output_dir, timeout=timeout, dry_run=dry_run)
    return 0

if __name__ == '__main__':
    sys.exit(main())
