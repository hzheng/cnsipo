# -*- coding: utf-8 -*-

"""
Patent data parser
"""

import re
import xml.etree.ElementTree as ET


class PatentParser(object):
    """A patent data parser.
    """

    CN = "中国"
    MAINLAND = "大陆"

    def __init__(self, local_list_xml):

        tree = ET.parse(local_list_xml)
        root = tree.getroot()

        self.cn_state_city_map = {}
        cn_nodes = root[0]
        # iterate Chinese states except HK, Macao, TW
        for child in cn_nodes[:-3]:
            state = child.attrib['Name'].encode('utf8')
            cities = [c.attrib['Name'].encode('utf8') for c in child]
            self.cn_state_city_map[state] = cities

        cn_states = self.cn_state_city_map.keys()
        self.cn_states_re = re.compile("^(" + "|".join(cn_states) + ")")

        foreign_countries = [
            c.attrib['Name'].encode('utf8') for c in cn_nodes[-3:]]
        foreign_countries.extend([
            c.attrib['Name'].encode('utf8') for c in root[1:]])
        self.foreign_re = re.compile("^(" + "|".join(foreign_countries) + ")")

    def parse_address(self, address):
        """Parse an address and return country and state
        """

        # TODO: check zip code for state?
        country = None
        stripped_addr = address.lstrip("0123456789() '\"`+－-")
        if stripped_addr.startswith(self.CN):
            country = self.MAINLAND
            stripped_addr = stripped_addr[len(self.CN):]

        matched = self.cn_states_re.match(stripped_addr)
        if matched:
            return self.MAINLAND, matched.group(1)

        matched = self.foreign_re.match(stripped_addr)
        if matched:
            return matched.group(1), None

        # check cities in China...
        for state, cities in self.cn_state_city_map.iteritems():
            for city in cities:
                if stripped_addr.startswith(city):
                    return self.MAINLAND, state
        # give up
        return country, None
