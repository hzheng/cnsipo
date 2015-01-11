# -*- coding: utf-8 -*-

"""
Patent data parser
"""

import re
import json
import xml.etree.ElementTree as ET

from cnsipo.utils import trans_str

from cnsipo.shared import get_logger


logger = get_logger()


class PatentParser(object):
    """A patent data parser.
    """

    CN = "中国"
    MAINLAND = "大陆"
    FOREIGN = "F"
    UNIVERSITY = "U"
    INDUSTRY = "I"
    GOVERNMENT = "G"
    ZIP_PATTERN = re.compile("^(\d\d)\d{4}")
    PAREN_PATTERN = re.compile("\((.+)\)")
    CN_ADDR_PATTERN = re.compile("中(国|南)|华(东|南|西|北|中)")

    def __init__(self, local_list_xml, cn_univs_json, hi_tech_ipcs=None):

        tree = ET.parse(local_list_xml)
        root = tree.getroot()

        self.cn_state_city_map = {}
        cn_nodes = root[0]
        # Chinese states except HK, Macao, TW
        mainland_nodes = cn_nodes[:-3]
        self.mainland_zip_map = {}
        for child in mainland_nodes:
            state = child.attrib['Name'].encode('utf8')
            cities = [c.attrib['Name'].encode('utf8') for c in child]
            self.cn_state_city_map[state] = cities
            for prefix in child.attrib['ZipPrefix'].split(","):
                self.mainland_zip_map[prefix] = state

        cn_states = self.cn_state_city_map.keys()
        self.cn_states_re = re.compile("^(" + "|".join(cn_states) + ")")

        hmt_nodes = cn_nodes[-3:]
        foreign_countries = [
            c.attrib['Name'].encode('utf8') for c in hmt_nodes]
        foreign_countries.extend([
            c.attrib['Name'].encode('utf8') for c in root[1:]])
        self.foreign_re = re.compile("^(" + "|".join(foreign_countries) + ")")

        self.foreign_state_city_map = {}
        for child in hmt_nodes:
            country = child.attrib['Name'].encode('utf8')
            cities = [c.attrib['Name'].encode('utf8') for c in child]
            self.foreign_state_city_map[country] = cities

        for node in root[1:]:
            country = node.attrib['Name'].encode('utf8')
            state_cities = []
            for state_node in node:
                try:
                    state = state_node.attrib['Name'].encode('utf8')
                except KeyError:
                    state = None
                if state:
                    state_cities.append(state)
                # add cities, too
                state_cities.extend([c.attrib['Name'].encode('utf8')
                                    for c in state_node])
            if state_cities:
                self.foreign_state_city_map[country] = state_cities

        self.ex_re1 = re.compile("小学|中学|监狱|银行")
        self.government_re0 = re.compile(
            "(.*科学院)")
        self.industry_re0 = re.compile(
            "(.*?公司)")
        self.university_re1 = re.compile("(大学|学院|学校)$")
        self.industry_re1 = re.compile(
            "(公司|实业|企业|工业|厂|集团|车间|矿)$")
        self.government_re1 = re.compile(
            "(医院|保健院)$")

        self.ex_re2 = re.compile(
            "解放军|部队|军区|军分区|公安局|警察")
        self.university_re2 = re.compile("大学|学院|学校")
        self.industry_re2 = re.compile(
            "有限|公司|实业|企业|厂|集团|车间")
        self.foreign_industry_re = re.compile(
            "株式|\(株\)|（株）|会社|公社|托拉斯")
        self.government_re2 = re.compile(
            "(科学|技术|研究|开发|研发|设计|科研|科技).*(所|院|中心|基地)|(科|工程)院"
            "|科学(研究|技术)|科委|(计算|实验|测试)中心|研究会|实验室|医院"
            "|政府|机构|部$|厅$|局$|处$|院$|所$|站$|部.*中心$|协会$|委员会$")
        self.foreign_government_re = re.compile(
            "研究组(织|合)")

        self.ex_re3 = re.compile(
            "·|\..+|队$|(农|林|牧|渔|殖|猪|牛|羊|鸡|禽|木|茶|盐|种|加工)场|商店|学会"
            "|办公室|联合会|工会|出版社|保健院|红十字|基金(会)?$|台$|馆$")

        with open(cn_univs_json) as f:
            univs = json.load(f)
            self.cn_univs = {
                s.encode('utf8'): [u.encode('utf8') for u in univs]
                for s, univs in univs.iteritems()}

        if hi_tech_ipcs:
            with open(hi_tech_ipcs) as f:
                self.ipc_re = re.compile(
                    "|".join([c.strip() for c in f.readlines()]))

    def parse_univ(self, address):
        for state, univs in self.cn_univs.iteritems():
            for univ in univs:
                if univ in address:
                    return self.MAINLAND, state
        return None, None

    def main_org(self, applicant):
        matched = self.industry_re0.search(applicant)
        if matched:
            return matched.group(0)
        matched = self.government_re0.search(applicant)
        if matched:
            return matched.group(0)

        for _, univs in self.cn_univs.iteritems():
            for univ in univs:
                if univ in applicant:
                    return univ
        return applicant

    def parse_address(self, address):
        """Parse an address and return country and state
        """
        if not address:
            return None, None

        country = None
        address = trans_str(address, "（）“”‘’＋－　 ", "()\"\"''+-  ")
        stripped_addr = address.lstrip("0123456789() '\"`+-")
        if stripped_addr.startswith(self.CN):
            country = self.MAINLAND
            stripped_addr = stripped_addr[len(self.CN):]

        # check states in China...
        matched = self.cn_states_re.match(stripped_addr)
        if matched:
            return self.MAINLAND, matched.group(1)

        # check foreign countries...
        matched = self.foreign_re.match(stripped_addr)
        if matched:
            # don't care foreign country's states
            return matched.group(1), None

        # check cities in China...
        for state, cities in self.cn_state_city_map.iteritems():
            for city in cities:
                if stripped_addr.startswith(city):
                    return self.MAINLAND, state

        # check univerisities in China...
        if self.university_re2.search(stripped_addr):
            univ_result = self.parse_univ(stripped_addr)
            if univ_result[0]:
                return univ_result

        # check foreign states/cities...
        for foreign_country, cities in self.foreign_state_city_map.iteritems():
            for city in cities:
                if stripped_addr.startswith(city):
                    # don't care foreign state/city
                    return foreign_country, None

        # check zip code
        zip_match = self.ZIP_PATTERN.match(address)
        if zip_match:
            try:
                zip_prefix = zip_match.group(1)
                return self.MAINLAND, self.mainland_zip_map[zip_prefix]
            except KeyError:
                pass

        # check string in parenthese
        paren_match = self.PAREN_PATTERN.search(address)
        if paren_match:
            return self.parse_address(paren_match.group(1))

        if country is None and self.CN_ADDR_PATTERN.search(address):
            country = self.MAINLAND

        logger.warn("unrecognized address: {}".format(address))
        return country, None

    def parse_applicant(self, applicant):
        """Parse an applicant and return his types:
           UNIVERSITY, INDUSTRY, GOVERNMENT
        """
        if self.ex_re1.search(applicant):
            return

        applicant = applicant.decode('utf8').strip(u" 　 ")
        # exclude person names
        if len(applicant) < 4:
            return

        applicant = applicant.encode('utf8')
        if self.industry_re0.search(applicant):
            return self.INDUSTRY
        if self.government_re0.search(applicant):
            return self.GOVERNMENT

        if self.university_re1.search(applicant):
            return self.UNIVERSITY
        if self.industry_re1.search(applicant):
            return self.INDUSTRY
        if self.government_re1.search(applicant):
            return self.GOVERNMENT

        if self.university_re2.search(applicant):
            return self.UNIVERSITY
        if self.industry_re2.search(applicant):
            return self.INDUSTRY
        if self.ex_re2.search(applicant):
            return
        if self.government_re2.search(applicant):
            return self.GOVERNMENT

        if self.foreign_industry_re.search(applicant):
            return self.INDUSTRY
        if self.foreign_government_re.search(applicant):
            return self.GOVERNMENT
        if self.ex_re3.search(applicant):
            return

        logger.warn("unrecognized applicant: {}".format(applicant))

    def parse_applicants(self, applicants, address=None, include_org=False):
        """Parse applicant(s) and return types and states pairs.
        """
        main_country, main_state = self.parse_address(address)
        results = []
        for appl in re.split(";|；", applicants):
            kind = self.parse_applicant(appl)
            if kind is None:
                continue
            country, state = self.parse_address(appl)
            if state is None:
                if country is None:
                    if kind == self.UNIVERSITY:
                        country, state = self.parse_univ(appl)
                        if state is None and main_country != self.MAINLAND:
                            # assume no-chinese university is foregin
                            state = self.FOREIGN
                elif country != self.MAINLAND:
                    state = self.FOREIGN
            # last resort: state from address
            if state is None and main_country:
                if main_country == self.MAINLAND:
                    state = main_state
                else:
                    state = self.FOREIGN
            if state:
                if include_org:
                    appl = appl.decode('utf8').strip(u" 　 ").encode('utf8')
                    appl2 = self.main_org(appl)
                    results.append((kind, state, appl, appl2))
                else:
                    results.append((kind, state))

        if include_org:
            return results

        if len(results) > 1:
            # remove redundants
            results = list(set(results))
            if len(results) == 1:
                results *= 2
            else:
                results = sorted(results)

        return results, main_country, main_state

    def parse_int_cl(self, int_cl):
        """Parse int_cl(s) and return their types.
        """
        hi_tech = False
        low_tech = False
        for ipc in re.split(";|；| | ", int_cl):
            if not ipc:
                continue

            if self.ipc_re.match(ipc):
                hi_tech = True
            else:
                low_tech = True
        return hi_tech, low_tech
