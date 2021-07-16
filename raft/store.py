from threading import Lock, Thread
import time
import config as cfg

class Store:

    def __init__(self):
        self.commit_id = 0
        self.log = list()
        self.staged = None
        self.db = dict()
        self.__lock = Lock()

    def action_handler(self, message: dict):
        action = message['action']
        payload = message['payload']
        if action == 'log':
            self.staged = payload
        elif action == 'commit':
            if not self.staged:
                self.staged = payload
            self.commit()
        return

    def put(self, term, payload, transport, majority):
        with self.__lock:
            self.staged = payload
            waited = 0
            log_message = {
                'term': term,
                'addr': transport.addr,
                'payload': payload,
                'action': 'log',
                'commit_id': self.commit_id
            }
            log_confirmations = [False] * len(transport.peers)
            Thread(target=self.send_data, args=(log_message, transport, log_confirmations,)).start()
        
            while sum(log_confirmations) + 1 < majority:
                waited += 0.0005
                time.sleep(0.0005)
                if waited > cfg.MAX_LOG_WAIT / 1000:
                    print(f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
                    return False

            commit_message = {
            "term": term,
            "addr": transport.addr,
            "payload": payload,
            "action": "commit",
            "commit_id": self.commit_id
        }
        self.commit()
        Thread(target=self.send_data,
                         args=(commit_message, transport,)).start()
        print("majority reached, replied to client, sending message to commit")
        return True

    def send_data(self, message, transport, confirmations: list=None):
        for i, peer in enumerate(transport.peers):
            reply = transport.send_data(peer, message)
            if reply and confirmations:
                confirmations[i] = True
        
    def get(self, payload):
        key = payload["key"]
        if key in self.db:
            payload["value"] = self.db[key]
            return payload
        else:
            return None

    def commit(self):
        self.commit_id += 1
        self.log.append(self.staged)
        key = self.staged['key']
        value = self.staged['value']
        self.staged = None
        self.db[key] = value
        print("ALL DATA", self.db)