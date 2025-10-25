#!/bin/bash

# Run push.sh repeatedly, interrupting each run shortly after it starts to mimic
# a manual Ctrl-C burst. Usage: ./push_burst.sh [count] [delay]

count=${1:-100}
delay=${2:-0.15}  # seconds to let push.sh start before interrupting

for ((i = 1; i <= count; i++)); do
  ./push.sh &
  pid=$!

  # Give the push a moment to upload objects before interrupting.
  sleep "$delay"

  # Send Ctrl-C (SIGINT) like a manual interrupt, then wait for cleanup.
  if kill -0 "$pid" 2>/dev/null; then
    kill -INT "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
  fi
done
