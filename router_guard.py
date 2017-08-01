#!/usr/bin/env python3
# vim: set fileencoding=utf-8 tabstop=4 expandtab shiftwidth=4 softtabstop=4:

# Imports
import argparse
import codecs
import locale
import logging
import requests
import time
from fake_useragent import UserAgent

VERSION=u'20170801'

DELAY_SECS=5

def enable_debugging():
    # Enabling debugging at http.client level (requests->urllib3->http.client)
    # you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # the only thing missing will be the response.body which is not logged.
    try: # for Python 3
        from http.client import HTTPConnection
    except ImportError:
        from httplib import HTTPConnection
    HTTPConnection.debuglevel = 1

    logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("yip")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


class RouterGuard(object):
    def __init__(self, address, username, password, protocol='http'):
        super().__init__()

        self.protocol = protocol
        self.address = address
        self.username = username
        self.password = password

        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': UserAgent().chrome,
        }

    def _get_url(self, page):
        if len(page) > 0 and page[0] == '/':
            return self.protocol + '://' + self.address + page
        else:
            return self.protocol + '://' + self.address + '/' + page

    @staticmethod
    def _exec(action, url, *args, **kwargs):
        try:
            r = action(url, *args, **kwargs)
            if r.status_code == 200:
                logging.info("  done")
                return True
            else:
                logging.error("  failed {url}: {status}".format(url=url, status=r.status_code))
                return False
        except Exception as ex:
            logging.error("  failed {url} with exception: {ex}".format(url=url, ex=ex))
            return False

    def login(self):
        logging.info("Login to {0} as {1}...".format(self.address, self.username))

        try:
            self.session.get(self._get_url(''))
            self.session.get(self._get_url('/cgi-bin/index2.asp'))
        except Exception as ex:
            logging.error("  failed {url} with exception: {ex}".format(url=self._get_url(''), ex=ex))
            return False

        self.session.cookies.set(name='UID', value=self.username, domain=self.address, path='/')
        self.session.cookies.set(name='PSW', value=self.password, domain=self.address, path='/')

        return self._exec(self.session.get, self._get_url('/cgi-bin/content.asp'))

    def logout(self):
        logging.info("Logout from {0}...".format(self.address))

        return self._exec(self.session.get, self._get_url('/cgi-bin/logout.cgi'))

    def reset(self):
        logging.info("Reseting...")

        return self._exec(
            self.session.post,
            self._get_url('/cgi-bin/mag-reset.asp'),
            {
                'rebootflag': '1',
                'restoreFlag': '1',
                'isCUCSupport': '0',
            }
        )

    def check(self, url="http://www.baidu.com"):
        logging.info("Checking '{0}'...".format(url))

        return self._exec(requests.get, url)


def main(**args):
    if args['verbose']:
        enable_debugging()

    guard = RouterGuard(
        address='192.168.1.1', protocol='http',
        username='useradmin', password='nE7jA%5m')

    if guard.login():
        if args['command'] == "reset":
            guard.reset()
            while True:
                time.sleep(DELAY_SECS)
                if guard.login():
                    break

            while True:
                time.sleep(DELAY_SECS)
                if guard.check():
                    break
        else:
            guard.check()
            guard.logout()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=u'''\
description''')

    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', default=False, help=u'Be moderatery verbose')
    parser.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False, help=u'Only show warning and errors')
    parser.add_argument('--version', action='version', version=VERSION, help=u'Show version and quit')
    parser.add_argument('command', nargs='?', default='check', choices=['check', 'reset'], help=u'Command')

    args = parser.parse_args()

    # 日志初始化
    log_format = u'%(asctime)s %(levelname)s %(message)s'

    if args.quiet:
        logging.basicConfig(level=logging.WARNING, format=log_format)
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG, format=log_format)
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)

    main(**vars(args))
