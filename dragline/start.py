from gevent import monkey, spawn, joinall
monkey.patch_all()

from zipfile import ZipFile
from multiprocessing import Process
import os
from runner import main
from redis import ConnectionPool
import redisds

import signal

import time
import runner



import MySQLdb

connection = MySQLdb.connect(host="localhost", user="root", passwd="passme", db="dragline")

# pool=ConnectionPool(host="192.168.0.15",db=1)

# start_queue = redisds.Queue("dragline",namespace="test",connection_pool=pool)
# start_queue.put("1")
cursor = connection.cursor()



import argparse
def start(run_id):

    qry = "SELECT spider_id FROM spider_run WHERE id=%d" % int((run_id))
    print run_id
    cursor.execute(qry)
    connection.commit()
    row = cursor.fetchall()
    print row
    if row:
        spider_id = row[0][0]
        qry = "SELECT zipfile FROM spider_spider WHERE id=%d" % int((spider_id))
        cursor.execute(qry)
        connection.commit()
        result = cursor.fetchall()
        if result:
            zipfile = result[0][0]


            #print zipfile
            f = open("zipfile.zip", "w")
            f.write(zipfile)
            f.close()
        else:
            raise Exception

        #unzip("zipfile.zip","spiders")
        directory = "spider_" + str(spider_id)
        if not os.path.exists(directory):
            os.makedirs(directory)
        zf = ZipFile("zipfile.zip")
        zf.extractall(directory)
        zf.close()
        files = os.walk(directory)
        for folder in files:
            pass

        spider_dir = folder[0]

        runner.main(spider_dir,False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('run_id', type=int)
    args = parser.parse_args()
    start(args.run_id)







