#!/bin/bash
set -euo pipefail

GAME="cstrike"
if [[ "${1:-}" == "-game" ]]; then
    GAME="${2:?-game requires a game directory}"
    shift 2
fi

cd /app && exec /app/hlds_run -game "$GAME" \
    -insecure \
    -nomaster \
    -strictportbind \
    -ip 0.0.0.0 \
    -port 27015 \
    -norestart \
    +maxplayers 16 \
    "$@"
