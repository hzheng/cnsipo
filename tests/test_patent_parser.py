# -*- coding: utf-8 -*-

"""
Test patent parser.
"""

import pytest

from cnsipo.patent_parser import PatentParser


@pytest.fixture(scope="module")
def parser():
    return PatentParser("LocList.xml")


def test_state(parser):
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
        # FIXME
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


def test_applicant(parser):
    applicant_types = [
        ("中国科学院过程工程研究所",
         (True, False, False)),
        ("N·V·菲利浦斯光灯制造厂",
         (False, True, False)),
        ("华中科技大学; 云南电力试验研究院有限公司电力研究院",
         (True, True, False)),
        ("广东电网公司电力调度控制中心; 华南理工大学",
         (True, True, False)),
        ("中山大学附属肿瘤医院; 广州医学院; 北京索奥生物医药科技有限公司",
         (True, True, True)),
        ("海普拉精密工业(株)",
         (False, True, False)),
        ("张华; 王公司",
         (False, False, False)),
        ("信息产业部通信计量中心",
         (False, False, True)),
        ("李小明; 马里兰大学",
         (True, False, False)),
        ("食品产业加工烹饪技术研究组合",
         (False, False, True))
    ]
    for applicant, types in applicant_types:
        assert parser.parse_applicants(applicant) == types
