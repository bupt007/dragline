from gevent import monkey, spawn, joinall
monkey.patch_all()

import httplib2
import httpcache2
from redisds import RedisQueue, RedisSet
from gevent.coros import BoundedSemaphore

from lxml import html
import sys
import os
import re
import urllib
import time
import traceback
from htmlhandler import Parser


class Crawl(object):
    lock = BoundedSemaphore(1)
    current_urls = set()
    running_count = 0

    def __init__(self):
      
        self.parser = Crawl.Parsers
        self.http = httplib2.Http(timeout=5)

    @classmethod
    def count(crawl):
        return crawl.running_count

    @classmethod
    def inc_count(crawl, url):
        crawl.lock.acquire()
        crawl.current_urls.add(url)
        crawl.running_count += 1
        crawl.lock.release()

    @classmethod
    def dec_count(crawl, url):
        crawl.lock.acquire()
        crawl.running_count -= 1
        crawl.lock.release()

    @classmethod
    def insert(crawl, url):
        if not any(url in i for i in (crawl.current_urls, crawl.visited_urls, crawl.url_queue)):
            # print "found", #
            crawl.url_queue.put(url)

    def process_url(self):
        while True:


            url = self.url_queue.get(timeout=2)
            if url:
                #print "processing", url
                self.inc_count(url)
                try:
                    time.sleep(2)
                    head, content = self.http.request(urllib.quote(url,":/"), 'GET')
                    for i in self.parser.parse(head, url, content):
                        self.insert(i)
                    self.visited_urls.add(url)
                    self.dec_count(url)
                    # print "processed", url
                except Exception, e:
                    print "failed", url, traceback.format_exc()
            else:
                print self.count()
                if not self.count():
                    break


if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
    import main
    Crawl.url_queue = RedisQueue(main.NAME, 'urls')
    Crawl.visited_urls = RedisSet(main.NAME, 'visited')
    Crawl.Parsers = Parser(main.ALLOWED_URLS, main.PARSERS)
    # if Crawl.url_queue.isempty():
    #     Crawl.visited_urls.clear()
    for url in main.START_URLS:
        Crawl.insert(url)
    crawlers = []
    for i in xrange(5):
        crawler = Crawl()
        crawlers.append(spawn(crawler.process_url))
    joinall(crawlers)
    print "finished"
else:
    exit()
