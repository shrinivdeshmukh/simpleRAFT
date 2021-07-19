import config as cfg
import time
from threading import Thread, Lock
from transport import Transport
from store import Store
from log import Logging

class Election:
    def __init__(self, transport: Transport):
        self.timeout_thread = None
        self.status = cfg.FOLLOWER
        self.term = 0
        self.vote_count = 0
        self.store = Store()
        self.election_logger = Logging('INFO', 'election.log').get_logger()
        self.__transport = transport

    def start_election(self):
        self.election_logger.info('starting election')
        self.term += 1
        self.vote_count = 0
        self.status = cfg.CANDIDATE
        self.peers = self.__transport.peers
        self.majority = (2 + len(self.peers)) // 2
        self.init_timeout()
        self.increment_vote()
        self.ask_for_vote()

    def ask_for_vote(self):
        for peer in self.peers:
            Thread(target=self.send_vote_request, args=(peer, self.term)).start()
    
    def send_vote_request(self, voter, term):
        message = {
            'term': term,
            'commit_id': self.store.commit_id,
            'staged': self.store.staged
        }
        while self.status == cfg.CANDIDATE and self.term == term:
            vote_reply = self.__transport.vote_request(voter, message)
            if vote_reply:
                choice = vote_reply['choice']
                self.election_logger.info(f'CHOICE from {voter} is {choice}, type is {type(choice)}, msg is {vote_reply}')
                if choice and self.status == cfg.CANDIDATE:
                    self.increment_vote()
                elif not choice:
                    term = vote_reply['term']
                    if term > self.term:
                        self.status = cfg.FOLLOWER
                break

    def decide_vote(self, term, commit_id, staged):
        if self.term < term and self.store.commit_id <= commit_id and (staged or (self.store.staged == staged)):
            self.reset_timeout()
            self.term = term
            return True, self.term
        else:
            return False, self.term

    def increment_vote(self):
        self.vote_count += 1
        if self.vote_count >= self.majority:
            self.status = cfg.LEADER
            self.start_heartbeat()
            self.election_logger.info(f'leader >>> {self.status}')

    def start_heartbeat(self):
        if self.store.staged:
            self.store.put(self.term, self.store.staged, self.__transport, self.majority)

        for peer in self.peers:
            Thread(target=self.send_heartbeat, args=(peer,)).start()

    def send_heartbeat(self, peer: str):
        if self.store.log:
            self.update_follower_commit(peer)
        message = {'term': self.term, 'addr': self.__transport.addr}
        while self.status == cfg.LEADER:
            start = time.time()
            reply = self.__transport.heartbeat(peer=peer, message=message)
            if reply:
                if reply['term'] > self.term:
                    self.term = reply['term']
                    self.status = cfg.FOLLOWER
                    self.init_timeout()
            delta = time.time() - start
            time.sleep((cfg.HB_TIME - delta) / 1000)

    def update_follower_commit(self, follower):
        first_message = {'term': self.term, 'addr': self.__transport.addr}
        second_message = {
            'term': self.term,
            'addr': self.__transport.addr,
            'action': 'commit',
        }
        reply = self.__transport.heartbeat(follower, first_message)
        i = -1
        if reply:
            while reply["commit_id"] < self.store.commit_id:
                second_message.update({'payload': self.store.log[i]})
                reply = self.__transport.heartbeat(follower, second_message)
                i = i -1

    def heartbeat_handler(self, message: dict):
        term = message['term']
        if self.term <= term:
            self.leader = message['addr']
            self.reset_timeout()

            if self.status == cfg.CANDIDATE:
                self.status = cfg.FOLLOWER
            elif self.status == cfg.LEADER:
                self.status =cfg.FOLLOWER
                self.init_timeout()

            if self.term < term:
                self.term = term
            
            if 'action' in message:
                self.store.action_handler(message)
        return self.term, self.store.commit_id

    def handle_put(self, payload):
        reply = self.store.put(self.term, payload, self.__transport, self.majority)
        return reply

    def handle_get(self, payload):
        return self.store.get(payload)

    def timeout_loop(self):
        while self.status != cfg.LEADER:
            delta = self.election_time - time.time()
            if delta < 0:
                if self.__transport.peers:
                    self.start_election()
            else:
                time.sleep(delta)

    def init_timeout(self):
        try:
            self.election_logger.info('starting timeout')
            self.reset_timeout()
            if self.timeout_thread and self.timeout_thread.is_alive():
                return
            self.timeout_thread = Thread(target=self.timeout_loop)
            self.timeout_thread.start()
        except Exception as e:
            raise e

    def reset_timeout(self):
        self.election_time = time.time() + cfg.random_timeout()