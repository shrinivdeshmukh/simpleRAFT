from transport import Transport
from election import Election
from store import Store
from threading import Thread

class Node(Transport):

    def __init__(self, my_ip: str, peers: list, timeout: int, **kwargs):
        self.__store = Store(**kwargs)
        self.__transport = Transport(my_ip, timeout=timeout)
        self.__election = Election(transport=self.__transport, store=self.__store)
        self.__peers = peers

    def run(self):
        print('starting transport')
        self.start_transport()
        print('starting add peers')
        self.start_adding_peers(peers=self.__peers)
        print('starting timeout node')
        self.start_timeout()
        print('timeout started')

    def start_transport(self):
        Thread(target=self.__transport.serve, args=(self.__election,)).start()

    def start_adding_peers(self, peers):
        if peers:
            for peer in peers:
                Thread(target=self.__transport.req_add_peer, args=(peer,)).start()

    def start_timeout(self):
        self.__election.init_timeout()