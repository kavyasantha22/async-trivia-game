#!/bin/bash

# Continuously run push.sh with an optional delay (default 60s) between runs.
interval="${1:-60}"

while true; do
  ./push.sh
  sleep "$interval"
done
