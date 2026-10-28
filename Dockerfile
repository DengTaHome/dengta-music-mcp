FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    MUSIC_BASE=http://127.0.0.1:9090 \
    MUSIC_GATEWAY_TOKEN=music-gateway

WORKDIR /app
COPY . /app

RUN chmod +x /app/entrypoint.sh \
 && mkdir -p /app/server/data

EXPOSE 10000
ENTRYPOINT ["/app/entrypoint.sh"]