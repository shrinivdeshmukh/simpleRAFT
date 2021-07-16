cd raft
mkdir -p .data
python main.py 127.0.0.1:5000 127.0.0.1:5001,127.0.0.1:5002,127.0.0.1:5003 > .data/node1.log 2>&1 &
echo $! > .data/.pid.txt
python main.py 127.0.0.1:5001 127.0.0.1:5000,127.0.0.1:5002,127.0.0.1:5003 > .data/node2.log 2>&1 &
echo $! >> .data/.pid.txt
python main.py 127.0.0.1:5002 127.0.0.1:5000,127.0.0.1:5001,127.0.0.1:5003 > .data/node3.log 2>&1 &
echo $! >> .data/.pid.txt
python main.py 127.0.0.1:5003 127.0.0.1:5000,127.0.0.1:5001,127.0.0.1:5002 > .data/node4.log 2>&1 &
echo $! >> .data/.pid.txt
cd ..
python web.py 127.0.0.1:5000 > ./raft/.data/web.log 2>&1 &
echo $! >> ./raft/.data/.pid.txt