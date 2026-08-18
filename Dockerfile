# =================
# 资源下载
# =================
FROM cm2network/steamcmd AS downloader

RUN /home/steam/steamcmd/steamcmd.sh \
    +@sSteamCmdForcePlatformType linux \
    +login anonymous \
    +app_set_config 90 mod cstrike \
    +app_update 90 -beta steam_legacy validate \
    +app_set_config 90 mod czero \
    +app_update 90 -beta steam_legacy validate \
    +quit

# ===================
# 基座镜像
# ===================
FROM debian:trixie-slim AS base

ENV TZ=Asia/Shanghai

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libc6:i386 \
        libstdc++6:i386 \
        libgcc-s1:i386 \
        libcurl4:i386 \
        zlib1g:i386 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 gamesrv \
    && useradd -u 1000 -g gamesrv -m -s /bin/bash gamesrv
RUN mkdir -p /app && chown 1000:1000 /app

COPY --from=downloader --chown=1000:1000 ["/home/steam/steamcmd/linux32/steamclient.so", "/home/gamesrv/.steam/sdk32/steamclient.so"]
COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life", "/app"]
COPY --chown=1000:1000 ["./patch/base/", "/app"]

RUN cp -r /app/-share/* /app/cstrike \
    && cp -r /app/-share/* /app/czero \
    && rm -rf /app/cstrike/maps/* \
    && rm -rf /app/czero/maps/* \
    && rm -rf /app/valve/maps/* \
    && rm -rf /app/-share \
    && chown -R 1000:1000 /app

EXPOSE 27015/udp 27015/tcp

WORKDIR /app
USER 1000:1000

# ===================
# 分支：死亡竞赛 (CS1.6)
# ===================
FROM base AS cs-dm

COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.bsp", "/app/cstrike/maps"]
COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.txt", "/app/cstrike/maps"]
COPY --chown=1000:1000 ["./patch/dm/", "/app"]

RUN cp -r /app/-share/* /app/cstrike \
    && rm -rf /app/-share

CMD ["bash", "/app/start-server-cs.sh", "+map", "de_dust2"]

# ===================
# 分支：对决 (CS1.6)
# ===================
FROM base AS cs-versus

COPY --chown=1000:1000 ["./patch/versus/", "/app"]

RUN cp -r /app/-share/* /app/cstrike \
    && rm -rf /app/-share

CMD ["bash", "/app/start-server-cs.sh", "+map", "aim_sk_ak_m4"]

# ===================
# 分支：死亡竞赛 (CSCZ)
# ===================
FROM base AS cscz-dm

COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.bsp", "/app/czero/maps"]
COPY --from=downloader --chown=1000:1000 ["/home/steam/Steam/steamapps/common/Half-Life/cstrike/maps/de_dust2.txt", "/app/czero/maps"]
COPY --chown=1000:1000 ["./patch/dm/", "/app"]

RUN cp -r /app/-share/* /app/czero \
    && rm -rf /app/-share

CMD ["bash", "/app/start-server-cscz.sh", "+map", "de_dust2"]

# ===================
# 分支：对决 (CSCZ)
# ===================
FROM base AS cscz-versus

COPY --chown=1000:1000 ["./patch/versus/", "/app"]

RUN cp -r /app/-share/* /app/czero \
    && rm -rf /app/-share

CMD ["bash", "/app/start-server-cscz.sh", "+map", "aim_sk_ak_m4"]
