#!/bin/bash

# Run push.sh 100 times in rapid succession.
for _ in {1..100}; do
  ./push.sh &
done
