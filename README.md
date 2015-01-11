cnsipo
======

INTRODUCTION
------------

`cnsipo` fetches data from SIPO of China.

USAGE
-----

Please take the following steps(step 1-5 are essential, others are optional):

1. get all patent ids for each year(1985-2014) of each kind
   (kind: 1-发明公布 2-发明授权 3-实用新型 4-外观设计)

        python cnsipo/patent_list.py -k{kind} {year} -i {input_dir} -o {output_dir}

    output:

        {input_dir}/{kind}-{year}.html (cached for later use)
        {output_dir}/{year}/{page_index}

2. merge id files(result of step 1) for each year

        bin/merge.sh output_dir path_to_year_dir/{year}

    output:

        {output_dir}/{year}

3. fetch patents' details from the id files(result of step 2) of each kind
   (detail\_kind: 1-详细信息 2-事务数据)

        python cnsipo/patent_detail.py -k{kind} -K{detail_kind} {year} -i {input_dir} -o {output_dir}

    output:

        {output_dir}/{year}

4. create a table on a (Postgres) database(d: detail, t: transaction)

        bin/initdb.sh -d{database} -u{db_user} -t{db_table} d|t

    output:

        a table in database

5. import data into database

        python cnsipo/patent_db.py -d{database} -u{db_user} -p{password} -t{db_table} -i {input_dir} -K{detail_kind} {year}

    output:

        data in database

6. create an auxiliary table on a (Postgres) database

        bin/initdb.sh -d{database} -u{db_user} -t{db_table} a

    output:

        a table in database

7. collect auxiliary data into database

        python cnsipo/patent_aux_db.py -d{database} -u{db_user} -p{password} -t{patent_table} -a{aux_table} {year}

    output:

        data in database

8. create a UIG(university/industry/government) table on a (Postgres) database

        bin/initdb.sh -d{database} -u{db_user} -t{db_table} u

    output:

        a table in database

9. collect UIG data into database

        python cnsipo/patent_uig_db.py -d{database} -u{db_user} -p{password} -i{uig_table} -t{patent_table} -a{aux_table} {year}

    output:

        data in database

10. print UIG nodes for each year

        python cnsipo/patent_report.py -d{database} -u{db_user} -p{password} -i{uig_table} -a{aux_table} {year} -o {output_dir}

    output:

        {output_dir}/node{year}


REFERENCE
---------

1. [中国专利公布公告](http://epub.sipo.gov.cn/gjcx.jsp)

2. [INTERNATIONAL PATENT CLASSIFICATION](http://www.wipo.int/export/sites/www/classifications/ipc/en/guide/guide_ipc.pdf)

3. [High-tech patents](http://epp.eurostat.ec.europa.eu/cache/ITY_SDDS/Annexes/htec_esms_an6.pdf)

4. C:\Program Files\Tencent\QQ\I18N\2052\LocList.xml


LICENSE
-------

Copyright 2014-2015 Hui Zheng

Released under the [MIT License](http://www.opensource.org/licenses/mit-license.php).
