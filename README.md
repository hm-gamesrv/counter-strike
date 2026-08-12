# Counter-Strike Server

## 1. 简述

CS 1.6 / CSCZ 插件服务器

**特点：**

- 基于 legacy 版本的服务端
- 配合 ReHLDS + ReGameDLL_CS + Metamod-R & AMX Mod X 完成基架搭建
- 使用 ReDeathmatch 实现死斗模式
- 使用 YaPB 实现 Bot 功能
- 使用 Reunion 实现跨联机协议（47/48）以及非 Steam 客户端之间的互通联机功能

**可用版本：**

| 游戏模式       | 镜像 tag            |
| -------------- | ------------------- |
| CS1.6 死亡竞赛 | `1.6-dm-latest`     |
| CS1.6 对决     | `1.6-versus-latest` |
| CSCZ 死亡竞赛  | `cz-dm-latest`      |
| CSCZ 对决      | `cz-versus-latest`  |

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
