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

        self.ex_re1 = re.compile("基金会|小学|中学|监狱|银行")
        self.university_re1 = re.compile("(大学|学院|学校)$")
        self.industry_re1 = re.compile(
            "(公司|实业|企业|厂|集团|车间|矿)$")
        self.government_re1 = re.compile(
            "(医院|保健院)$")

        self.ex_re2 = re.compile(
            "解放军|部队|军区|军分区|公安局|警察")
        self.university_re2 = re.compile("大学|学院|学校")
        self.industry_re2 = re.compile(
            "有限|公司|实业|企业|厂|集团|车间")
        self.foreign_industry_re = re.compile(
            "株式|\(株\)|会社|公社|托拉斯")
        self.government_re2 = re.compile(
            "(科学|技术|研究|开发|设计|科研|科技).*(所|院|中心|基地)|(科|工程)院"
            "|科学(研究|技术)|科委|(计算|实验|测试)中心|研究会|实验室|医院|保健院"
            "|政府|机构|部$|厅$|局$|处$|院$|所$|站$|部.*中心$|协会$|委员会$")
        self.foreign_government_re = re.compile(
            "研究组(织|合)")

        self.ex_re3 = re.compile(
            "·|\..+|队$|(农|林|牧|渔|殖|猪|牛|羊|鸡|禽|木|茶|盐|种)场|商店|学会"
            "|办公室|联合会|工会|红十字会|台$|馆$|")

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

    def parse_applicants(self, applicants):
        """Parse an applicant and return his types:
           university, industry, government
        """
        industry = university = government = False
        for applicant in re.split(",|，|;|；| |　| ", applicants):
            if self.ex_re1.search(applicant):
                continue
            chars = len(applicant.decode('utf8'))
            if chars < 4:
                continue

            if self.university_re1.search(applicant):
                university = True
                continue
            if self.industry_re1.search(applicant):
                industry = True
                continue
            if self.foreign_industry_re.search(applicant):
                industry = True
                continue
            if self.government_re1.search(applicant):
                government = True
                continue
            if self.foreign_government_re.search(applicant):
                government = True
                continue

            if self.university_re2.search(applicant):
                university = True
                continue
            if chars < 5:
                continue
            if self.industry_re2.search(applicant):
                industry = True
                continue
            if self.ex_re2.search(applicant):
                continue
            if self.government_re2.search(applicant):
                government = True
                continue
            if self.ex_re3.search(applicant):
                continue
            print applicant
        return university, industry, government
