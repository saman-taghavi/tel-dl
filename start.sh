#!/bin/bash
source  /home/ubuntu/Projects/tel-dl/.venv/bin/activate
PID=$(ps aux | grep 'example.py' | grep -v grep | awk {'print $2'} | xargs)
if [ "$PID" != "" ]
then
kill -9 $PID
sleep 2
echo "" > nohup.out
echo "Restarting FastAPI server"
else
echo "No such process. Starting new FastAPI server"
fi
nohup python /home/ubuntu/Projects/tel-dl/example.py  > bot_output.log &
