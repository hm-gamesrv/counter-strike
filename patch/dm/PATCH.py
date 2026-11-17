#!/usr/bin/env python3
"""Assemble the ReDeathmatch cstrike tree for the docker build.

Downloads a ReDeathmatch release, extracts it, and copies it into the target
directory.  The bundled scripting sources are skipped: they are not needed at
runtime.  Local overrides are copied on top by the Dockerfile afterwards.

Usage:
    python3 PATCH.py --dest /out [--version 1.0.0-b11]
"""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

REDM_VER = os.environ.get("REDM_VER") or "1.0.0-b11"
SKIP = "addons/amxmodx/scripting"


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


def merge(source: Path, dest: Path) -> None:
    if not source.is_dir():
        raise SystemExit(f"error: missing directory: {source}")
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        if relative.as_posix().startswith(SKIP):
            continue
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def main() -> None:
    parser = argparse.ArgumentParser(description="assemble a ReDeathmatch cstrike tree")
    parser.add_argument(
        "--version",
        default=REDM_VER,
        help="release tag (default: %(default)s)",
    )
    parser.add_argument("--dest", required=True, help="target directory")
    args = parser.parse_args()

    version = args.version or REDM_VER
    dest = Path(args.dest).resolve()
    url = (
        "https://github.com/ReDeathmatch/ReDeathmatch_AMXX/releases/download/"
        f"{version}/ReDeathmatch-{version}.zip"
    )

    with tempfile.TemporaryDirectory(prefix="redm-") as tmp:
        workdir = Path(tmp)
        archive = workdir / "redm.zip"
        download(url, archive)
        root = workdir / "release"
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(root)
        merge(root / "cstrike", dest)

    log(f"done: {dest}")


if __name__ == "__main__":
    main()
