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

if __name__ == '__main__':
    import sys
    my_ip = sys.argv[1]
    peers = list()
    try:
        peers = (sys.argv[2]).split(',')
    except Exception:
        pass
    n = Node(my_ip=my_ip, peers=peers)
    
    n.run()

