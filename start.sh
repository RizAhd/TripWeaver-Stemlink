#!/usr/bin/env bash
set -u

python -m mcp_servers.hotel_server &
python -m mcp_servers.flight_server &
python -m mcp_servers.weather_server &

wait_for_port() {
    local port="$1"
    for _ in $(seq 1 30); do
        if python -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1', $port)) == 0 else 1)"; then
            echo "MCP server on port $port is ready"
            return 0
        fi
        sleep 1
    done
    echo "MCP server on port $port did not start, continuing without it"
    return 1
}

wait_for_port 8001 || true
wait_for_port 8002 || true
wait_for_port 8003 || true

exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-7860}"
