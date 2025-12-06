#!/usr/bin/env bash
set -euo pipefail

# Quick local spin-up: scheduler + one local node.
# Usage: MODEL="Qwen/Qwen3-8B-Instruct" ./scripts/run_and_join.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARALLAX="$ROOT_DIR/venv/bin/parallax"

MODEL="${MODEL:-Qwen/Qwen3-8B-Instruct}"
SCHED_PORT="${SCHED_PORT:-3001}"
SLEEP_BEFORE_JOIN="${SLEEP_BEFORE_JOIN:-5}"

if [ ! -x "$PARALLAX" ]; then
  echo "parallax not found at $PARALLAX (did you create venv?)" >&2
  exit 1
fi

cleanup() {
  echo "Stopping processes..."
  pkill -P $$ || true
}
trap cleanup EXIT INT TERM

echo "Starting scheduler with model: $MODEL (port: $SCHED_PORT)"
"$PARALLAX" run -u -m "$MODEL" --port "$SCHED_PORT" &
SCHED_PID=$!

echo "Waiting $SLEEP_BEFORE_JOIN seconds before joining..."
sleep "$SLEEP_BEFORE_JOIN"

echo "Starting local node join..."
"$PARALLAX" join -u &
JOIN_PID=$!

wait "$SCHED_PID"
