import requests
import json

base = 'http://info.sweettracker.co.kr'

def company_api():
    url = '/api/v1/companylist'
    t_key = 'xTAE1mDNbEnHiB4xx7FFQg'
    res = requests.get(base+url, params={'t_key':t_key})
    return res.json()

def recommend_api(t_invoice):
    url = '/api/v1/recommend'
    t_key = 'xTAE1mDNbEnHiB4xx7FFQg'
    res = requests.get(base+url, params={'t_key':t_key, 't_invoice':t_invoice})
    return res.json()

def tracking_api(t_code, t_invoice):
    url = '/api/v1/trackingInfo'
    t_key = 'xTAE1mDNbEnHiB4xx7FFQg'
    res = requests.get(base + url, params={'t_key': t_key, 't_code':t_code,'t_invoice': t_invoice})
    return res.json()


print(json.dumps(tracking_api('01','6124003136324'),indent=4,ensure_ascii = False))

