from random import randrange

LEADER = 0
CANDIDATE = 1
FOLLOWER = 2
LOW_TIMEOUT = 150
HIGH_TIMEOUT = 300

REQUESTS_TIMEOUT = 50
HB_TIME = 50
MAX_LOG_WAIT = 150

def random_timeout():
    return randrange(LOW_TIMEOUT, HIGH_TIMEOUT) / 1000