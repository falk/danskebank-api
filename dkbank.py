# -*- coding: utf-8 -*-

import requests
import json
import sys
from time import sleep
from base64 import b64decode
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


class DKBank(object):

    mb_url = 'https://mb.danskebank.dk/smartphones/gmb.svc/'

    """
    Private key, derived from the android app icon...
    """
    key = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCzaFT5q4XWSOz4LjTGNmhHa5WvvZY2AYTzCd7WnMY+VXs25l5XR1OtRFxuIU0tsWxpKDTEqpuUveS7TV/8d3CO0Mq5mjNsrJuehH6a0rJ1tvVDCx2nzFLp+c7eLgldR3nV5EOblCEC2EiXU3YsHlLlapJEPm40sd2vuaswxYcZ/wIDAQAB='

    methods = {
        'init':     {'method': 'POST', 'url': 'InitSession'},
        'create':   {'method': 'POST', 'url': 'CreateSession'},
        'login':    {'method': 'POST', 'url': 'Login'},
        'accounts': {'method': 'GET',  'url': 'Accounts'},
        'account':  {'method': 'GET',  'url': '/Service/Accounts/{account_number}/Transactions?pageSize=40&lastId=&currency=DKK'}
    }

    info_schema = {
        u'AccountNumber': ('account_number', str),
        u'Balance': ('balance', float),
    }

    magic_key = ''
    token = ''

    def __init__(self, cpr, pin):
        self.cpr = cpr
        self.pin = pin

    def _request(self, method, payload={}, **params):
        template = self.mb_url + self.methods[method]['url']
        url = template.format(**params)

        response = self._send_request(url, method, payload)
        response.raise_for_status()

        if response.content:
            print response.content
            data = response.json()
            status_code = data['Status']['StatusCode']
            if 'MagicKey' in data:
                self.magic_key = data['MagicKey']
            if status_code == 9:
                print "bad response"
                print response.content
                sys.exit()
            print "new key: " + self.magic_key
            return data
        return None

    def _parse(self, data):
        info = {}
        for key, value in data.items():
            if key in self.info_schema:
                field_name, type_ = self.info_schema[key]
                value = type_(value)
                info[field_name] = value
        return info

    def _send_request(self, url, method, payload):
        headers = {
            'Content-Type': 'text/json',
            'User-Agent': 'Python/1.0.0',
        }
        payload = json.dumps(payload)
        params = {'magicKey': self.magic_key}
        print "sending magic key:" + self.magic_key
        if self.methods[method]['method'] == 'POST':
            response = requests.post(url, data=payload,
                                     headers=headers, params=params)
        else:
            response = requests.get(url, headers=headers, params=params)

        return response

    def init_session(self):
        request = self._request('init')
        self.token = self._crypt_token(request['Token'])

    def _crypt_token(self, token):
        key = RSA.importKey(b64decode(self.key))
        rsakey = PKCS1_v1_5.new(key)
        encrypted = rsakey.encrypt(token.encode('utf-8'))
        return encrypted.encode('base64')

    def create_session(self):
        payload = {"notificationId": self.token,
                   "logSession": False,
                   "os": "Android",
                   "model": "one",
                   "osVersion": "1.3.3.7",
                   "appVersion": "8.00",
                   "manufacturer": "python",
                   "isTablet": False,
                   "stopOnErrors": [],
                   "language": "ost",
                   "deviceId": "10000000-0000-0000-0000-000000000001",
                   "country": "DK"}

        return self._request('create', payload)

    def login(self):
        payload = {"loginId": self.cpr,
                   "loginCode": self.pin}
        return self._request('login', payload)

    def accounts(self):
        accounts = self._request('accounts')['Accounts']
        act = []
        for account in accounts:
            act.append({'account_number': account['AccountNumber'], 'name': account[
                       'AccountName'], 'balance': account['Balance']})
        return act

    def sum(self):
        return sum([x['balance'] for x in self.accounts()])

    def transactions(self, account_number):
        transactions = self._request('account', account_number=account_number)
        return transactions

    def bootstrap(self):
        # Sleep to reduce Trifork.GMB.Service.Util.MagicException's at endpoint
        self.init_session()
        sleep(2)
        self.create_session()
        sleep(2)
        self.login()
        sleep(2)

cpr = 1234
pin = 1234
obj = DKBank(cpr, pin)
obj.bootstrap()
# print obj.sum()
