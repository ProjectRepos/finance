# Load master data into the mongo database
# Uses with python3 <input file>

from pymongo import MongoClient
import datetime
import sys
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

logging.info("Connecting to MongoDB.")
client = MongoClient('localhost', 5001)
db = client.finance
db_collection = db.master

logging.info("Opening file {0}".format(sys.argv[1]))
with open(sys.argv[1],errors='ignore') as ifile:
    data = set([x.rstrip() for x in ifile])
    data_dict = [{
        "date":x.split(',')[0],
        "account":x.split(',')[1],
        "ammount":x.split(',')[2],
        "comment":x.split(',')[3],
        "payee":x.split(",")[4],
        "category":x.split(',')[5],
        "injest_time":datetime.datetime.utcnow()} for x in data]

logging.info('Inserting {0} records into database.'.format(len(data)))
db_collection.insert_many(data_dict)
