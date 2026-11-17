# =================
# Builder
# =================
FROM python:3.15-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget unzip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/depot-downloader \
    && wget -qO /opt/depot-downloader/DepotDownloader-linux-x64.zip \
    https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_3.4.0/DepotDownloader-linux-x64.zip \
    && unzip /opt/depot-downloader/DepotDownloader-linux-x64.zip -d /opt/depot-downloader

# 1: Base Goldsrc Shared Content 
# 11: Counter-Strike Base Content
# 81: Condition Zero Base Content
# 4: Linux dedicated server
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 1 -manifest 5928322771446233610 \
    && /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 11 -manifest 4720911300072406946 \
    && /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 81 -manifest 3601230779843470737 \
    && /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 4 -manifest 8690279432129063737 
# 1006: Steamworks SDK Redist (LINUX32)
RUN /opt/depot-downloader/DepotDownloader -os linux -validate -dir /download -app 90 -depot 1006 -manifest 6403079453713498174 

COPY install.py /usr/local/bin/install.py
RUN python3 /usr/local/bin/install.py --dest /download \
    && chown -R 1000:1000 /download

# ===================
# 基座镜像
# ===================
FROM debian:trixie-slim AS base

ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8

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
    && useradd --create-home --uid 1000 --gid 1000 --shell /usr/sbin/nologin gamesrv
RUN mkdir -p /app && chown 1000:1000 /app

COPY --from=builder --chown=1000:1000 ["/download/steamclient.so", "/home/gamesrv/.steam/sdk32/steamclient.so"]
COPY --from=builder --chown=1000:1000 ["/download", "/app"]
COPY ["./patch/base", "/app"]

EXPOSE 27015/udp 27015/tcp

WORKDIR /app
USER 1000:1000
CMD ["bash", "/app/start-server.sh", "+map", "de_dust2"]

# ===================
# 死亡竞赛文件组装
# ===================
FROM python:3.15-slim AS dm-builder

ARG REDM_VER
ENV REDM_VER=${REDM_VER}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY patch/dm/PATCH.py /usr/local/bin/PATCH.py
RUN python3 /usr/local/bin/PATCH.py --dest /out

# 本地覆盖：手写配置、出生点、导航图
COPY patch/dm/share/ /out/

# ===================
# 分支：死亡竞赛
# ===================
FROM base AS cs-dm

COPY --from=dm-builder --chown=1000:1000 ["/out/", "/app/cstrike/"]
COPY --from=dm-builder --chown=1000:1000 ["/out/", "/app/czero/"]
COPY --chown=1000:1000 ["./patch/dm/cstrike/", "/app/cstrike/"]

CMD ["bash", "/app/start-server.sh", "+map", "de_dust2"]
