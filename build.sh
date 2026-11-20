#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 configure.py
exec ninja -f .build/build.ninja "$@"
