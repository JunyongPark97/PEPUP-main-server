from django.test import TestCase
import requests
# Create your tests here.


class JusoMaster:
    url = "http://www.juso.go.kr/addrlink/addrLinkApi.do"
    confmKey = 'U01TX0FVVEgyMDIwMDEzMDIxMDA1MDEwOTQyNzQ='

    def search_juso(self, keyword='', currentpage=1, countperpage=10):
        res = requests.post(self.url, data={
            'confmKey': self.confmKey,
            'keyword': keyword,
            'currentPage': currentpage,
            'countPerPage': countperpage,
            'resultType': 'json'
        })
        return res.json()


if '__main__' == __name__:
    keyword = '일성트루엘'
    j = JusoMaster()
    while keyword:
        keyword = input('keyword: ')
        print(j.search_juso(keyword))
