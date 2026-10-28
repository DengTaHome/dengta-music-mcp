# dengta-music-mcp

Stable Docker deployment for [Anko3o/Music-Mcp-Netease](https://github.com/Anko3o/Music-Mcp-Netease),
a derivative of [eryu / 耳屿](https://github.com/sebastianevan200-stack/eryu) © Evelyn & River.

**License:** CC BY-NC-SA 4.0 — non-commercial use only; retain attribution and share-alike.
See `LICENSE` for the full upstream license.

## Endpoints

- `/` — player UI (pass `?token=<MUSIC_WEB_TOKEN>` once, then the browser keeps an HttpOnly cookie)
- `/mcp` — MCP endpoint (requires `Authorization: Bearer <MCP_TOKEN>`)
- `/admin/cookie` — internal cookie export (requires `X-Admin-Secret`)
- `/login-qr.png?token=...` — optional pre-rendered QR image (server-side polling is separate)
- `/health` — health check

## Environment

`MUSIC_WEB_TOKEN`, `MCP_TOKEN`, `ADMIN_SECRET`, `MUSIC_GATEWAY_TOKEN`,
optional `NETEASE_COOKIE`, `MUSIC_CARD_BASE`, `MUSIC_PUBLIC_URL`.

## NetEase login (upstream-documented method)

The canonical method is the upstream README's **MUSIC_U cookie**, not the raw QR API:

1. Log in at <https://music.163.com> in a desktop browser.
2. DevTools → Application → Cookies → `https://music.163.com` → copy `MUSIC_U`.
3. Put it in the mounted volume as `MUSIC_U=<value>` in `server/data/.netease_cred`
   (or set `NETEASE_COOKIE`).
4. Restart the container and verify `/music/netease/status` reports `logged_in: true`.

The QR endpoint (`/music/netease/qr/new` + `/qr/check`) exists upstream, but NetEase
may return risk-control code `8821` for datacenter IPs / non-browser clients. When that
happens, use the cookie method above — same as the upstream tutorial.

## Docker

```bash
docker build -t dengta-music-mcp .
docker run -d --name dengta-music-mcp --restart unless-stopped \
  -p 127.0.0.1:10080:10000 \
  -v /path/to/music-data:/app/server/data \
  -e MUSIC_WEB_TOKEN=... -e MCP_TOKEN=... -e ADMIN_SECRET=... \
  -e MUSIC_GATEWAY_TOKEN=music-gateway \
  -e MUSIC_CARD_BASE=https://music.example.com \
  -e MUSIC_PUBLIC_URL=https://music.example.com/ \
  dengta-music-mcp
```
