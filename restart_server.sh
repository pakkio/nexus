#!/bin/bash

# Kill any process using port 5000
echo "Checking for processes on port 5000..."
PID=$(lsof -ti:5000)
if [ -n "$PID" ]; then
    echo "Killing process $PID on port 5000..."
    kill -9 $PID
    sleep 1
else
    echo "No process found on port 5000"
fi

# Start the server with nohup
echo "Starting server with virtualenv python..."
export PYTHONPATH=.
nohup poetry run python app.py > app_server.log 2>&1 &

echo "Server started! PID: $!"
echo "Logs: tail -f app_server.log"
