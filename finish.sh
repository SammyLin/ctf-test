#!/bin/bash
# usage: ./finish.sh <tool> <task>
set -eu
K=$(cd "$(dirname "$0")" && pwd); TOOL=$1; TASK=$2
RUN=${EVAL_RUNS:-$HOME/eval-runs}/$TOOL/$TASK; R=$K/results/$TOOL/$TASK
echo $(( $(date +%s) - $(cat "$R/start") )) > "$R/seconds"
git -C "$RUN" add -A
git -C "$RUN" diff --cached HEAD --binary --output="$R/changes.patch"
for f in findings.json answers.md; do [ -f "$RUN/$f" ] && cp "$RUN/$f" "$R/"; done
echo "Saved to $R ($(cat "$R/seconds") s, $(git -C "$RUN" diff --cached HEAD --name-only | wc -l | tr -d ' ') files changed)."
read -r -p "Notes (errors, got stuck, could not read the image, needed a retry...). Enter to skip: " N || N=""
[ -n "$N" ] && echo "$N" > "$R/notes.txt"
exit 0
