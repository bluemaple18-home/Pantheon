#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8877 --reload
