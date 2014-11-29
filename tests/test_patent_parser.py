# -*- coding: utf-8 -*-

"""
Test patent parser.
"""

from cnsipo.patent_parser import PatentParser


def test_state():
    parser = PatentParser("LocList.xml")

    addr_states = [
        ("北京市西城区西长安街86号", (parser.MAINLAND, "北京")),
        ("天津市王串场河北省水利所设计院", (parser.MAINLAND, "天津")),
        ("武汉市武昌珞珈山", (parser.MAINLAND, "湖北")),
        ("618000四川省德阳市华山北路东电医院", (parser.MAINLAND, "四川")),
        ("中国香港沙田大围悠安路一号3楼", ("香港", None)),
        ("中国澳门南湾大马路401至415号中国法律大厦15楼B座", ("澳门", None)),
        ("台湾省新竹科学工业园区", ("台湾", None)),
        ("中国台湾新竹科学工业园区", ("台湾", None)),
        ("美国康涅狄格州", ("美国", None)),
        # should be (mainland, beijing)
        ("中国邮电工业总公司科技处(北京市西长安街13号)", (parser.MAINLAND, None)),
        # should be (mainland, beijing)
        ("清华大学东区16栋5单元501", (None, None)),
        # should be (mainland, shanghai)
        ("航天部上海航天局八○六研究所(上海市华山路1539号)", (None, None)),
        # should be (mainland, hebei)
        ("水利电力部华北电管局保定电力技工学校", (None, None)),
        # should be (Japan, None)
        ("大阪府大阪市东区道修町4丁目3番地", (None, None))
    ]
    for address, state in addr_states:
        assert parser.parse_address(address) == state
