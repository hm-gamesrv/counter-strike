#!/usr/bin/env python3
"""Deploy a ReDeathmatch release into patch/dm/share.

The release archive contains a cstrike/ tree with plugins, configs, lang and
spawn data.  This script extracts it and merges everything into the target
directory.  An existing configs/plugins-redm.ini is kept, so local debug flags
are not overwritten on upgrade.

Usage:
    python3 PATCH.py [--version 1.0.0-b11] [--dest patch/dm/share]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REDM_VER = os.environ.get("REDM_VER", "1.0.0-b11")
KEEP = "addons/amxmodx/configs/plugins-redm.ini"


def log(message: str) -> None:
    print(f"==> {message}", flush=True)


def download(url: str, dest: Path, attempts: int = 3) -> None:
    log(f"downloading {url.rsplit('/', 1)[-1]}")
    request = urllib.request.Request(url, headers={"User-Agent": "redm-patch"})
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


def disable_debug(cfg: Path) -> None:
    """Comment out the per-plugin debug flag, as recommended by the guide."""
    if not cfg.exists():
        return
    text = cfg.read_text(encoding="utf-8", errors="surrogateescape")
    text = re.sub(r"(?m)^(\s*\S+\s+)(debug)\s*$", r"\1;debug", text)
    cfg.write_text(text, encoding="utf-8", errors="surrogateescape")


def merge(source: Path, dest: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"error: missing directory: {source}")
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        target = dest / relative
        if relative.as_posix() == KEEP and target.exists():
            log(f"keeping {relative}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="deploy a ReDeathmatch release")
    parser.add_argument(
        "--version",
        default=REDM_VER,
        help="release tag (default: %(default)s)",
    )
    parser.add_argument(
        "--dest",
        default=str(Path(__file__).resolve().parent / "share"),
        help="target directory (default: patch/dm/share)",
    )
    args = parser.parse_args()

    dest = Path(args.dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    url = (
        "https://github.com/ReDeathmatch/ReDeathmatch_AMXX/releases/download/"
        f"{args.version}/ReDeathmatch-{args.version}.zip"
    )

    with tempfile.TemporaryDirectory(prefix="redm-") as tmp:
        workdir = Path(tmp)
        archive = workdir / "redm.zip"
        download(url, archive)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(workdir / "release")
        merge(workdir / "release/cstrike", dest)

    disable_debug(dest / KEEP)
    log(f"done: {dest}")


if __name__ == "__main__":
    main()
