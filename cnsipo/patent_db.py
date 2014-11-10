# -*- coding: utf-8 -*-

"""
Convert patent data to database
"""

__author__ = "Hui Zheng"
__copyright__ = "Copyright 2014 Hui Zheng"
__credits__ = ["Hui Zheng"]
__license__ = "MIT <http://www.opensource.org/licenses/mit-license.php>"
__version__ = "0.1"
__email__ = "xyzdll[AT]gmail[DOT]com"

import json
import os
import sys
import datetime
from optparse import OptionParser

import psycopg2

from shared import get_logger, DETAIL_KINDS

logger = get_logger()

APP_NO = 'app_no'

FIELDS_MAP = [{
    u'申请号': (APP_NO, str),
    u'发明名称': ('name', str),
    u'发明人': ('inventor', str),
    u'申请人': ('applicant', str),
    u'申请日': ('app_date', datetime.date),
    u'申请公布号': ('app_pub_no', str),
    u'申请公布日': ('app_pub_date', datetime.date),
    u'Int. Cl.': ('int_cl', str),
    u'地址': ('address', str),
    u'摘要': ('digest', str),
    u'专利代理机构': ('agency', str),
    u'代理人': ('agent', str),
    # following are ignored
    u'优先权': ('priority', None),
    u'本国优先权': ('native_priority', None),
    u'分案原申请': ('init_app', None),
    u'PCT申请数据': ('pct_app_data', None),
    u'PCT公布数据': ('pct_pub_data', None),
    u'PCT进入国家阶段日': ('pct_stage_date', None),
    u'生物保藏': ('bio_protection', None),
    u'对比文件': ('comp_file', None),
    u'更正文献出版日': ('mod_lit_pub_date', None),
    }, {
    u'事务数据公告日': ('pub_date', datetime.date),
    u'事务数据类型': ('data_type', str),
}]

FIELDS = [(APP_NO, "name", "inventor", "applicant", "app_date", "app_pub_no",
          "app_pub_date", "int_cl", "address", "digest", "agency", "agent"),
          # "priority", "native_priority", "init_app", "pct_app_data",
          # "pct_pub_data", "pct_stage_date", "bio_protection",
          #"comp_file", 'mod_lit_pub_date'
          (APP_NO, "pub_date", "data_type")]


def create_statement(table, detail_kind):
    flds = FIELDS[detail_kind]
    return "INSERT INTO {} ({}) VALUES ({});".format(table,
           ",".join(flds), ",".join(["%(" + i + ")s" for i in flds]))


def insert_data(conn, cursor, stmt, batch_vals, failed_vals):
    try:
        cursor.executemany(stmt, batch_vals)
        conn.commit()
        batch_vals[:] = []
        return
    except psycopg2.IntegrityError as e:  # forgiveable
        logger.warn("duplicate data: {}".format(e))
    except psycopg2.DataError as e:  # need to check data
        logger.error("bad data: {}".format(e))
    except psycopg2.DatabaseError as e:  # unexpected
        logger.error("unexpected database error: {}".format(e))

    #failed
    failed_vals.extend(batch_vals)
    batch_vals[:] = []
    conn.rollback()


def parse_data(detail_map, flds_map, flds, batch_vals):
    vals = dict.fromkeys(flds)
    for k, v in detail_map.items():
        fld_name, fld_type = flds_map[k]
        if not fld_type:  # ignore
            continue
        if fld_type is datetime.date:
            v = datetime.datetime.strptime(v, '%Y.%m.%d')
        vals[fld_name] = v
    batch_vals.append(vals)
    return vals


