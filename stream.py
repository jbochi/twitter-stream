from TwitterAPI import TwitterAPI
import json
import os
import redis
import yaml


with open("twitter_credentials.yaml") as f:
    twitter = yaml.load(f)

#http://boundingbox.klokantech.com/
RIO_DE_JANEIRO = '-43.793888,-23.076426,-43.096904,-22.746033'
BRAZIL = '-74.0,-33.9,-28.6,5.3'
US = '-125.9,23.4,-63.3,50.2'


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def main():
    redis_conn = redis.Redis(REDIS_HOST, REDIS_PORT)
    twitter_api = TwitterAPI(
        twitter['consumer_key'],
        twitter['consumer_secret'],
        twitter['access_token_key'],
        twitter['access_token_secret'])
    r = twitter_api.request('statuses/filter', {'locations': US})
    for item in r:
        redis_conn.publish("twitter", json.dumps(item))
        print item.get('text')

if __name__ == "__main__":
    main()
