#!/bin/bash
source  .venv/bin/activate
PID=$(ps aux | grep 'example.py' | grep -v grep | awk {'print $2'} | xargs)
if [ "$PID" != "" ]
then
kill -9 $PID
sleep 2
echo "" > nohup.out
echo "Restarting tel-dl server"
else
echo "No such process. Starting new tel-dl server"
fi
nohup python  -u  example.py  > bot_output.log  2> bot_error.log  &
