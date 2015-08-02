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
PORTO_ALEGRE = '-51.26681,-30.261167,-51.086999,-29.956573'


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


def subscribe_script_to_channel(redis_conn, script, channel):
    sha = redis_conn.execute_command("SCRIPT", "LOAD", script)
    redis_conn.execute_command("SSUBSCRIBE", sha, channel)
    return sha


def load_scripts(redis_conn):
    # increment counter for each message
    subscribe_script_to_channel(redis_conn, "return redis.call('incr', 'messages')", "twitter")

    # set message as last_message
    subscribe_script_to_channel(redis_conn, "redis.call('set', 'last_message', ARGV[2])", "twitter")

    # create a new channel if text messages
    subscribe_script_to_channel(redis_conn, "redis.call('publish', 'twitter_text', cjson.decode(ARGV[2]).text)", "twitter")

    # set message text as last_message_text
    subscribe_script_to_channel(redis_conn, "redis.call('set', 'last_message_text', ARGV[2])", "twitter_text")

    # create a channel for hashtags
    subscribe_script_to_channel(redis_conn, """for hash_tag in ARGV[2]:gmatch('#%S+') do
        redis.call('publish', 'hash_tags', hash_tag)
    end""", "twitter_text")

    # count top hashtags
    subscribe_script_to_channel(redis_conn, "redis.call('zincrby', 'hashtags', 1, ARGV[2])", "hash_tags")


def top_hash_tags(redis_conn, num=5):
    return redis_conn.zrevrangebyscore("hashtags", max="+inf",  min="0", start=0, num=num, withscores=True)


def stream(redis_conn):
    twitter_api = TwitterAPI(
        twitter['consumer_key'],
        twitter['consumer_secret'],
        twitter['access_token_key'],
        twitter['access_token_secret'])
    r = twitter_api.request('statuses/filter', {'locations': BRAZIL})
    i = 0
    for item in r:
        i += 1
        redis_conn.publish("twitter", json.dumps(item))
        #print "Message: " + item.get('text', "")
        if i % 50 == 0:
            print "******* TOP HASHTAGS *******"
            for hashtag, count in top_hash_tags(redis_conn, num=20):
                print hashtag, count
            print "****************************"


def main():
    redis_conn = redis.Redis(REDIS_HOST, REDIS_PORT)
    load_scripts(redis_conn)
    redis_conn.delete('hashtags')
    stream(redis_conn)


if __name__ == "__main__":
    main()
