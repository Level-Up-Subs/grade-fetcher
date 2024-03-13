#!/bin/bash

export PATH=/usr/local/bin:/usr/bin:/bin



source env/bin/activate && /usr/local/bin/python3 main.py && deactivate #>> Logs/output_$(date +\%Y\%m\%d_\%H\%M\%S).txt 2>&1

status="$(git status --porcelain --branch)"

source token.sh

if [ "$status" != "## main..origin/main" ]; then
    git add Submissions/*.txt
    git commit -m "Adding submissions to repo"
    git push https://github-actions[bot]:$GITHUB_TOKEN@github.com/Level-Up-Subs/grade-fetcher.git
fi
