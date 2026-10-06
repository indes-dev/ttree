#!/usr/bin/env bash
# Run a command under OS-level limits: wall time, CPU seconds, address space, processes.
# Usage: run_bounded.sh WALL_SECONDS CPU_SECONDS MEMORY_MIB COMMAND...
set -uo pipefail
export LC_ALL=C
wall=$1 cpu=$2 mem=$3; shift 3
# RLIMIT_NPROC counts every process of this user, so allow current usage + 256.
nproc=$(( $(ps -L -U "$(id -u)" --no-headers | wc -l) + 256 ))
start=$EPOCHREALTIME
timeout --kill-after=5 "$wall" prlimit --cpu="$cpu" --as=$((mem * 1024 * 1024)) --nproc="$nproc" -- "$@"
status=$?
awk -v s="$start" -v e="$EPOCHREALTIME" -v st="$status" -v w="$wall" -v c="$cpu" -v m="$mem" \
  'BEGIN { printf "bounded: status=%s wall=%.2fs limits=(wall %ss, cpu %ss, as %s MiB)\n", st, e - s, w, c, m }' >&2
exit "$status"
