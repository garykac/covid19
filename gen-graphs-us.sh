#!/bin/bash

set -e

python plot.py --all

git commit -a -m "Generate graphs for $1 $2 $3"

git push
