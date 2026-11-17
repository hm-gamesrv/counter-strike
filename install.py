#!/usr/bin/env python3
"""在已下载的 CS 1.6 / Condition Zero 服务端上部署组件。

服务端文件由 Dockerfile 的 DepotDownloader 步骤下载，本脚本负责：
    1. 下载 ReHLDS / ReGameDLL_CS / Metamod-R / AMX Mod X / ReAPI / ReUnion /
       YaPB / AmxxEasyHttp，解压合并成一份公共 share；
    2. 用 share 部署引擎（ReHLDS 根级文件）；
    3. 分别把 share 部署到 cstrike 和 czero，两者互不依赖；
    4. 清理多余地图与无用库。

用法：
    python3 install.py [--dest /app]

各组件版本可用同名环境变量覆盖（REHLDS_VER、AMXX_VER 等）。
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REHLDS_VER = os.environ.get("REHLDS_VER", "3.15.0.896")
REGAMEDLL_VER = os.environ.get("REGAMEDLL_VER", "5.30.0.814")
METAMOD_VER = os.environ.get("METAMOD_VER", "1.3.0.149")
AMXX_TAG = os.environ.get("AMXX_TAG", "1.10.0.5488")
AMXX_VER = os.environ.get("AMXX_VER", "1.10.0-git5488")
REAPI_VER = os.environ.get("REAPI_VER", "5.29.0.358")
REUNION_VER = os.environ.get("REUNION_VER", "0.2.0.34")
YAPB_VER = os.environ.get("YAPB_VER", "4.8.1427")
EASYHTTP_VER = os.environ.get("EASYHTTP_VER", "1.5.0")
REUNION_SALT = os.environ.get("REUNION_SALT", "cs16-dm-default-salt-change-me")


def log(message: str) -> None:
    print(f"==> {message}", flush=True)


def fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def download(url: str, dest: Path, attempts: int = 3) -> None:
    log(f"downloading {url.rsplit('/', 1)[-1]}")
    request = urllib.request.Request(url, headers={"User-Agent": "cs16-dm-installer"})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                with dest.open("wb") as file:
                    shutil.copyfileobj(response, file)
            return
        except OSError as error:
            if attempt == attempts:
                raise
            log(f"download failed ({error}), retry {attempt}/{attempts - 1}")
            time.sleep(2)


def extract_zip(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            path = Path(bundle.extract(info, dest))
            # zipfile 不恢复 Unix 权限，这里补回
            mode = info.external_attr >> 16
            if mode:
                os.chmod(path, mode)


def extract_tar(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(dest, filter="data")


def merge_tree(source: Path, dest: Path) -> None:
    if not source.is_dir():
        fail(f"missing directory: {source}")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, dirs_exist_ok=True)


def ensure_amxx_module(cfg: Path, name: str) -> None:
    """确保 AMX Mod X 的 modules.ini 启用了指定模块。"""
    text = cfg.read_text(encoding="utf-8", errors="surrogateescape")
    if re.search(rf"(?m)^\s*{re.escape(name)}\s*$", text):
        return
    text = re.sub(rf"(?m)^\s*;+\s*{re.escape(name)}\s*$", "", text)
    text = text.rstrip("\n") + "\n" + name + "\n"
    cfg.write_text(text, encoding="utf-8", errors="surrogateescape")


def set_metamod_gamedll(game: Path) -> None:
    """让 liblist.gmm / liblist.gam 指向 Metamod（两种布局都可能出现）。"""
    changed = 0
    for name in ("liblist.gmm", "liblist.gam"):
        path = game / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        updated, count = re.subn(
            r"(?m)^\s*gamedll_linux\s+.*$",
            'gamedll_linux "addons/metamod/metamod_i386.so"',
            text,
        )
        if count == 0:
            fail(f"no gamedll_linux line in {name}")
        path.write_text(updated, encoding="utf-8", errors="surrogateescape")
        changed += 1
    if changed == 0:
        fail("liblist.gam or liblist.gmm not found")


def configure_reunion(cfg: Path) -> None:
    """允许协议 47/48 的非 Steam 客户端，并满足 AuthVersion >= 3 对 salt 的要求。

    cid_NoSteam47/48 用 3（按客户端 IP 生成 STEAM_ 标识符）；值为 1 会被 ReUnion 判为非法。
    AuthVersion 为 4 时 SteamIdHashSalt 不能为空，否则 ReUnion 初始化失败。
    """
    text = cfg.read_text(encoding="utf-8", errors="surrogateescape")
    for key in (47, 48):
        pattern = re.compile(rf"(?m)^\s*#?\s*cid_NoSteam{key}\s*=.*$")
        line = f"cid_NoSteam{key} = 3"
        if pattern.search(text):
            text = pattern.sub(line, text, count=1)
        else:
            text = text.rstrip("\n") + "\n" + line + "\n"

    salt_pattern = re.compile(r"(?m)^\s*#?\s*SteamIdHashSalt\s*=.*$")
    salt_line = f"SteamIdHashSalt = {REUNION_SALT}"
    if salt_pattern.search(text):
        text = salt_pattern.sub(salt_line, text, count=1)
    else:
        text = text.rstrip("\n") + "\n" + salt_line + "\n"

    cfg.write_text(text, encoding="utf-8", errors="surrogateescape")


def download_rehlds(workdir: Path) -> Path:
    log(f"preparing ReHLDS {REHLDS_VER}")
    archive = workdir / "rehlds.zip"
    download(
        "https://github.com/rehlds/ReHLDS/releases/download/"
        f"{REHLDS_VER}/rehlds-bin-{REHLDS_VER}.zip",
        archive,
    )
    root = workdir / "rehlds"
    extract_zip(archive, root)
    engine = root / "bin/linux32"
    if not engine.is_dir():
        fail(f"unexpected ReHLDS layout, missing {engine}")
    return engine


def download_regamedll(share: Path, workdir: Path) -> None:
    log(f"preparing ReGameDLL_CS {REGAMEDLL_VER}")
    archive = workdir / "regamedll.zip"
    download(
        "https://github.com/rehlds/ReGameDLL_CS/releases/download/"
        f"{REGAMEDLL_VER}/regamedll-bin-{REGAMEDLL_VER}.zip",
        archive,
    )
    root = workdir / "regamedll"
    extract_zip(archive, root)
    merge_tree(root / "bin/linux32/cstrike", share)


def download_metamod(share: Path, workdir: Path) -> None:
    log(f"preparing Metamod-R {METAMOD_VER}")
    archive = workdir / "metamod.zip"
    download(
        "https://github.com/rehlds/Metamod-R/releases/download/"
        f"{METAMOD_VER}/metamod-bin-{METAMOD_VER}.zip",
        archive,
    )
    root = workdir / "metamod"
    extract_zip(archive, root)
    merge_tree(root / "addons", share / "addons")


def download_amxmodx(share: Path, workdir: Path) -> None:
    log(f"preparing AMX Mod X {AMXX_VER}")
    base = workdir / "amxx-base.tar.gz"
    game = workdir / "amxx-cstrike.tar.gz"
    base_url = (
        "https://github.com/alliedmodders/amxmodx/releases/download/"
        f"{AMXX_TAG}/amxmodx-{AMXX_VER}-base-linux.tar.gz"
    )
    game_url = (
        "https://github.com/alliedmodders/amxmodx/releases/download/"
        f"{AMXX_TAG}/amxmodx-{AMXX_VER}-cstrike-linux.tar.gz"
    )
    download(base_url, base)
    download(game_url, game)

    root = workdir / "amxx"
    extract_tar(base, root)
    extract_tar(game, root)  # cstrike 包覆盖同名文件
    merge_tree(root / "addons", share / "addons")


def download_reapi(share: Path, workdir: Path) -> None:
    log(f"preparing ReAPI {REAPI_VER}")
    archive = workdir / "reapi.zip"
    download(
        "https://github.com/rehlds/ReAPI/releases/download/"
        f"{REAPI_VER}/reapi-bin-{REAPI_VER}.zip",
        archive,
    )
    root = workdir / "reapi"
    extract_zip(archive, root)
    merge_tree(root / "addons", share / "addons")

    # ReAPI 是 AMX Mod X 模块，需要在 modules.ini 中启用才会被加载
    modules = share / "addons/amxmodx/configs/modules.ini"
    if not modules.exists():
        fail(f"missing AMX Mod X modules config: {modules}")
    ensure_amxx_module(modules, "reapi")


def download_reunion(share: Path, workdir: Path) -> None:
    log(f"preparing ReUnion {REUNION_VER}")
    archive = workdir / "reunion.zip"
    download(
        "https://github.com/rehlds/ReUnion/releases/download/"
        f"{REUNION_VER}/reunion-{REUNION_VER}.zip",
        archive,
    )
    root = workdir / "reunion"
    extract_zip(archive, root)
    merge_tree(root / "addons", share / "addons")

    cfg = share / "reunion.cfg"
    shutil.copy2(root / "reunion.cfg", cfg)
    configure_reunion(cfg)


def download_yapb(share: Path, workdir: Path) -> None:
    log(f"preparing YaPB {YAPB_VER}")
    archive = workdir / "yapb-linux.tar.xz"
    download(
        "https://github.com/yapb/yapb/releases/download/continuous/"
        f"yapb-{YAPB_VER}-linux.tar.xz",
        archive,
    )
    root = workdir / "yapb"
    extract_tar(archive, root)
    merge_tree(root / "addons", share / "addons")


def download_easyhttp(share: Path, workdir: Path) -> None:
    """AmxxEasyHttp 是 AMXX 的 HTTP 模块，ReDeathmatch 用它做版本检查。"""
    log(f"preparing AmxxEasyHttp {EASYHTTP_VER}")
    archive = workdir / "easyhttp.zip"
    download(
        "https://github.com/Next21Team/AmxxEasyHttp/releases/download/"
        f"{EASYHTTP_VER}/AmxxEasyHttp-{EASYHTTP_VER}-linux-i386.zip",
        archive,
    )
    root = workdir / "easyhttp"
    extract_zip(archive, root)
    merge_tree(root / "addons", share / "addons")

    modules = share / "addons/amxmodx/configs/modules.ini"
    if not modules.exists():
        fail(f"missing AMX Mod X modules config: {modules}")
    ensure_amxx_module(modules, "easy_http")


def write_metamod_plugins(share: Path) -> None:
    """按加载顺序写 Metamod 插件列表。"""
    plugins = share / "addons/metamod/plugins.ini"
    plugins.parent.mkdir(parents=True, exist_ok=True)
    plugins.write_text(
        "linux addons/reunion/reunion_mm_i386.so\n"
        "linux addons/yapb/bin/yapb.so\n"
        "linux addons/amxmodx/dlls/amxmodx_mm_i386.so\n",
        encoding="utf-8",
    )


def prepare_share(workdir: Path) -> tuple[Path, Path]:
    """下载并解压所有组件，返回 (share, engine)。

    share 可直接叠加到 cstrike 或 czero（等价于 patch/base_1/-share）：
        addons/      Metamod-R + AMX Mod X + ReAPI + ReUnion + YaPB + AmxxEasyHttp
        dlls/cs.so   ReGameDLL_CS
        delta.lst / game.cfg / game_init.cfg
        reunion.cfg  ReUnion 配置

    engine 是 ReHLDS 解压目录，由 install_engine 覆盖到服务端根级。
    """
    share = workdir / "share"
    share.mkdir(parents=True)
    engine = download_rehlds(workdir)
    download_regamedll(share, workdir)
    download_metamod(share, workdir)
    download_amxmodx(share, workdir)
    download_reapi(share, workdir)
    download_reunion(share, workdir)
    download_yapb(share, workdir)
    download_easyhttp(share, workdir)
    write_metamod_plugins(share)
    return share, engine


def install_engine(dest: Path, engine: Path) -> None:
    """用 ReHLDS 覆盖根级引擎文件。"""
    log("deploying ReHLDS engine")
    merge_tree(engine, dest)
    for name in ("hlds_linux", "hlds_run"):
        (dest / name).chmod(0o755)


def install_cstrike(dest: Path, share: Path) -> None:
    """把公共组件部署到 cstrike。"""
    log("deploying cstrike")
    game = dest / "cstrike"
    if not game.is_dir():
        fail(f"missing cstrike directory: {game}")
    merge_tree(share, game)
    set_metamod_gamedll(game)


def install_czero(dest: Path, share: Path) -> None:
    """把公共组件部署到 czero，不读取 cstrike 的部署结果。"""
    log("deploying czero")
    game = dest / "czero"
    if not game.is_dir():
        fail(f"missing czero directory: {game}")
    merge_tree(share, game)
    set_metamod_gamedll(game)


def prune(dest: Path) -> None:
    """cstrike 保留 de_dust2，czero 保留 de_dust2_cz，删除 64 位库与 DepotDownloader 缓存。"""
    log("pruning extra files")
    keep = {"cstrike": "de_dust2.", "czero": "de_dust2_cz."}
    for mod, prefix in keep.items():
        maps = dest / mod / "maps"
        if not maps.is_dir():
            continue
        for entry in maps.iterdir():
            if entry.name.startswith(prefix):
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    shutil.rmtree(dest / "valve/maps", ignore_errors=True)
    for name in (
        "libsteamwebrtc.so",
        "linux64/steamclient.so",
        "linux64/libsteamwebrtc.so",
    ):
        (dest / name).unlink(missing_ok=True)
    shutil.rmtree(dest / ".DepotDownloader", ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="deploy CS 1.6 / Condition Zero server")
    parser.add_argument(
        "--dest",
        default=os.environ.get("CS_DIR", "/app"),
        help="server directory (default: /app)",
    )
    args = parser.parse_args()

    dest = Path(args.dest).resolve()
    if not (dest / "hlds_linux").exists():
        fail(f"server files not found: {dest}/hlds_linux; run the Dockerfile DepotDownloader step first")

    with tempfile.TemporaryDirectory(prefix="cs-") as tmp:
        share, engine = prepare_share(Path(tmp))
        install_engine(dest, engine)
        install_cstrike(dest, share)
        install_czero(dest, share)
        prune(dest)

    log(f"done: {dest}")


if __name__ == "__main__":
    main()
