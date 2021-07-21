# from raft.transport import Transport, Thread

# if __name__ == '__main__':
#     import sys
#     my_ip = sys.argv[1]
#     peers = list()
#     try:
#         peers = (sys.argv[2]).split(',')
#     except Exception:
#         pass
#     t = Transport(my_ip)
#     t1 = Thread(target=t.serve)
#     t1.start()
#     if peers:
#         for peer in peers:
#             Thread(target=t.req_add_peer, args=(peer,)).start() 

from node import Node
from argparse import ArgumentParser

if __name__ == '__main__':
    import sys
    parser = ArgumentParser()
    parser.add_argument('-t', '--type', help='Type of datastore', choices=('memory', 'database'), default='memory')
    parser.add_argument('-d', '--database', help='Name of the database', default='default')
    parser.add_argument('--dir', help='Location to store the database on the disk', default='data')
    parser.add_argument('--addr', help='Address of this node, the node shall listen on this address', default='0.0.0.0:5000')
    parser.add_argument('--peers', help='Address of the other nodes in the cluster', default=None)
    parser.add_argument('--timeout', help='Ping the peers after every unit time specified by this argument', default=1)
    args = parser.parse_args()
    my_ip = args.addr
    peers = list()
    if args.peers:
        peers = args.peers.split(',')
    store_type = args.type
    database = args.database
    data_dir = args.dir
    timeout = float(args.timeout)
    # try:
    #     peers = (sys.argv[2]).split(',')
    #     store_type = sys.argv[3]
    #     database = sys.argv[4]
    # except Exception:
    #     pass
    n = Node(my_ip=my_ip, peers=peers, timeout=timeout, store_type=store_type, data_dir=data_dir, database=database)
    
    n.run()