def import_data(conn, stmt, detail_kind, year, input_dir, include_file,
                exclude_file, error_file, start=0, end=-1,
                batch_size=1000, dry_run=False):
    dirname = os.path.join(input_dir, year)
    i = 0
    batch_vals = []
    failed_vals = []
    flds = FIELDS[detail_kind]
    flds_map = FIELDS_MAP[detail_kind]
    with conn.cursor() as cursor:
        if include_file:
            with open(include_file) as f:
                detail_files = f.read().splitlines()
        else:
            detail_files = os.listdir(dirname)
        if exclude_file:
            with open(exclude_file) as f:
                excluded = f.read().splitlines()
                detail_files = [d for d in detail_files if d not in excluded]
        for detail_file in detail_files:
            i += 1
            if i <= start:
                continue
            if end >= 0 and i > end:
                break

            with open(os.path.join(dirname, detail_file), 'r') as f:
                vals = None
                try:
                    json_obj = json.load(f)
                    if isinstance(json_obj, list):  # transaction case
                        for details in json_obj:
                            vals = parse_data(
                                details, flds_map, flds, batch_vals)
                            vals[APP_NO] = detail_file
                    else:  # detail case
                        vals = parse_data(json_obj, flds_map, flds, batch_vals)
                        assert vals[APP_NO] == detail_file
                #except (KeyError, AssertionError) as e:
                except Exception as e:
                    if vals is None:
                        vals = {}
                    vals[APP_NO] = detail_file  # in case of early exception
                    failed_vals.append(vals)  # OK even in transaction case
                    logger.error("{}({})".format(detail_file, e))
                    continue

                if dry_run:  # only show 1 insertion in each transaction
                    print "execute: {}\n{}".format(stmt, vals)
                elif len(batch_vals) >= batch_size:
                    insert_data(conn, cursor, stmt, batch_vals, failed_vals)
        # leftover
        if batch_vals:
            insert_data(conn, cursor, stmt, batch_vals, failed_vals)
    if failed_vals:
        with open(error_file, 'w') as f:
            for val in failed_vals:
                f.write("{}\n".format(val[APP_NO]))


def main(argv=None):
    usage = "usage: %prog [options] yearOrId1 [yearOrId2 ...]"
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
    parser.add_option("-K", "--detail-kind", dest="detail_kind", type="int",
                      default="1",
                      help="1: {} 2: {}".format(*DETAIL_KINDS))
    parser.add_option("-t", "--patent_table",
                      dest="patent_table_prefix", default="patent_",
                      help="patent table's prefix")
    parser.add_option("-i", "--input-dir", dest="input_dir", default="input",
                      help="input directory(contains patent details)")
    parser.add_option("-I", "--include-file", dest="include_file",
                      help="a file containing included filenames")
    parser.add_option("-x", "--exclude-file", dest="exclude_file",
                      help="a file containing excluded filenames")
    parser.add_option("-E", "--error-file", dest="error_file", default="error",
                      help="error file's prefix(to be appended by year)")
    parser.add_option("-b", "--batch-size", dest="batch_size", default="1000",
                      help="size of batch insertion")
    parser.add_option("-s", "--start", dest="start", default="0",
                      help="start index")
    parser.add_option("-e", "--end", dest="end", default="-1",
                      help="end index")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="show what would have been done")
    (options, args) = parser.parse_args(argv)
    if len(args) == 0:
        parser.error("missing arguments")

    detail_kind = options.detail_kind - 1
    try:
        detail_kind_str = DETAIL_KINDS[detail_kind]
    except:
        parser.error("detail_kind should be an integer between 1 and {}".
                     format(len(DETAIL_KINDS)))

    input_dir = options.input_dir
    include_file = options.include_file
    exclude_file = options.exclude_file
    error_file = options.error_file
    start = int(options.start)
    end = int(options.end)
    batch_size = int(options.batch_size)
    dry_run = options.dry_run

    with psycopg2.connect(
            "dbname='{}' user='{}' host='{}' password='{}'".format(
                options.database, options.user,
                options.host, options.password)) as conn:
        stmt = create_statement(options.patent_table_prefix + detail_kind_str,
                                detail_kind)
        for year in args:
            print "processing on patents' {} in year {}".format(
                  detail_kind_str, year)
            import_data(conn, stmt, detail_kind, year,
                        input_dir=input_dir,
                        include_file=include_file, exclude_file=exclude_file,
                        error_file=error_file+year, start=start, end=end,
                        batch_size=batch_size, dry_run=dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
