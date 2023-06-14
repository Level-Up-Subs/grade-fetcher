#!/bin/bash

/usr/local/bin/python3 automatic.py >> Logs/output_$(date +\%Y\%m\%d_\%H\%M\%S).txt 2>&1



git config --global user.name "github-actions[bot]"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
git status --porcelain | grep -q . && git -C ~/Developer/projects/LevelUpSubs/grade-fetcher add Submissions/*.txt && git -C ~/Developer/projects/LevelUpSubs/grade-fetcher commit -m "Adding submissions to repo" && git -C ~/Developer/projects/LevelUpSubs/grade-fetcher push || [ $? -eq 1 ]

git push
