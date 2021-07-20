from threading import Lock, Thread
import time
import config as cfg
from log import Logging
from os import path, getenv, makedirs
from datastore.rocks import RockStore
from datastore.memory import MemoryStore

class Store:

    def __init__(self, store_type: str='memory', **kwargs):
        self.commit_id = 0
        self.log = list()
        self.staged = None
        self.db = self.__get_database(store_type, **kwargs)
        self.__lock = Lock()
        # self.__file_handle = open()
        self.__data_dir = getenv('DATA_DIR', './data')
        self.__log_file = getenv('LOG_FILENAME', 'append.log')
        self.__data_file = getenv('DATA_FILENAME', 'data.json')
        self.logger = Logging('INFO', 'store.log').get_logger()

    def __get_database(self, store_type: str, **kwargs):
        if store_type == 'database':
            database = kwargs.get('database', None)
            data_dir = kwargs.get('data_dir', None)
            db = RockStore(database=database, data_dir=data_dir)
        else:
            db = MemoryStore()
        return db

    def __file_open(self, filepath):
        if not path.exists():
            makedirs(self.__data_dir)

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
            Thread(target=self.send_data, args=(
                log_message, transport, log_confirmations,)).start()

            while sum(log_confirmations) + 1 < majority:
                waited += 0.0005
                time.sleep(0.0005)
                if waited > cfg.MAX_LOG_WAIT / 1000:
                    self.logger.info(
                        f"waited {cfg.MAX_LOG_WAIT} ms, update rejected:")
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
        self.logger.info(
            "majority reached, replied to client, sending message to commit")
        return True

    def send_data(self, message, transport, confirmations: list = None):
        for i, peer in enumerate(transport.peers):
            reply = transport.send_data(peer, message)
            if reply and confirmations:
                confirmations[i] = True

    def get(self, payload):
        key = payload["key"]
        value = self.db.get(key=key)
        payload.update({'value': value})
        return payload

    def commit(self):
        self.commit_id += 1
        with self.__lock:
            self.log.append(self.staged)
            key = self.staged['key']
            value = self.staged['value']
            self.staged = None
            self.db.put(key, value)
