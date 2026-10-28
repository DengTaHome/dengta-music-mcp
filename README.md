# dengta-music-mcp

Stable Docker deployment for [Anko3o/Music-Mcp-Netease](https://github.com/Anko3o/Music-Mcp-Netease) (MIT).

- `/` — player UI (pass `?token=<MUSIC_WEB_TOKEN>` once)
- `/mcp` — MCP endpoint (requires `Authorization: Bearer <MCP_TOKEN>`)
- `/admin/cookie` — internal cookie export (requires `X-Admin-Secret`)
- `/health` — health check

Environment: `MUSIC_WEB_TOKEN`, `MCP_TOKEN`, `ADMIN_SECRET`, optional `NETEASE_COOKIE`
(persisted after QR login for restarts). Data is ephemeral on free Render; cookie is the
only credential expected to survive restarts.