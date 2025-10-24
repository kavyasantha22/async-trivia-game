#!/bin/bash
echo "a" >> a.txt
git checkout
git add .
git commit -m "automatic push"
git push upstream master