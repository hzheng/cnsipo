cnsipo
======

INTRODUCTION
------------

`cnsipo` fetches data from SIPO of China. 

USAGE
-----

Please take the following steps:

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

4. create a table on a (Postgres) database

        bin/initdb.sh -d{database} -u{db_user} -t{db_table} 

    output:
        a table in database

5. import data into database

        python cnsipo/patent_db.py -d{database} -u{db_user} -p{password} -t{db_table} -i {input_dir} {year}

    output:
        data in database


REFERENCE
---------

[中国专利公布公告](http://epub.sipo.gov.cn/gjcx.jsp)


LICENSE
-------

Copyright 2014-2015 Hui Zheng

Released under the [MIT License](http://www.opensource.org/licenses/mit-license.php).
