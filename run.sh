#!/bin/bash

export PATH=/usr/local/bin:/usr/bin:/bin

/usr/local/bin/python3 automatic.py >> Logs/output_$(date +\%Y\%m\%d_\%H\%M\%S).txt 2>&1

/usr/bin/git config --global user.name "github-actions[bot]"
/usr/bin/git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
/usr/bin/git status --porcelain | grep -q . && /usr/bin/git add Submissions/*.txt && /usr/bin/git commit -m "Adding submissions to repo" && /usr/bin/git push  || [ $? -eq 1 ]
