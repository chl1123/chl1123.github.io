#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: collect-rbk-evidence.sh --out DIR [options]

Options:
  --task-id ID         Filter evidence for an exact task ID (repeatable).
  --insight-url URL    insightd query URL (default: http://127.0.0.1:8019).
  --trace-dir DIR      Trace directory (default: /opt/.data/diagnosis/rbk/trace/event).
  --copy-trace         Copy the finalized trace into the output directory.
  -h, --help           Show this help.
EOF
}

out_dir=""
insight_url="http://127.0.0.1:8019"
trace_dir="/opt/.data/diagnosis/rbk/trace/event"
copy_trace=false
task_ids=()

while (($#)); do
  case "$1" in
    --out)
      out_dir=${2:?missing value for --out}
      shift 2
      ;;
    --task-id)
      task_ids+=("${2:?missing value for --task-id}")
      shift 2
      ;;
    --insight-url)
      insight_url=${2:?missing value for --insight-url}
      shift 2
      ;;
    --trace-dir)
      trace_dir=${2:?missing value for --trace-dir}
      shift 2
      ;;
    --copy-trace)
      copy_trace=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$out_dir" ]]; then
  echo "--out is required" >&2
  usage >&2
  exit 2
fi

for command_name in curl jq find sort sed cut cp zstd strings awk head; do
  command -v "$command_name" >/dev/null || {
    echo "Required command not found: $command_name" >&2
    exit 1
  }
done

mkdir -p "$out_dir"
sync_file="$out_dir/insight-sync.json"
live_report="$out_dir/insight-report.json"
task_ids_file="$out_dir/task-ids.json"
filtered_live="$out_dir/insight-events.filtered.json"
filtered_persisted="$out_dir/rbk-report.filtered.jsonl"
manifest_file="$out_dir/manifest.json"

curl -fsS --max-time 10 "$insight_url/sync" -o "$sync_file"
wait_sec=$(jq -r '.wait_sec // 5' "$sync_file")
if ! [[ "$wait_sec" =~ ^[0-9]+$ ]] || ((wait_sec > 60)); then
  echo "Invalid insightd wait_sec: $wait_sec" >&2
  exit 1
fi
sleep $((wait_sec + 1))

mapfile -t trace_candidates < <(
  find "$trace_dir" -maxdepth 1 -type f \
    -name 'rbk+common_*.pft.zst' ! -name '*.__temp__.*' \
    -printf '%T@ %p\n' |
  sort -nr |
  head -n 10 |
  cut -d' ' -f2-
)
if ((${#trace_candidates[@]} == 0)); then
  echo "No finalized common trace found in $trace_dir" >&2
  exit 1
fi

trace_contains_task_ids() {
  local candidate=$1
  local task_id=""

  for task_id in "${task_ids[@]}"; do
    if ! awk -v task_id="$task_id" '
      $0 == task_id ||
      index($0, "\"taskId\":\"" task_id "\"") ||
      index($0, "\"taskId\": \"" task_id "\"") ||
      index($0, "'\''taskId'\'': '\''" task_id "'\''") { found=1; exit }
      END { exit(found ? 0 : 1) }
    ' < <(zstd -dc -- "$candidate" | strings -n 4); then
      return 1
    fi
  done
}

trace_path=""
for candidate in "${trace_candidates[@]}"; do
  if trace_contains_task_ids "$candidate"; then
    trace_path=$candidate
    break
  fi
done
if [[ -z "$trace_path" ]]; then
  echo "No recent finalized common trace contains every requested task ID" >&2
  exit 1
fi

jq -n '$ARGS.positional' --args "${task_ids[@]}" > "$task_ids_file"
curl -fsS --max-time 10 "$insight_url/report" -o "$live_report"
jq --slurpfile ids "$task_ids_file" '
  def normalized_da:
    if type == "string" then (fromjson? // .) else . end;
  def task_matches($event; $id):
    [($event.da | normalized_da) | .. | scalars | tostring] | any(. == $id);
  if ($ids[0] | length) == 0 then {events:.list}
  else {events:[.list[] as $event |
    select(($ids[0] | map(. as $id | task_matches($event; $id)) | any)) |
    $event]}
  end
' "$live_report" > "$filtered_live"

report_path="$trace_dir/rbk+report.jsonl"
if [[ -f "$report_path" ]]; then
  cp "$report_path" "$out_dir/rbk+report.jsonl"
  jq -c --slurpfile ids "$task_ids_file" '
    def normalized_da:
      if type == "string" then (fromjson? // .) else . end;
    def task_matches($event; $id):
      [($event.da | normalized_da) | .. | scalars | tostring] | any(. == $id);
    if ($ids[0] | length) == 0 then .
    else . as $event |
      select(($ids[0] | map(. as $id | task_matches($event; $id)) | any))
    end
  ' "$report_path" > "$filtered_persisted"
fi

copied_trace=""
if [[ "$copy_trace" == true ]]; then
  copied_trace="$out_dir/$(basename "$trace_path")"
  cp "$trace_path" "$copied_trace"
fi

jq -n \
  --arg collected_at "$(date --iso-8601=seconds)" \
  --arg insight_url "$insight_url" \
  --arg trace_source "$trace_path" \
  --arg trace_copy "$copied_trace" \
  --arg report_source "$report_path" \
  --arg trace_selection "newest of up to 10 finalized traces containing every requested taskId" \
  --slurpfile task_ids "$task_ids_file" \
  --slurpfile sync "$sync_file" \
  '{collectedAt:$collected_at, insightUrl:$insight_url,
    taskIds:$task_ids[0], sync:$sync[0], traceSource:$trace_source,
    traceCopy:$trace_copy, traceSelection:$trace_selection,
    reportSource:$report_source}' > "$manifest_file"

echo "Evidence written to: $out_dir"
echo "Finalized trace: $trace_path"
