#!/bin/bash
PID=$(ps aux | grep 'filebrowser' | grep -v grep | awk {'print $2'} | xargs)
if [ "$PID" != "" ]
then
kill -9 $PID
sleep 2
echo "" > nohup.out
echo "Restarting FastAPI server"
else
echo "No such process. Starting new FastAPI server"
fi
filebrowser config import /home/ubuntu/Projects/tel-dl/file_server.json >/dev/null
nohup filebrowser -c /home/ubuntu/Projects/tel-dl/file_server.json &


