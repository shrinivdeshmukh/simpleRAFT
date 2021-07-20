import socket
from threading import Thread, Lock
from json import dumps, loads, JSONDecodeError
import time
from log import Logging
import config as cfg


class Transport:

    def __init__(self, my_ip: str, timeout: int):
        self.host, self.port = my_ip.split(':')
        self.port = int(self.port)
        self.addr = my_ip
        self.ping_logger = Logging('INFO', 'ping.log').get_logger()
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.host, self.port))
        self.server.listen()
        self.peers = list()
        self.lock = Lock()
        Thread(target=self.ping, args=(timeout,)).start()

    def serve(self, election):
        self.election = election
        while True:
            client, address = self.server.accept()
            msg = client.recv(1024).decode('utf-8')
            msg = self.decode_json(msg)
            if isinstance(msg, dict):
                msg_type = msg['type']
                if msg_type == 'add_peer':
                    all_peers = self.peers.copy()
                    msg.update({'sender': self.addr})
                    self.add_peer(msg)
                    client.send(self.encode_json(
                        {'type': 'add_peer', 'payload': all_peers}))
                elif msg_type == 'heartbeat':
                    term, commit_id = self.election.heartbeat_handler(
                        message=msg)
                    client.send(self.encode_json(
                        {'type': 'heartbeat', 'term': term, 'commit_id': commit_id}))
                elif msg_type == 'vote_request':
                    choice, term = self.election.decide_vote(
                        msg['term'], msg['commit_id'], msg['staged'])
                    client.send(self.encode_json(
                        {'type': 'vote_request', 'term': term, 'choice': choice}))
                elif msg_type == 'ping':
                    msg.update({'is_alive': True, 'addr': self.addr})
                    client.send(self.encode_json(msg))
                elif msg_type == 'put':
                    if self.election.status == cfg.LEADER:
                        put_response = {'type': 'put'}
                        reply = self.election.handle_put(msg)
                        put_response.update({'success': reply})
                        client.send(self.encode_json(put_response))
                    # elif self.election.status == cfg.CANDIDATE:
                    #     reply = self.encode_json(
                    #         {'type': 'put', 'success': False, 'message': 'Cluster unavailable, please try again in sometime'})
                    else:
                        reply = self.redirect_to_leader(self.encode_json(msg))
                        client.send(bytes(reply, encoding='utf-8'))
                elif msg_type == 'get':
                    if self.election.status == cfg.LEADER:
                        get_response = {'type': 'get'}
                        reply = self.election.handle_get(msg)
                        if not reply:
                            reply = None
                        get_response.update({'data': reply})
                        client.send(self.encode_json(get_response))
                    else:
                        reply = self.redirect_to_leader(self.encode_json(msg))
                        client.send(bytes(reply, encoding='utf-8'))

                elif msg_type == 'data':
                    term, commit_id = self.election.heartbeat_handler(msg)
                    client.send(self.encode_json(
                        {'type': 'data', 'term': term, 'commit_id': commit_id}))
            else:
                send_msg = 'hey there; from {}'.format(self.addr)
                client.send(bytes(self.addr, encoding='utf-8'))
        client.close()

    def redirect_to_leader(self, message):
        leader_host, leader_port = (self.election.leader).split(':')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((leader_host, int(leader_port)))
        s.send(message)
        leader_reply = s.recv(1024).decode('utf-8')
        return leader_reply

    def proxy_client(self, addr: str, message=None):
        if not message:
            message = {'type': 'echo', 'payload': 'whatsup?'}
        client = self.reconnect(addr)
        client.send(self.encode_json(message))
        msg = client.recv(1024).decode('utf-8')
        client.close()
        return

    def req_add_peer(self, addr: str):
        client = self.reconnect(addr)
        if not client:
            self.ping_logger.info(f'Could not connect to peer {addr}')
            return
        message = self.encode_json({'type': 'add_peer', 'payload': self.addr})
        client.send(message)
        msg = client.recv(1024).decode('utf-8')
        reply = self.decode_json(msg)
        all_peers = reply['payload']
        with self.lock:
            self.peers.append(addr)
        if all_peers:
            with self.lock:
                for peer in all_peers:
                    self.peers.append(peer)
        self.peers = list(set(self.peers))

    def add_peer(self, message, leader=False):
        try:
            reciever_address = message['sender']
            new_peer = message['payload']
            if new_peer not in self.peers:
                with self.lock:
                    self.peers.append(new_peer)
            if self.election.status == cfg.LEADER:
                self.election.start_heartbeat()
        except Exception as e:
            raise e

    def reconnect(self, addr: str):
        i = 0
        while i < 20:
            try:
                host, port = addr.split(':')
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client.connect((host, int(port)))
                return client
            except ConnectionRefusedError:
                client.close()
                time.sleep(0.02)
                del client
            except TimeoutError as e:
                self.ping_logger.info(f'Timeout error connecting to peer {addr}')
                self.ping_logger.info(f'Removing peer {addr} from list of peers')
                with self.lock:
                    self.peers.remove(addr)
            except Exception as e:
                raise e
            finally:
                i += 1
        else:
            return False

    def ping(self, timeout: int):
        while True:
            if self.peers:
                self.ping_logger.debug(f'peers >>> {self.peers}')
                for peer in self.peers:
                    Thread(target=self.echo, args=(peer,)).start()
            else:
                self.ping_logger.debug('ping  >>> no peers to ping')
            time.sleep(timeout)

    def echo(self, peer):
        client = self.reconnect(peer)
        if not client:
            return
        echo_msg = self.encode_json({'type': 'ping'})
        client.send(echo_msg)
        echo_reply = self.decode_json(client.recv(1024).decode('utf-8'))
        client.close()
        if echo_reply:
            self.ping_logger.debug('ping  >>> {}'.format(echo_reply))
            if echo_reply['is_alive']:
                return True
        return False

    def heartbeat(self, peer: str, message: dict = None):
        client = self.reconnect(peer)
        message.update({'type': 'heartbeat'})
        heartbeat_message = self.encode_json(message)
        client.send(heartbeat_message)
        heartbeat_reply = self.decode_json(client.recv(1024).decode('utf-8'))
        client.close()
        return heartbeat_reply

    def vote_request(self, peer: str, message: dict = None):
        client = self.reconnect(peer)
        if not client:
            return
        message.update({'type': 'vote_request'})
        vote_request_message = self.encode_json(message)
        client.send(vote_request_message)
        vote_reply = self.decode_json(client.recv(1024).decode('utf-8'))
        client.close()
        return vote_reply

    def send_data(self, peer=None, message: dict = None):
        client = self.reconnect(peer)
        message.update({'type': 'data'})
        data_message = self.encode_json(message)
        client.send(data_message)
        data_reply = self.decode_json(client.recv(1024).decode('utf-8'))
        client.close()
        return data_reply

    def encode_json(self, msg):
        if isinstance(msg, dict):
            return bytes(dumps(msg), encoding='utf-8')
        return msg

    def decode_json(self, msg):
        if isinstance(msg, str):
            try:
                return loads(msg)
            except JSONDecodeError as e:
                raise TypeError('JSON format incorrect {}'.format(msg)) from e
            except Exception as e:
                raise e
        return msg
