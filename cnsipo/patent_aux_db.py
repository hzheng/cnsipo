# -*- coding: utf-8 -*-

"""
Fill data into an auxiliary patent database
"""

from __future__ import print_function

import sys
import re
from optparse import OptionParser

import psycopg2

from cnsipo.shared import get_logger

logger = get_logger()

APP_NO = 'app_no'
APP_YEAR = 'app_year'
COUNTRY = 'country'
STATE = 'state'
CN = "中国"
MAINLAND = "大陆"
CN_STATES = []
CN_STATES_RE = None
CN_STATE_CITY_MAP = None
FOREIGN_COUNTRIES = []
FOREIGN_RE = None


def init(xml_file):
    global CN_STATES, CN_STATE_CITY_MAP, FOREIGN_COUNTRIES, \
        CN_STATES_RE, FOREIGN_RE
    if CN_STATES:
        return

    import xml.etree.ElementTree as ET

    tree = ET.parse(xml_file)
    root = tree.getroot()

    CN_STATE_CITY_MAP = {}
    cn_nodes = root[0]
    for child in cn_nodes[:-3]:  # iterate Chinese states except HK, Macao, TW
        state = child.attrib['Name'].encode('utf8')
        cities = [c.attrib['Name'].encode('utf8') for c in child]
        CN_STATE_CITY_MAP[state] = cities

    CN_STATES = CN_STATE_CITY_MAP.keys()
    CN_STATES_RE = re.compile("^(" + "|".join(CN_STATES) + ")")

    FOREIGN_COUNTRIES.extend([
        c.attrib['Name'].encode('utf8') for c in cn_nodes[-3:]])
    FOREIGN_COUNTRIES.extend([
        c.attrib['Name'].encode('utf8') for c in root[1:]])
    FOREIGN_RE = re.compile("^(" + "|".join(FOREIGN_COUNTRIES) + ")")


def sort_state(address):
    country = None
    stripped_addr = address.lstrip("0123456789() '\"`+－-")
    if stripped_addr.startswith(CN):
        country = MAINLAND
        stripped_addr = stripped_addr[len(CN):]

    matched = CN_STATES_RE.match(stripped_addr)
    if matched:
        return MAINLAND, matched.group(1)

    matched = FOREIGN_RE.match(stripped_addr)
    if matched:
        return matched.group(1), None

    # check cities in China...
    for state, cities in CN_STATE_CITY_MAP.iteritems():
        for city in cities:
            if stripped_addr.startswith(city):
                return MAINLAND, state
    # give up
    return country, None


def sort_states(records, year):
    for record in records:
        result = {APP_YEAR: year}
        result[APP_NO], address = record
        result[COUNTRY], result[STATE] = sort_state(address)
        yield result


def select_patent_statement(table, year):
    return "SELECT app_no, address FROM {} WHERE "\
        "extract(year from app_date) = {};".format(table, year)


def save_state_statement(table):
    flds = [APP_NO, APP_YEAR, COUNTRY, STATE]
    return "INSERT INTO {} ({}) VALUES ({});".format(
        table, ",".join(flds), ",".join(["%(" + i + ")s" for i in flds]))


def gen_patents(conn, table, year, batch_size):
    with conn.cursor() as cursor:
        stmt = select_patent_statement(table, year)
        try:
            logger.debug("executing {}".format(stmt))
            cursor.execute(stmt)
            while True:
                results = cursor.fetchmany(batch_size)
                if results:
                    yield sort_states(results, year)
                else:
                    break
        except psycopg2.DatabaseError as e:
            logger.error("unexpected database error: {}".format(e))


def save_sorted_state(conn, table, aux_tbl, year, batch_size, dry_run=False):
    with conn.cursor() as cursor:
        stmt = save_state_statement(aux_tbl)
        if dry_run:
            print("executing {}".format(stmt))
            return

        logger.debug("executing {}".format(stmt))
        try:
            for results in gen_patents(conn, table, year, batch_size):
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
                      help="states")
    parser.add_option("-A", "--address", dest="address",
                      help="address test")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="show what would have been done")
    (options, args) = parser.parse_args(argv)

    init(options.loc_file)
    if options.address:
        country, state = sort_state(options.address)
        print("country={}, state={}".format(country, state))
        return 0

    if len(args) == 0:
        parser.error("missing arguments")

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
            save_sorted_state(conn, detail_tbl, aux_tbl, year,
                              batch_size=batch_size, dry_run=dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
