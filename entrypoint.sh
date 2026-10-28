#!/bin/sh
set -eu

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
touch /app/server/data/.netease_cred
ln -sfn /app/server/data/.netease_cred /app/server/.netease_cred

cd /app
python server/music.py > /tmp/music.log 2>&1 &
MUSIC_PID=$!
python mcp/music_mcp.py > /tmp/music-mcp.log 2>&1 &
MCP_PID=$!

cleanup() { kill "$MUSIC_PID" "$MCP_PID" 2>/dev/null || true; }
trap cleanup INT TERM

i=0
while [ "$i" -lt 60 ]; do
  if python -c "import socket; s=socket.create_connection(('127.0.0.1',9090),1); s.close()" 2>/dev/null \
     && python -c "import socket; s=socket.create_connection(('127.0.0.1',18012),1); s.close()" 2>/dev/null; then
    break
  fi
  i=$((i+1)); sleep 1
done
echo "starting proxy on ${PORT:-10000}"
exec python proxy.py