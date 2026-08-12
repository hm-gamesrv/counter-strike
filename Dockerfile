# =================
# 资源下载
# =================
FROM cm2network/steamcmd AS downloader

RUN /home/steam/steamcmd/steamcmd.sh +quit
RUN /home/steam/steamcmd/steamcmd.sh \
    +@sSteamCmdForcePlatformType linux \
    +login anonymous \
    +app_set_config 90 mod cstrike \
    +app_update 90 -beta steam_legacy validate \
    +quit

# ===================
# 基座镜像
# ===================
FROM debian:trixie-slim AS base

EXPOSE 27015/udp 27015/tcp

ENV TZ=Asia/Shanghai

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        # 64-bit 依赖
        ca-certificates \
        # 32-bit 依赖
        libc6:i386 \
        libstdc++6:i386 \
        libgcc-s1:i386 \
        libcurl4:i386 \
        zlib1g:i386 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 gamesrv && \
    useradd -u 1000 -g gamesrv -m -s /bin/bash gamesrv
RUN mkdir -p /app && chown 1000:1000 /app
USER 1000:1000

COPY --from=downloader --chown=1000:1000 ["/home/steam/steamcmd/linux32/steamclient.so", "/home/gamesrv/.steam/sdk32/steamclient.so"]
COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life", "/app"]
RUN rm -rf /app/cstrike/maps/* \
    && rm -rf /app/valve/maps/*
COPY --chown=1000:1000 ["./patch/base/", "/app"]

WORKDIR /app

# ===================
# 分支：死亡竞赛
# ===================
FROM base AS dm

COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.bsp", "/app/cstrike/maps"]
COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.txt", "/app/cstrike/maps"]
COPY --chown=1000:1000 ["./patch/dm/", "/app"]

CMD ["bash", "/app/start-server.sh", "+map", "de_dust2"]

# ===================
# 分支：对决
# ===================
FROM base AS versus

COPY --chown=1000:1000 ["./patch/versus/", "/app"]

CMD ["bash", "/app/start-server.sh", "+map", "aim_sk_ak_m4"]