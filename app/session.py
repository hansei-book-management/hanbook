import redis

from app.config import *

rd = redis.StrictRedis(host=REDIS, port=6379, db=0)
