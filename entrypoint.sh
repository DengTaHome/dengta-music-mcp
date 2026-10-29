#!/bin/sh
set -eu

: "${MUSIC_WEB_TOKEN:?MUSIC_WEB_TOKEN is required}"
: "${MCP_TOKEN:?MCP_TOKEN is required}"
: "${ADMIN_SECRET:?ADMIN_SECRET is required}"
: "${MUSIC_GATEWAY_TOKEN:?MUSIC_GATEWAY_TOKEN is required}"

umask 077
mkdir -p /app/server/data

# Persist the player secret and NetEase cookie inside the mounted data volume.
if [ -n "${MUSIC_WEB_TOKEN:-}" ]; then
  printf '%s' "$MUSIC_WEB_TOKEN" > /app/server/data/.secret
  chmod 600 /app/server/data/.secret 2>/dev/null || true
fi
ln -sfn /app/server/data/.secret /app/server/.secret

if [ -n "${NETEASE_COOKIE:-}" ]; then
  printf 'MUSIC_U=%s\n' "$NETEASE_COOKIE" > /app/server/data/.netease_cred
  chmod 600 /app/server/data/.netease_cred 2>/dev/null || true
fi
ln -sfn /app/server/data/.netease_cred /app/server/.netease_cred

cd /app
python server/music.py > /app/server/data/music.log 2>&1 &
MUSIC_PID=$!
python mcp/music_mcp.py > /app/server/data/music-mcp.log 2>&1 &
MCP_PID=$!

cleanup() { kill "$MUSIC_PID" "$MCP_PID" 2>/dev/null || true; }
trap cleanup INT TERM

ready=0
i=0
while [ "$i" -lt 60 ]; do
  if python -c "import socket; s=socket.create_connection(('127.0.0.1',9090),1); s.close()" 2>/dev/null \
     && python -c "import socket; s=socket.create_connection(('127.0.0.1',18012),1); s.close()" 2>/dev/null; then
    ready=1
    break
  fi
  i=$((i+1)); sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "upstreams did not become ready within 60s" >&2
  exit 1
fi
echo "starting proxy on ${PORT:-10000}"
python proxy.py > /app/server/data/proxy.log 2>&1 &
PROXY_PID=$!

# Any child dying must terminate the container so Docker restarts it; a bare
# health endpoint only proves the proxy process is alive.
while kill -0 "$MUSIC_PID" 2>/dev/null && kill -0 "$MCP_PID" 2>/dev/null && kill -0 "$PROXY_PID" 2>/dev/null; do
  sleep 5
done
echo "child exited (music=$MUSIC_PID mcp=$MCP_PID proxy=$PROXY_PID); restarting"
kill "$MUSIC_PID" "$MCP_PID" "$PROXY_PID" 2>/dev/null || true
exit 1