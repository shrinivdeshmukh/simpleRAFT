# simpleRAFT
Simple RAFT implementation using python sockets

# Usage

### Start the Nodes

```
cd simpleRAFT
python node.py <THIS NODE ADDRESS> <OTHER_NODE_ADDR_1>,<OTHER_NODE_ADDR_2>,<OTHER_NODE_ADDR_3>,<OTHER_NODE_ADDR_N>
```
Do this on all the other nodes

example:
For Node1:
```
cd simpleRAFT
python node.py 192.168.1.102:5000 192.168.1.102:5001,192.168.1.103:5002.192.168.1.104:5003  # NO SPACES AFTER EACH COMMA
```

For Node2:
```
cd simpleRAFT
python node.py 192.168.1.102:5000 192.168.1.101:5000,192.168.1.103:5002.192.168.1.104:5003  # NO SPACES AFTER EACH COMMA
```

Repeat this on all the nodes

### Put and Get Data

* Start the web server
```
python server.py <ANY_ADDRESS_FROM_THE_ABOVE_SERVERS>
```

Go to http://localhost:8000/docs

* Put data

![Alt text](static/put.png?raw=true "Put Data")

* Get data

![Alt text](static/get.png?raw=true "Put Data")

### Credits

The implementation is based on [Oaklight/Vesper](https://github.com/Oaklight/Vesper)