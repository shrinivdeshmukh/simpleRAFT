from transport import Transport
import config as cfg
from queue import Queue
import time
import threading
import messages as msg_in


class Node(Transport):

    def __init__(self, my_ip: str, peers: list=None):
        self.term = 0
        self.vote_count = 0
        self.status = cfg.FOLLOWER
        self.timeout_thread = None
        self.log = list()
        self.majority = (2 + len(peers)) // 2
        self.DB = dict()
        self.staged = None
        self.leader = None
        super().__init__(my_ip)
        self.addr = my_ip
        if self.addr in peers:
            peers.remove(self.addr)
        self.peers = peers
        self.commit_id = 0

    def start_election(self):
        print('starting election')
        self.term += 1
        self.vote_count = 0
        self.status = cfg.CANDIDATE
        self.init_timeout()
        self.increment_vote()
        self.send_vote_req()

    def increment_vote(self):
        self.vote_count += 1
        if self.vote_count >= self.majority:
            print("ELECTING MYSELF AS LEADER")
            self.status = cfg.LEADER
            self.start_heartbeat()

    def send_vote_req(self):
        for peer in self.peers:
            threading.Thread(target=self.ask_for_vote, args=(
                peer, self.term)).start()

    def ask_for_vote(self, peer, term):
        message = msg_in.ask_for_vote(term, self.commit_id, self.staged)
        while self.status == cfg.CANDIDATE and self.term == term:
            reply = self.ask_for_vote_transport(peer, message)
            if reply:
                choice = reply[peer]['choice']
                if choice and self.status == cfg.CANDIDATE:
                    self.increment_vote()
                elif not choice:
                    term = reply[peer]['term']
                    if term > self.term:
                        self.term = term
                        self.status == cfg.FOLLOWER
                break

    def decide_vote(self, term, commit_id, staged):
        if self.term < term and self.commit_id <= commit_id and (
                staged or (self.staged == staged)):
            self.reset_timeout()
            self.term = term
            return True, self.term
        else:
            return False, self.term

    def start_heartbeat(self):
        print("STARTING HEARTBEAT")
        if self.staged:
            self.handle_put(self.staged)

        for peer in self.peers:
            threading.Thread(target=self.send_heartbeat, args=(peer,)).start()

    def send_heartbeat(self, peer):
        if self.log:
            self.update_follower_commitid(peer)

        message = {'term': self.term, 'addr': f'{self.host}:{self.port}'}
        while self.status == cfg.LEADER:
            start = time.time()
            reply = self.heartbeat_transport(peer, message)
            if reply:
                term = reply[peer]['term']
                if term > self.term:
                    self.term = term
                    self.status = cfg.FOLLOWER
                    self.init_timeout()
            delta = time.time() - start
            time.sleep((cfg.HB_TIME - delta) / 1000)

    def update_follower_commitid(self, peer):
        first_message = {"term": self.term, "addr": f'{self.host}:{self.port}'}
        second_message = {
            "term": self.term,
            "addr": f'{self.host}:{self.port}',
            "action": "commit",
            "payload": self.log[-1]
        }
        reply = self.heartbeat_transport(peer, message)
        if reply and reply[peer]['commit_id'] < self.commit_id:
            reply = self.heartbeat_transport(peer, message)

    def analyze_heartbeat(self, msg):
        term = msg["term"]
        if self.term <= term:
            self.leader = msg["addr"]
            self.reset_timeout()
            if self.status == cfg.CANDIDATE:
                self.status = cfg.FOLLOWER
            elif self.status == cfg.LEADER:
                self.status = cfg.FOLLOWER
                self.init_timeout()
            if self.term < term:
                self.term = term

            if "action" in msg:
                print("received action", msg)
                action = msg["action"]
                if action == "log":
                    payload = msg["payload"]
                    self.staged = payload
                elif self.commit_id <= msg["commit_id"]:
                    if not self.staged:
                        self.staged = msg["payload"]
                    self.commit()

        return self.term, self.commit_id

    def reset_timeout(self):
        self.election_time = time.time() + cfg.random_timeout()

    def init_timeout(self):
        self.reset_timeout()

        if self.timeout_thread and self.timeout_thread.isAlive():
            return
        self.timeout_thread = threading.Thread(target=self.timeout)
        self.timeout_thread.start()

    def timeout(self):
        while self.status != cfg.LEADER:
            delta = self.election_time - time.time()

            if delta < 0:
                self.start_election()
            else:
                time.sleep(delta)

    def handle_put(self, payload):
        print("putting", payload)
        self.lock.acquire()
        self.staged = payload
        waited = 0
        log_message = {
            "term": self.term,
            "addr": self.addr,
            "payload": payload,
            "action": "log",
            "commit_id": self.commit_id
        }

        # spread log  to everyone
        log_confirmations = [False] * len(self.peers)
        threading.Thread(target=self.spread_update,
                         args=(log_message, log_confirmations)).start()
        while sum(log_confirmations) + 1 < self.majority:
            waited += 0.0005
            time.sleep(0.0005)
            if waited > cfg.MAX_LOG_WAIT / 1000:
                print(f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
                self.lock.release()
                return False
        commit_message = {
            "term": self.term,
            "addr": self.addr,
            "payload": payload,
            "action": "commit",
            "commit_id": self.commit_id
        }
        self.commit()
        threading.Thread(target=self.spread_update,
                         args=(commit_message, None, self.lock)).start()
        print("majority reached, replied to client, sending message to commit")
        return True

    def handle_get(self, payload):
        print("getting", payload)
        key = payload["key"]
        if key in self.DB:
            payload["value"] = self.DB[key]
            return payload
        else:
            return None

    def spread_update(self, message, confirmations=None, lock: threading.Lock = None):
        for i, peer in enumerate(self.peers):
            reply = self.heartbeat_transport(peer, message)
            if reply and confirmations:
                confirmations[i] = True
        if lock:
            lock.release()

    def commit(self):
        self.commit_id += 1
        self.log.append(self.staged)
        key = self.staged["key"]
        value = self.staged["value"]
        self.DB[key] = value
        self.staged = None


if __name__ == '__main__':
    import sys
    port = sys.argv[1]
    peers = (sys.argv[2]).split(',')
    n = Node(port, peers)
    t1 = threading.Thread(target=n.serve)
    t2 = threading.Thread(target=n.client, args=(peers,))
    t3 = threading.Thread(target=n.init_timeout)
    t1.start()
    t2.start()
    t3.start()
