# =================
# Download
# =================
FROM debian:trixie-slim AS download

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/depot-downloader \
    && wget -qO /opt/depot-downloader/DepotDownloader-linux-x64.zip \
    https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_3.4.0/DepotDownloader-linux-x64.zip \
    && unzip /opt/depot-downloader/DepotDownloader-linux-x64.zip -d /opt/depot-downloader

# 1: Base Goldsrc Shared Content 
# 11: Counter-Strike Base Content
# 81: Condition Zero Base Content
# 90: Linux dedicated server
# 1006: Steamworks SDK Redist (LINUX32)
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 1 -manifest 5928322771446233610
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 11 -manifest 4720911300072406946
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 81 -manifest 3601230779843470737
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 4 -manifest 8690279432129063737
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 1006 -manifest 6403079453713498174 

# =================
# Prune
# =================
FROM download AS prune

COPY --from=download --chown=1000:1000 ["/download", "/app"]
COPY --chown=1000:1000 ["./patch/base/", "/app"]

RUN rm -rf /app/cstrike/maps/* \
    && rm -rf /app/czero/maps/* \
    && rm -rf /app/valve/maps/* \
    && rm -rf /app/libsteamwebrtc.so \
    && rm -rf /app/linux64/steamclient.so \
    && rm -rf /app/linux64/libsteamwebrtc.so \
    && cp -r /app/-share/* /app/cstrike \
    && cp -r /app/-share/* /app/czero \
    && rm -rf /app/-share \
    && chown -R 1000:1000 /app

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

COPY --from=prune --chown=1000:1000 ["/app/steamclient.so", "/home/gamesrv/.steam/sdk32/steamclient.so"]
COPY --from=prune --chown=1000:1000 ["/app", "/app"]

EXPOSE 27015/udp 27015/tcp

WORKDIR /app
USER 1000:1000

# ===================
# 分支：死亡竞赛 (CS1.6)
# ===================
FROM base AS cs-dm

COPY --from=download --chown=1000:1000 ["/download/cstrike/maps/de_dust2.bsp", "/app/cstrike/maps"]
COPY --from=download --chown=1000:1000 ["/download/cstrike/maps/de_dust2.txt", "/app/cstrike/maps"]
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

COPY --from=download --chown=1000:1000 ["/download/cstrike/maps/de_dust2.bsp", "/app/czero/maps"]
COPY --from=download --chown=1000:1000 ["/download/cstrike/maps/de_dust2.txt", "/app/czero/maps"]
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
