# -*- coding: utf-8 -*-

"""
Retrieve patent details
"""

__author__ = "Hui Zheng"
__copyright__ = "Copyright 2014 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"

import requests
import json
import os
import sys
from optparse import OptionParser
from bs4 import BeautifulSoup
from utils import retry, JobQueue, threaded
from shared import get_logger, ContentError, FORGIVEN_ERROR

URL = 'http://epub.sipo.gov.cn/patentdetail.action'
DELAY = 3
RETRIES = 10000

logger = get_logger()


def get_params(patent_id):
    params = {
            'strSources': "fmmost",
            'strWhere': "申请号='{}' and GBINDEX=1".format(patent_id),
            'strLicenseCode': "",
            'pageNow': 1,
            }
    return params


@retry(FORGIVEN_ERROR, tries=RETRIES, delay=DELAY, backoff=1, logger=logger)
def query(patent_id, dirname, timeout, dry_run=False):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    output_path = os.path.join(dirname, patent_id)
    if os.path.exists(output_path):
        logger.debug("SKIP the patent {}".format(patent_id))
        return

    logger.debug("doing with patent: {}".format(patent_id))
    if dry_run:
        return

    try:
        params = get_params(patent_id)
        resp = requests.post(URL, params=params, timeout=timeout)
        bs = BeautifulSoup(resp.text)
        tbl = bs.table.table
        details = {}
        for row in tbl.findAll('tr'):
            cells = row.findAll('td')
            details[cells[0].get_text().encode('utf-8')] = \
                    cells[1].get_text().encode('utf-8')
        digest = bs.find_all("div", class_="xm_jsh")[0]
        details['摘要'] = digest.get_text().encode('utf-8')
        with open(output_path, 'w') as f:
            json.dump(details, f, ensure_ascii=False)
            f.write("\n")
        logger.info("DONE with the patent: {}".format(patent_id))
    except AttributeError:
        raise ContentError()
    except FORGIVEN_ERROR as e:
        logger.debug("FAIL(may retry) with the patent: {}({})".format(
            patent_id, e))
        raise
    except Exception as e:
        logger.error("FAIL(no retry) with the patent: {}({})".format(
            patent_id, e))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error("{}|{}|{}".format(exc_type, fname, exc_tb.tb_lineno))
        raise


def main(argv=None):
    usage = "usage: %prog [options] yearOrId1 [yearOrId2 ...]"
    parser = OptionParser(usage)
    parser.add_option("-i", "--input-dir", dest="input_dir", default="input",
            help="input directory(contains ID files)")
    parser.add_option("-o", "--output-dir",
            dest="output_dir", default="output",
            help="output directory")
    parser.add_option("-t", "--threads", dest="threads", default="20",
            help="number of threads")
    parser.add_option("-T", "--timeout", dest="timeout", default="5",
            help="connection timeout")
    parser.add_option("-s", "--start", dest="start", default="0",
            help="start index")
    parser.add_option("-e", "--end", dest="end", default="-1",
            help="end index")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
            help="show what would have been done")
    (options, args) = parser.parse_args(argv)
    if len(args) == 0:
        parser.error("missing arguments")

    input_dir = options.input_dir
    output_dir = options.output_dir
    timeout = int(options.timeout)
    start = int(options.start)
    end = int(options.end)
    dry_run = options.dry_run

    job_queue = JobQueue(1 if dry_run else int(options.threads))
    with threaded(job_queue):
        if len(args[0]) == 4: # assumed years
            for year in args:
                dirname = os.path.join(output_dir, year)
                with threaded(job_queue):
                    with open(os.path.join(input_dir, year)) as f:
                        i = 1
                        for line in f:
                            i += 1
                            if i > start and (end < 0 or i <= end):
                                job_queue.add_task(query, line.strip(),
                                        dirname, timeout, dry_run=dry_run)
        else: # assumed ids
            for patent_id in args:
                dirname = output_dir
                job_queue.add_task(query, patent_id, dirname, timeout,
                        dry_run=dry_run)
    return 0

if __name__ == '__main__':
    sys.exit(main())
