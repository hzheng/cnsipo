# -*- coding: utf-8 -*-

"""
Test patent list.
"""

import os

from cnsipo.patent_list import KINDS, init_params, query


def test_query(tmpdir):
    kind = KINDS[0]
    year = 1985
    input_dir = str(tmpdir.mkdir("input"))
    input_file = "{}/{}-{}.html".format(input_dir, kind, year)

    assert not os.path.isfile(input_file)
    params, pages = init_params(year, kind, input_dir)
    assert params
    assert pages > 100
    assert os.path.isfile(input_file)

    output_dir = str(tmpdir.mkdir("output"))
    page_now = 2
    output_file = "{}/{}/{}".format(output_dir, year, page_now)

    assert not os.path.isfile(output_file)
    query(params, year, page_now, output_dir)
    assert os.path.isfile(output_file)
