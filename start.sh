#!/bin/bash
# usage: ./start.sh <tool> <task> [short|detailed]     cli: any name you choose, e.g. cli-a   task: audit b1 b2 v1 qa
set -eu
K=$(cd "$(dirname "$0")" && pwd); TOOL=$1; TASK=$2; STYLE=${3:-detailed}
RUN=${EVAL_RUNS:-$HOME/eval-runs}/$TOOL/$TASK; R=$K/results/$TOOL/$TASK
[ -e "$RUN" ] && { echo "$RUN already exists. Delete it to rerun."; exit 1; }
mkdir -p "$RUN" "$R"; unzip -q "$K/tasks/$TASK.zip" -d "$RUN"
git -C "$RUN" init -q; git -C "$RUN" config core.autocrlf false; git -C "$RUN" add -A >/dev/null
git -C "$RUN" -c user.email=eval@x -c user.name=eval commit -qm snapshot
date +%s > "$R/start"; echo "$STYLE" > "$R/style"
command -v pbcopy >/dev/null && pbcopy < "$K/prompts/$TASK.$STYLE.txt"
echo "Timer started. Prompt is on the clipboard (also in prompts/$TASK.$STYLE.txt)."
echo "1) Open this folder in $TOOL:  $RUN"
echo "2) New session, paste the prompt, let it work. Do not help it. 30 minute limit."
echo "3) When it stops:  ./finish.sh $TOOL $TASK"
