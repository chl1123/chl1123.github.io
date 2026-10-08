#!/usr/bin/env bash
# rbk-triage.sh - turn a fault time window into concrete RBK trace/log commands.
#
# This is a read-only planner: it prints the artifacts and ptcat/log commands that
# cover the reported window. It does not modify robot state.
#
# Usage:
#   rbk-triage.sh --at '2026-09-29 13:47:00' [--until '2026-09-29 13:57:00']
#                  [--symptom script|nav|loc|map|device|crash|latency]
#                  [--task-id ID] [--trace-dir DIR] [--log-dir DIR]
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: rbk-triage.sh --at 'YYYY-MM-DD HH:MM:SS' [options]

Options:
  --at TIME          Fault time (wall clock). Required. Local timezone is assumed.
  --until TIME       End of window (default: --at + 10 minutes).
  --symptom KIND     script | nav | loc | map | device | crash | latency (default: script).
  --task-id ID       Task ID to correlate (repeatable).
  --trace-dir DIR    Trace directory (default: /opt/.data/diagnosis/rbk/trace/event).
  --log-dir DIR      Log directory (default: /opt/.data/diagnosis/rbk/logs).
  -h, --help         Show this help.
EOF
}

at=""
until=""
symptom="script"
trace_dir="/opt/.data/diagnosis/rbk/trace/event"
log_dir="/opt/.data/diagnosis/rbk/logs"
task_ids=()

while (($#)); do
  case "$1" in
    --at) at=${2:?missing value for --at}; shift 2 ;;
    --until) until=${2:?missing value for --until}; shift 2 ;;
    --symptom) symptom=${2:?missing value for --symptom}; shift 2 ;;
    --task-id) task_ids+=("${2:?missing value for --task-id}"); shift 2 ;;
    --trace-dir) trace_dir=${2:?missing value for --trace-dir}; shift 2 ;;
    --log-dir) log_dir=${2:?missing value for --log-dir}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$at" ]]; then
  echo "--at is required. Ask the reporter for the exact fault time first." >&2
  usage >&2
  exit 2
fi

at_epoch=$(date -d "$at" +%s)
if [[ -z "$until" ]]; then
  until=$(date -d "@$((at_epoch + 600))" '+%Y-%m-%d %H:%M:%S')
fi
until_epoch=$(date -d "$until" +%s)
if ((until_epoch < at_epoch)); then
  echo "--until precedes --at" >&2
  exit 2
fi

# ptcat spelling: YYYYMMDD.HH:MM:SS
to_ptcat() { date -d "$1" '+%Y%m%d.%H:%M:%S'; }
b=$(to_ptcat "$at")
e=$(to_ptcat "$until")

case "$symptom" in
  script)  group='rbk\.script\.utils_rpc'; names='Rc RcError Rs RsError' ;;
  nav)     group='rbk\.nav\.MoveFactory';  names='' ;;
  loc)     group='rbk\.loc\.MCLoc';        names='locationEachFrame locByNDT eKFLocalizationFusion locationbyRef' ;;
  map)     group='rbk\.loc\.BlockMapLoader'; names='changeMap' ;;
  device)  group='rbk\.device\.DSPChassis';  names='motorInfo messageDI messageDO distanceInfo' ;;
  crash)   group=''; names='' ;;
  latency) group='rbk\.device\.DSPChassis';  names='messageDI' ;;
  *) echo "Unknown --symptom: $symptom" >&2; exit 2 ;;
esac

