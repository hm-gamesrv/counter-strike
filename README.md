# Counter-Strike Server

## 1. 简述

CS 1.6 / CSCZ 插件服务器。

**特点：**

- 基于 steam_legacy (Pre-25th Anniversary Build) 版本的服务端
- ReHLDS + ReGameDLL_CS + Metamod-R + AMX Mod X 基架
- 使用 ReDeathmatch 实现死斗模式
- 使用 YaPB 实现 Bot 功能
- 使用 ReUnion 实现跨联机协议（47/48）以及非 Steam 客户端之间的互通联机

镜像内同时部署 `cstrike` 和 `czero`，通过 `-game` 选择：

```bash
# CS 1.6（默认）
bash /app/start-server.sh +map de_dust2

# Condition Zero
bash /app/start-server.sh -game czero +map de_dust2_cz
```

**可用版本：**

| 游戏模式     | target  | 镜像 tag |
| ------------ | ------- | -------- |
| CS1.6 死亡竞赛 | `cs-dm` | `1.6-dm` |
| CS1.6 基座     | `base`  | `latest` |

**组件版本：**

| 组件          | 版本             |
| ------------- | ---------------- |
| ReHLDS        | 3.15.0.896       |
| ReGameDLL_CS  | 5.30.0.814       |
| Metamod-R     | 1.3.0.149        |
| AMX Mod X     | 1.10.0-git5488   |
| ReAPI         | 5.29.0.358       |
| ReUnion       | 0.2.0.34         |
| YaPB          | 4.8.1427         |
| AmxxEasyHttp  | 1.5.0            |
| ReDeathmatch  | 1.0.0-b11        |

## 2. 资源占用信息

### 2.1. 端口

| 端口号 | 协议 | 说明         |
| ------ | ---- | ------------ |
| 27015  | UDP  | 游戏联机端口 |
| 27015  | TCP  | RCON 端口    |

## 3. 构建与运行

### 3.1. 构建并运行（Docker）

例：CS1.6 死亡竞赛：

```bash
docker build --target cs-dm -t counter-strike:1.6-dm-temp . && \
    docker run --rm -it \
        -p 27015:27015/udp \
        -p 27015:27015/tcp \
        counter-strike:1.6-dm-temp
```

### 3.2. 运行服务器（Podman）

例：CS1.6 死亡竞赛（1.6-dm-latest）：

```bash
IMAGE=ghcr.io/hm-gamesrv/counter-strike:1.6-dm-latest

if ! podman pull "$IMAGE"; then
    exit 1
fi

podman run --rm -it \
    --name counter-strike-1.6-dm \
    --userns keep-id \
    --network pasta \
    -p 27015:27015/udp \
    -p 27015:27015/tcp \
    "$IMAGE"
```

## 4. 目录结构

| 路径           | 说明                                                         |
| -------------- | ------------------------------------------------------------ |
| `Dockerfile`   | builder 下载服务端并安装组件，`base` 运行                    |
| `install.py`   | 下载 ReHLDS / ReGameDLL / Metamod / AMXX / ReAPI / ReUnion / YaPB，部署到 `cstrike` 和 `czero` |
| `patch/base`   | 启动脚本、`mapcycle.txt`                                      |
| `patch/dm`     | ReDeathmatch 插件、死斗配置、地图                                |
