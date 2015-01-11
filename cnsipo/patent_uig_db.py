# -*- coding: utf-8 -*-

"""
Create a UIG(University/Industry/Government) database
"""

from __future__ import print_function

import sys
from optparse import OptionParser

import psycopg2

from cnsipo.shared import get_logger
from cnsipo.patent_parser import PatentParser

logger = get_logger()

APP_NO = 'app_no'
APP_YEAR = 'app_year'
STATE = 'state'
ADDRESS = 'address'
APPLICANT = 'applicant'
COLLAB = 'collab'
KIND = 'kind'
ORG = 'org'
ORG2 = 'org2'
patent_parser = None


def gen_uig_data(conn, table, aux_tbl, year, batch_size):
    stmt = "SELECT {}, {}, {} FROM {} WHERE {} IN "\
           "(SELECT {} FROM {} WHERE {}={} AND "\
           "({} LIKE '%G%I%' OR {} LIKE '%I%U%'))".format(
               APP_NO, ADDRESS, APPLICANT, table, APP_NO, APP_NO,
               aux_tbl, APP_YEAR, year, COLLAB, COLLAB)
    with conn.cursor() as cursor:
        try:
            logger.debug("executing {}".format(stmt))
            cursor.execute(stmt)
            while True:
                results = cursor.fetchmany(batch_size)
                if results:
                    yield parse_uig(results, year)
                else:
                    break
        except psycopg2.DatabaseError as e:
            logger.error("unexpected database error: {}".format(e))


def parse_uig(records, year):
    for record in records:
        result = {}
        result[APP_NO], address, applicants = record
        for kind, state, appl, appl2 in patent_parser.parse_applicants(
            applicants, address, True
        ):
            result[ORG] = appl
            result[ORG2] = appl2
            result[STATE] = state
            result[KIND] = kind
            yield result


def save_uig_info(conn, uig_tbl, table, aux_tbl, year, batch_size,
                  dry_run=False):
    flds = [APP_NO, ORG, ORG2, STATE, KIND]
    stmt = "INSERT INTO {} ({}) VALUES ({});".format(
        uig_tbl, ",".join(flds), ",".join(["%(" + i + ")s" for i in flds]))
    if dry_run:
        print("executing {}".format(stmt))
        return

    with conn.cursor() as cursor:
        logger.debug("executing {}".format(stmt))
        try:
            for results in gen_uig_data(conn, table, aux_tbl,
                                        year, batch_size):
                cursor.executemany(stmt, results)
            conn.commit()
        except psycopg2.DatabaseError as e:
            logger.error("unexpected database error: {}".format(e))
            return


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
    parser.add_option("-t", "--patent-table", dest="patent_detail_tbl",
                      default="patent_detail",
                      help="patent table")
    parser.add_option("-a", "--patent-aux-table", dest="patent_aux_tbl",
                      default="patent_aux",
                      help="patent auxiliary table")
    parser.add_option("-b", "--batch-size", dest="batch_size", default="1000",
                      help="size of batch insertion")
    parser.add_option("-l", "--loc-file", dest="loc_file",
                      default="LocList.xml",
                      help="country/state/city list file")
    parser.add_option("-U", "--univ-file", dest="univ_file",
                      default="cn_univs.json",
                      help="chinese univerisity list file")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="show what would have been done")
    (options, args) = parser.parse_args(argv)
    if len(args) < 1:
        parser.error("missing arguments")

    global patent_parser
    patent_parser = PatentParser(options.loc_file, options.univ_file)

    uig_tbl = options.patent_uig_tbl
    detail_tbl = options.patent_detail_tbl
    aux_tbl = options.patent_aux_tbl
    batch_size = int(options.batch_size)
    dry_run = options.dry_run

    with psycopg2.connect(
            "dbname='{}' user='{}' host='{}' password='{}'".format(
                options.database, options.user,
                options.host, options.password)) as conn:
        for year in args:
            print("processing on patents in year {}".format(year),
                  file=sys.stderr)
            save_uig_info(conn, uig_tbl, detail_tbl, aux_tbl, year,
                          batch_size=batch_size, dry_run=dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
