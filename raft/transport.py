from socket import socket, AF_INET, SOCK_STREAM, gethostname, gethostbyname
from threading import Thread, Lock
import selectors
from time import sleep
from json import loads, dumps, JSONDecodeError
import config as cfg

class Transport:

    def __init__(self, my_ip: str):
        self.host, self.port = my_ip.split(':')
        self.port = int(self.port)
        self.selector = selectors.DefaultSelector()
        self.server = socket(AF_INET, SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()
        self.lock = Lock()
        self.__CODER = 'utf-8'
        self.__HEADER = 1024
        self.heartbeat_handler = None
       
    def accept(self, server, mask):
        client, address = server.accept()
        self.selector.register(client, selectors.EVENT_READ, self.handler)

    def handler(self, client, mask):
        data = client.recv(1024).decode('utf-8')
        if data:
            data = self.decode_msg(data)
            if isinstance(data, dict):
                if data['type'] == 'vote_request':
                    term = data['term']
                    commit_id = data['commit_id']
                    staged = data['staged']
                    vote_response, term = self.decide_vote(term, commit_id, staged)
                    client.send(self.encode_msg({'type': 'vote_response', 'term': term, 'choice': vote_response}))
                elif data['type'] == 'heartbeat':
                    term, commit_id = self.analyze_heartbeat(data)
                    client.send(self.encode_msg({'type': 'heartbeat_response', 'term': term, 'commit_id': commit_id}))
                elif data['type'] == 'put':
                    if not self.status == cfg.LEADER:
                        reply = self.redirect_to_leader(self.encode_msg(data))
                        client.send(self.encode_msg(reply))
                    else:    
                        put_response = self.handle_put({x: data[x] for x in data if x not in ['type']})
                        client.send(self.encode_msg({'type': 'put_response', 'success': put_response}))
                elif data['type'] == 'get':
                    if not self.status == cfg.LEADER:
                        reply = self.redirect_to_leader(self.encode_msg(data))
                        client.send(self.encode_msg(reply))
                    else:
                        db_data = self.handle_get({x: data[x] for x in data if x not in ['type']})
                        client.send(self.encode_msg({'type': 'get_response', 'data': db_data}))
            else:    
                print(f'echoing {data} to {client}')
                client.send(bytes(data, encoding=self.__CODER))
        else:
            self.selector.unregister(client)
            client.close()

    def redirect_to_leader(self, message):
        leader_host, leader_port = (self.leader).split(':')
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((leader_host, int(leader_port)))
        s.send(message)
        leader_reply = s.recv(self.__HEADER).decode(self.__CODER)
        return leader_reply

    def serve(self):
        self.selector.register(self.server, selectors.EVENT_READ, self.accept)
        while True:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def client(self, peers):
        for peer in peers:
            Thread(target=self.connect, args=(peer,)).start()

    def connect(self, address):
        conn = self.retry(address)
        conn.send(bytes(f'PEER ADDRESS: {self.host}:{self.port}', encoding=self.__CODER))
        msg = conn.recv(1024).decode('utf-8')

    def retry(self, address):
        host, port = address.split(':')
        i = 1
        while True:
            try:
                client = socket(AF_INET, SOCK_STREAM)
                client.connect((host, int(port)))
                return client
            except ConnectionRefusedError:
                print(f'Reconnection attempt {i} to peer {address}')
                i += 1
                sleep(2)
                continue

    def ask_for_vote_transport(self, peer, message: dict):
        print(f'asking {peer} for vote')
        message.update({'type': 'vote_request'})
        conn = self.retry(peer)
        encoded_msg = self.encode_msg(message)
        conn.send(encoded_msg)
        vote_reply = conn.recv(self.__HEADER).decode(self.__CODER)
        return {peer: loads(vote_reply)}

    def heartbeat_transport(self, peer: str, message: dict):
        message.update({'type': 'heartbeat'})
        conn = self.retry(peer)
        encode_msg = self.encode_msg(message)
        conn.send(encode_msg)
        heartbeat_reply = conn.recv(self.__HEADER).decode(self.__CODER)
        return {peer: loads(heartbeat_reply)}

    def encode_msg(self, message):
        if isinstance(message, dict):
            message = bytes(dumps(message), encoding=self.__CODER)
            return message
        elif isinstance(message, str):
            message = bytes(message, encoding=self.__CODER)
        else:
            raise TypeError('Unknown message type')
        return message

    def decode_msg(self, message):
        try:
            message = loads(message)
        except JSONDecodeError:
            pass
        return message

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1])
    peers = (sys.argv[2]).split(',')
    t = Transport(port, peers)
    t1 = Thread(target=t.serve)
    t2 = Thread(target=t.client, args=(peers,))
    t3 = Thread(target=t.init_timeout)
    t1.start()
    t2.start()
    t3.start()