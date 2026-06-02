#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
exec python3 pika_fastfetch_gui.py "$@"
