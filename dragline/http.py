import six
if six.PY2:
    from urllib import urlencode
    from urlparse import urldefrag
else:
    from urllib.parse import urlencode
import socket
from hashlib import sha1
import time
import requests
from .defaultsettings import RequestSettings
from collections import defaultdict
import operator
import socks
from random import randint
from .redisds import Dict
import types
import re

socket.setdefaulttimeout(300)


class RequestError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Request(object):

    """
    :param url: the URL of this request
    :type url: string
    :param method: the HTTP method of this request. Defaults to ``'GET'``.
    :type method: string
    :param headers: the headers of this request.
    :type headers: dict
    :param callback: name of the function to call after url is downloaded.
    :type callback: string
    :param meta:  A dict that contains arbitrary metadata for this request.
    :type meta: dict
    """

    settings = RequestSettings()
    stats = Dict("stats:*")
    method = "GET"
    form_data = None
    headers = {}
    callback = None
    meta = None
    retry = 0
    cookies = None
    callback_object = None
    dontfilter = False
    session = requests.Session()
    timeout = None
    proxy = []
    _cookie_regex = re.compile('(([^ =]*)?=[^ =]*?;)')

    def __init__(self, url, method=None, form_data=None, headers=None, callback=None, meta=None,
                 cookies=None, proxy=None, timeout=None, dontfilter=None):
        if isinstance(url, str):
            self.url = str(url)
        elif isinstance(url, unicode):
            self.url = unicode(url)
        else:
            AssertionError("Invalid url type")
        if form_data:
            self.method = 'POST'
            self.form_data = form_data
        if method:
            assert method in ['GET', 'POST', 'HEAD', 'PUT', 'DELETE'], 'INVALID METHOD'
            self.method = method
        if callback:
            self.callback = callback
        if meta:
            self.meta = meta
        if headers:
            self.headers = headers
        if proxy:
            self.proxy = proxy
        if cookies:
            self.cookies = cookies
        if dontfilter:
            self.dontfilter = True
        if timeout:
            self.timeout = timeout

    def __getstate__(self):
        d = self.__dict__.copy()
        if isinstance(self.callback, types.MethodType) and hasattr(self.callback, 'im_self'):
            d['callback'] = self.callback.__name__
            if not Request.callback_object == self.callback.im_self:
                Request.callback_object = self.callback.im_self
        return d

    def __setstate__(self, d):
        if 'callback' in d and isinstance(d['callback'], str):
            d['callback'] = getattr(Request.callback_object, d['callback'])
        self.__dict__ = d

    def __repr__(self):
        return "<%s>" % self.get_unique_id(False)

    def __str__(self):
        return self.get_unique_id(False)

    def __usha1(self, x):
        """sha1 with unicode support"""
        if isinstance(x, unicode):
            return sha1(x.encode('utf-8')).hexdigest()
        else:
            return sha1(x).hexdigest()

    def send(self):
        """
        This function sends HTTP requests.

        :returns: response
        :rtype: :class:`dragline.http.Response`
        :raises: :exc:`dragline.http.RequestError`: when failed to fetch contents

        >>> req = Request("http://www.example.org")
        >>> response = req.send()
        >>> print response.headers['status']
        200

        """

        try:
            if self.timeout:
                timeout = self.timeout
            else:
                timeout = max(self.settings.DELAY, self.settings.TIMEOUT)
            proxy_choice = randint(0, len(self.settings.PROXIES))
            args = dict(url=self.url, method=self.method, data=self.form_data,
                        verify=False, timeout=timeout, cookies=self.cookies)
            if len(self.proxy) > 0:
                proxy = self.proxy
            elif not proxy_choice == 0:
                proxy = self.settings.PROXIES[proxy_choice - 1]
            else:
                proxy = None
            if proxy:
                pattern = "http://%s:%s" if len(proxy) == 2 else "http://%s:%s@%s:%s"
                args['proxies'] = {"http": pattern % proxy}
            args['headers'] = self.settings.HEADERS
            args['headers'].update(self.headers)
            res = Response(self.session.request(**args))

            if self.settings.AUTOTHROTTLE:
                self.updatedelay(res.elapsed)
                time.sleep(self.settings.DELAY)
        except Exception as e:
            raise RequestError(e.message)
        else:
            self.stats.inc('pages_crawled')
            self.stats.inc('request_bytes', len(res))
        return res

    def get_unique_id(self, hashing=True):
        request = self.method + ":" + urldefrag(self.url)[0]
        if self.form_data:
            request += ":" + urlencode(sorted(self.form_data.items(),
                                              key=operator.itemgetter(1)))
        if hashing:
            return self.__usha1(request)
        else:
            return request

    @classmethod
    def updatedelay(cls, delay):
        cls.settings.DELAY = min(
            max(cls.settings.MIN_DELAY, delay,
                (cls.settings.DELAY + delay) / 2.0),
            cls.settings.MAX_DELAY)


class Response(requests.Response):

    """
    This function is used to create user defined
    response to test your spider and also in many
    other cases.

    :param url: the URL of this response
    :type url: string

    :param headers: the headers of this response.
    :type headers: dict

    :param body: the response body.
    :type body: str

    :param meta: meta copied from request
    :type meta: dict

    """
    url = None
    body = ""
    headers = {}
    meta = None
    status = None

    def __init__(self, response, meta=None):
        self.__dict__ = response.__dict__
        self.body = self.content
        self.status = self.status_code
        if meta:
            self.meta = meta

    def __len__(self):
        if 'content-length' in self.headers:
            return int(self.headers['content-length'])
        return len(self.body)
