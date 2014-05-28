from gevent import monkey, spawn, joinall
monkey.patch_all()

import sys
import argparse
import os
import traceback
import logging
import logging.config
from defaultsettings import SpiderSettings
from crawl import Crawler


logging.config.dictConfig(SpiderSettings.LOGCONFIG)
logger = logging.getLogger("dragline")


def load_module(path, filename):
    try:
        sys.path.insert(0, path)
        module = __import__(filename)
        del sys.path[0]
        return module
    except Exception as e:
        logger.exception("Failed to load module %s" % filename)
        raise ImportError


def main(filename, directory, resume, conf=SpiderSettings()):
    module = load_module(directory, filename.strip('.py'))
    spider = getattr(module, "Spider")(conf)
    spider.logger = logging.getLogger(spider._name)
    Crawler.load_spider(spider, resume)
    crawlers = [Crawler() for i in xrange(5)]
    try:
        joinall([spawn(crawler.process_url) for crawler in crawlers])
    except KeyboardInterrupt:
        pass
    except:
        logger.exception("Unable to complete")
    else:
        logger.info("Crawling completed")


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('spider', help='spider file name')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    path, filename = os.path.split(os.path.abspath(args.spider))
    main(filename, path, args.resume)

if __name__ == "__main__":
    run()
