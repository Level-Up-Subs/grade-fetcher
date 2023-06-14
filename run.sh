#!/bin/bash

export PATH=/usr/local/bin:/usr/bin:/bin

/usr/local/bin/python3 automatic.py >> Logs/output_$(date +\%Y\%m\%d_\%H\%M\%S).txt 2>&1

git config --global user.name "github-actions[bot]"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"

status="$(git status --porcelain --branch)"

if [ "$status" != "## main..origin/main" ]; then
    git add Submissions/*.txt
    git commit -m "Adding submissions to repo"
    git push
fi
