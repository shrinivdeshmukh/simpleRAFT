from random import randrange

LEADER = 0
CANDIDATE = 1
FOLLOWER = 2
LOW_TIMEOUT = 100
HIGH_TIMEOUT = 500

REQUESTS_TIMEOUT = 50
HB_TIME = 20
MAX_LOG_WAIT = 1500

def random_timeout():
    return randrange(LOW_TIMEOUT, HIGH_TIMEOUT) / 1000