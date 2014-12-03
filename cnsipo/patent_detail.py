# -*- coding: utf-8 -*-

"""
Retrieve patent details and transactions
"""

import json
import os
import sys
from optparse import OptionParser

import requests
from bs4 import BeautifulSoup

from cnsipo.utils import retry, JobQueue, threaded
from cnsipo.shared import get_logger, ContentError, FORGIVEN_ERROR, \
    DETAIL_KINDS


KINDS = ['fmgb', 'fmsq', 'syxx', 'wgsq']
STR_SRC = ['fmmost', 'fmmost', 'xxmost', 'wgmost']
STR_WHERE = ['GB', 'SQ', 'GB', 'SQ']
DELAY = 3
RETRIES = 1000

logger = get_logger()


def detail_params(patent_id, kind):
    params = {
        'strSources': STR_SRC[kind],
        'strWhere': "申请号='{}' and {}INDEX=1".format(
            patent_id, STR_WHERE[kind]), 'strLicenseCode': "", 'pageNow': 1
    }
    return "http://epub.sipo.gov.cn/patentdetail.action", params


def detail_parse(bs, kind):
    # TODO: not work for kind 'wgsq'
    details = {}
    tbl = bs.table.table
    for row in tbl.findAll('tr'):
        cells = row.findAll('td')
        details[cells[0].get_text().encode('utf-8')] = \
            cells[1].get_text().encode('utf-8')
    digest = bs.find_all("div", class_="xm_jsh")[0]
    details['摘要'] = digest.get_text().encode('utf-8')
    return details


def transaction_params(patent_id, kind):
    params = {'an': "{}".format(patent_id)}
    return "http://epub.sipo.gov.cn/fullTran.action", params


def transaction_parse(bs, kind):
    trans = []
    for tbl in bs.findAll('table'):
        t = tbl.table
        if t:
            key_val = {}
            rows = t.findAll('tr')
            cells = rows[1].findAll('td')
            for i in [0, 2]:
                key_val[cells[i].get_text().encode('utf-8')] \
                    = cells[i + 1].get_text().encode('utf-8')
            trans.append(key_val)
    return trans


@retry(FORGIVEN_ERROR, tries=RETRIES, delay=DELAY, backoff=1, logger=logger)
def query(get_params, parse, kind,
          patent_id, dirname, timeout, check_level, dry_run=False):
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    output_path = os.path.join(dirname, patent_id)
    if check_level and os.path.exists(output_path):
        if check_level > 1 and os.path.getsize(output_path) < 10:
            logger.info("REDO with id: {}(empty result)".format(patent_id))
        else:
            logger.debug("SKIP the patent {}".format(patent_id))
            return

    msg = "doing with patent: {}".format(patent_id)
    if dry_run:
        print msg
        return

    logger.debug(msg)
    try:
        url, params = get_params(patent_id, kind)
        resp = requests.post(url, params=params, timeout=timeout)
        bs = BeautifulSoup(resp.text)
        result = parse(bs, kind)
        if not result:  # empty
            raise ContentError("no valid data found")
        with open(output_path, 'w') as f:
            json.dump(result, f, ensure_ascii=False)
            f.write("\n")
        logger.info("DONE with the patent: {}".format(patent_id))
    except AttributeError as e:
        logger.warn("an error page for the patent: ({})".format(patent_id))
        raise ContentError("attribute error")
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
    parser.add_option("-k", "--kind", dest="kind", type="int", default="1",
                      help="patent type(1-4)")
    parser.add_option("-K", "--detail-kind", dest="detail_kind", type="int",
                      default="1",
                      help="1: {} 2: {}".format(*DETAIL_KINDS))
    parser.add_option("-i", "--input-dir", dest="input_dir", default="input",
                      help="input directory(contains ID files)")
    parser.add_option("-o", "--output-dir",
                      dest="output_dir", default="output",
                      help="output directory")
    parser.add_option("-t", "--threads", dest="threads", type="int",
                      default="20",
                      help="number of threads")
    parser.add_option("-T", "--timeout", dest="timeout", type="int",
                      default="5",
                      help="connection timeout")
    parser.add_option("-s", "--start", dest="start", type="int", default="0",
                      help="start index")
    parser.add_option("-e", "--end", dest="end", type="int", default="-1",
                      help="end index")
    parser.add_option("-c", "--check-level", dest="check_level", type="int",
                      default="1",
                      help="0: no check, 1: check file existence, "
                      "2: check file size")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="show what would have been done")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("missing arguments")

    get_params, parse = None, None
    kind = options.kind - 1
    kind_str = KINDS[kind]
    try:
        detail_kind = DETAIL_KINDS[options.detail_kind - 1]
        get_params = globals()[detail_kind + "_params"]
        parse = globals()[detail_kind + "_parse"]
    except:
        parser.error("detail_kind should be an integer between 1 and {}".
                     format(len(DETAIL_KINDS)))

    input_dir = options.input_dir
    output_dir = options.output_dir
    timeout = options.timeout
    start = options.start
    end = options.end
    check_level = options.check_level
    dry_run = options.dry_run

    job_queue = JobQueue(1 if dry_run else options.threads)
    with threaded(job_queue):
        if len(args[0]) == 4:  # assumed years
            for year in args:
                dirname = os.path.join(output_dir, year)
                print "start on patents' {}(kind: {}) in year {}".format(
                    detail_kind, kind_str, year)
                with open(os.path.join(input_dir, year)) as f:
                    i = 1
                    for line in f:
                        i += 1
                        if i > start and (end < 0 or i <= end):
                            job_queue.add_task(query,
                                               get_params, parse, kind,
                                               line.strip(), dirname,
                                               timeout=timeout,
                                               check_level=check_level,
                                               dry_run=dry_run)
        else:  # assumed ids
            for patent_id in args:
                print "start on patent {}'s {}(kind: {})".format(
                    patent_id, detail_kind, kind_str)
                dirname = output_dir
                job_queue.add_task(query, get_params, parse, kind,
                                   patent_id, dirname, timeout=timeout,
                                   check_level=check_level, dry_run=dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
