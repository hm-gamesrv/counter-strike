#!/bin/bash

./hlds_run -game czero \
    -insecure \
    -nomaster \
    -strictportbind \
    -ip 0.0.0.0 \
    -port 27015 \
    -norestart \
    +maxplayers 16 \
    "$@"