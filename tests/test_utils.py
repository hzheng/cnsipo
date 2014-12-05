# -*- coding: utf-8 -*-

"""
Test utils.
"""

from cnsipo.utils import trans_str


def test_trans_str():
    assert trans_str("this is a test", "abcde", "ABCDE") == "this is A tEst"

    assert trans_str("中海油（天津）管道工程技术有限公司", "（）", "()") \
        == "中海油(天津)管道工程技术有限公司"

    assert trans_str("他说：“‘好’极了！”", "“”‘’：！", "\"\"'':!") \
        == "他说:\"'好'极了!\""