echo "== RBK triage plan =="
echo "window:  $at  ..  $until"
echo "ptcat:   -b '$b' -e '$e'"
echo "symptom: $symptom"
if ((${#task_ids[@]})); then
  echo "taskIds: ${task_ids[*]}"
fi
echo

echo "== Candidate trace segments (by start time) =="
selected_trace=""
if [[ -d "$trace_dir" ]]; then
  ls -1t "$trace_dir"/rbk+common_*.pft.zst 2>/dev/null | head -20 || true
else
  echo "(trace dir missing: $trace_dir)"
fi
echo

# Pick the segment whose start is the latest one <= the window start.
# Filenames look like rbk+common_YYYY-MM-DD_HH-MM-SS[.__temp__].pft.zst.
if [[ -d "$trace_dir" ]]; then
  best_epoch=-1
  while IFS= read -r seg; do
    base=${seg##*/}
    # rbk+common_YYYY-MM-DD_HH-MM-SS[.__temp__].pft.zst
    stamp=${base#rbk+common_}
    stamp=${stamp%%.pft.zst}
    stamp=${stamp%.__temp__}
    [[ "$stamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] || continue
    d=${stamp%%_*}; t=${stamp#*_}
    seg_epoch=$(date -d "$d ${t//-/:}" +%s 2>/dev/null) || continue
    # Prefer the newest segment that started at or before the fault window.
    if (( seg_epoch <= at_epoch )) && (( seg_epoch > best_epoch )); then
      best_epoch=$seg_epoch
      selected_trace=$seg
    fi
  done < <(ls -1 "$trace_dir"/rbk+common_*.pft.zst 2>/dev/null)
fi

if [[ -n "$selected_trace" ]]; then
  echo "== Selected trace segment for this window =="
  echo "$selected_trace"
  echo "# (started $(date -d "@$best_epoch" '+%Y-%m-%d %H:%M:%S'); segments roll about every 15 min,"
  echo "#  so if the window spans a roll, also query the next segment.)"
  echo
export TRACE="$selected_trace"
fi

# Candidate ide/script logs whose start time falls within [at - 20min, until].
echo "== Candidate logs covering the window =="
if [[ -d "$log_dir" ]]; then
  for sub in ide scripts; do
    [[ -d "$log_dir/$sub" ]] || continue
    found=0
    for f in $(ls -1t "$log_dir/$sub"/*.log 2>/dev/null); do
      base=${f##*/}
      stamp=${base%.log}
      stamp=${stamp##*_}
      [[ "$stamp" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] || continue
      d=${stamp%%_*}; t=${stamp#*_}
      f_epoch=$(date -d "$d ${t//-/:}" +%s 2>/dev/null) || continue
      if (( f_epoch <= until_epoch + 1200 )) && (( f_epoch >= at_epoch - 7200 )); then
        echo "$f"
        found=1
      fi
    done
    (( found )) || echo "($sub: no log started near the window; the active file may have an older name)"
  done
else
  echo "(log dir missing: $log_dir)"
fi
echo

if [[ "$symptom" == "crash" ]]; then
  echo "== Crash triage =="
  echo "# RBK-level crash: syslog first"
  echo "sudo journalctl -S '$at' -U '$until' --no-pager | rg -i 'rbk|segfault|oom|killed|core'"
  mon=$(LC_ALL=C date -d "$at" '+%b %e')
  echo "sudo awk '/^${mon}/{p=1} p' /var/log/syslog | rg -i 'rbk|segfault|oom|killed'"
  echo "# Script-process crash: PyIDE ide log"
  echo "rg -n 'broker::start|register_service|unregister_service|Traceback|exit' $log_dir/ide/<newest>.log"
  echo "# Coredumps"
  echo "ls -lt /opt/.data/diagnosis/rbk/coredump | head"
  exit 0
fi

echo "== Suggested ptcat queries =="
if [[ -n "$selected_trace" ]]; then
  echo "TRACE=$selected_trace"
else
  echo "TRACE=<no segment auto-selected; choose one from the list above>"
fi
for n in $names; do
  echo "ptcat -b '$b' -e '$e' -g '$group' -n '$n' \"\$TRACE\""
done
if [[ -z "$names" ]]; then
  echo "ptcat -b '$b' -e '$e' -g '$group' \"\$TRACE\""
fi
echo
echo "# Discover script-defined channels in the window before naming them:"
echo "ptcat -c stat -b '$b' -e '$e' \"\$TRACE\" | rg 'rbk\\.script\\.utils_rpc|messageDI|fork|actions'"
echo

if ((${#task_ids[@]})); then
  echo "== taskId correlation =="
  for t in "${task_ids[@]}"; do
    echo "rg -n \"taskId[\\\"']?\\s*[:=]\\s*$t|::get_task|::update_cmd|scriptReport\" $log_dir/ide/<newest>.log"
    echo "rg -n '$t|MoveFactory::scriptReport|update_cmd' $log_dir/scripts/<newest>.log"
  done
fi
