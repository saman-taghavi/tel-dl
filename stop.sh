#!/bin/bash
PID=$(ps aux | grep 'test.py' | grep -v grep | awk {'print $2'} | xargs)
if [ "$PID" != "" ]
then
kill -9 $PID
sleep 2
echo "tel-dl off"
else
echo "No tel-dl"
fi

