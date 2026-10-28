#!/bin/sh
set -eu

if [ -n "${MUSIC_WEB_TOKEN:-}" ]; then
  printf '%s' "$MUSIC_WEB_TOKEN" > /app/server/.secret
  chmod 600 /app/server/.secret 2>/dev/null || true
fi

if [ -n "${NETEASE_COOKIE:-}" ]; then
  printf 'MUSIC_U=%s\n' "$NETEASE_COOKIE" > /app/server/.netease_cred
  chmod 600 /app/server/.netease_cred 2>/dev/null || true
fi

cd /app
python server/music.py > /tmp/music.log 2>&1 &
MUSIC_PID=$!
python mcp/music_mcp.py > /tmp/music-mcp.log 2>&1 &
MCP_PID=$!

cleanup() { kill "$MUSIC_PID" "$MCP_PID" 2>/dev/null || true; }
trap cleanup INT TERM

# Wait until both local ports answer (max ~60s)
i=0
while [ "$i" -lt 60 ]; do
  if python -c "import socket,sys; s=socket.create_connection(('127.0.0.1',9090),1); s.close()" 2>/dev/null \
     && python -c "import socket,sys; s=socket.create_connection(('127.0.0.1',18012),1); s.close()" 2>/dev/null; then
    break
  fi
  i=$((i+1)); sleep 1
done
echo "starting proxy on ${PORT:-10000}"
exec python proxy.py