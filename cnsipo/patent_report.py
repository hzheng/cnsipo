# -*- coding: utf-8 -*-

"""
UIG(University/Industry/Government) report
"""

from __future__ import print_function

import sys
from itertools import combinations
from optparse import OptionParser

import psycopg2

from cnsipo.shared import get_logger

logger = get_logger()

APP_NO = 'app_no'
APP_YEAR = 'app_year'
STATE = 'state'
ADDRESS = 'address'
APPLICANT = 'applicant'
KIND = 'kind'
ORG2 = 'org2'


def gen_uig_data(conn, uig_tbl, aux_tbl, year, batch_size):
    stmt = "SELECT u.{}, u.{}, {}, {} FROM {} u, {} a WHERE {}={} AND "\
           "u.{}=a.{} AND u.{}!='F' ORDER BY u.{}".format(
               APP_NO, STATE, ORG2, KIND, uig_tbl, aux_tbl, APP_YEAR, year,
               APP_NO, APP_NO, STATE, APP_NO)
    with conn.cursor() as cursor:
        try:
            logger.debug("executing {}".format(stmt))
            cursor.execute(stmt)
            while True:
                results = cursor.fetchmany(batch_size)
                if results:
                    for result in results:
                        yield result
                else:
                    break
        except psycopg2.DatabaseError as e:
            logger.error("unexpected database error: {}".format(e))


def gen_nodes(conn, uig_tbl, aux_tbl, year, batch_size):
    last_app_no = None
    group = []
    for app_no, state, org2, kind in gen_uig_data(conn, uig_tbl, aux_tbl,
                                                  year, batch_size):
        member = (org2, state, kind)
        if last_app_no == app_no:  # same group
            group.append(member)
        else:  # new group
            if len(group) > 1:
                # report...
                for n1, n2 in combinations(group, 2):
                    yield (last_app_no, n1, n2)
            group = [member]
            last_app_no = app_no


def report_nodes(conn, uig_tbl, aux_tbl, year, batch_size, output_dir):
    with open("{}/node{}".format(output_dir, year), "w") as f:
        for app_no, n1, n2 in gen_nodes(conn, uig_tbl, aux_tbl,
                                        year, batch_size):
            print(app_no, n1[0], n2[0], n1[1], n2[1], n1[2], n2[2], file=f)


def main(argv=None):
    usage = "usage: %prog [options] year1 [year2 ...]"
    parser = OptionParser(usage)
    import getpass
    username = getpass.getuser()

    parser.add_option("-d", "--database", dest="database", default="cnsipo",
                      help="database name")
    parser.add_option("-u", "--user", dest="user", default=username,
                      help="database username")
    parser.add_option("-p", "--password", dest="password",
                      help="database password")
    parser.add_option("-H", "--host", dest="host", default="localhost",
                      help="database host")
    parser.add_option("-i", "--patent-uig-table", dest="patent_uig_tbl",
                      default="patent_uig",
                      help="patent auxiliary table")
    # parser.add_option("-t", "--patent-table", dest="patent_detail_tbl",
    #                   default="patent_detail",
    #                   help="patent table")
    parser.add_option("-a", "--patent-aux-table", dest="patent_aux_tbl",
                      default="patent_aux",
                      help="patent auxiliary table")
    parser.add_option("-b", "--batch-size", dest="batch_size", default="1000",
                      help="size of batch insertion")
    parser.add_option("-o", "--output-dir",
                      dest="output_dir", default="output",
                      help="output directory")
    (options, args) = parser.parse_args(argv)
    if len(args) < 1:
        parser.error("missing arguments")

    uig_tbl = options.patent_uig_tbl
    # detail_tbl = options.patent_detail_tbl
    aux_tbl = options.patent_aux_tbl
    batch_size = int(options.batch_size)
    output_dir = options.output_dir

    with psycopg2.connect(
            "dbname='{}' user='{}' host='{}' password='{}'".format(
                options.database, options.user,
                options.host, options.password)) as conn:
        for year in args:
            print("processing on patents in year {}".format(year),
                  file=sys.stderr)
            report_nodes(conn, uig_tbl, aux_tbl, year,
                         batch_size=batch_size, output_dir=output_dir)
    return 0


if __name__ == '__main__':
    sys.exit(main())
