cat raft/.data/.pid.txt | while read line 
do
    kill -9 $line
   # do something with $line here
done