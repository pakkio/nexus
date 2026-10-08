#!/bin/bash
# (Re)start the Nexus API in tmux session "nexus" with the SQLite document store.
# Usage: ./start_nexus.sh            (run from anywhere)
cd "$(dirname "$0")" || exit 1
tmux kill-session -t nexus 2>/dev/null
sleep 1
tmux new-session -d -s nexus -c "$PWD" "set -a; source /root/pakkio/.env; set +a; \
NEXUS_USE_MOCKUP=true NEXUS_STORAGE=sqlite NEXUS_SQLITE_PATH=$PWD/database/nexus.db \
.venv/bin/python -c \"from app import app; from mcp_server import build_asgi_app; import uvicorn; uvicorn.run(build_asgi_app(app), host='0.0.0.0', port=5000)\""
for i in $(seq 1 30); do sleep 1; c=$(curl -s -m2 -o /dev/null -w '%{http_code}' localhost:5000/); [ "$c" = 200 ] && echo "nexus up (sqlite)" && exit 0; done
echo "nexus did not come up"; exit 1
