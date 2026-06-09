#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DEFAULT_CONFIG="$SCRIPT_DIR/build_deb.yml"
DEFAULT_NODE="master"
DEFAULT_ARCH="arm64"
DEFAULT_OUTPUT_ROOT="$SCRIPT_DIR"
RMS_TOOL_DIR="/tmp/rms-plugin-zip"
RMS_TOOL_REPO="https://cnb.cool/seer-robotics/src/tools/rms-plugin-zip.git"
SCRIPT_TARGET_PREFIX=".data/rbk/resources/scripts"
LIB_TARGET_PREFIX="data/rbk"

PACKAGE_ID=""
VERSION=""
DESCRIPTION=""
NODE="$DEFAULT_NODE"
OUTPUT_ROOT="$DEFAULT_OUTPUT_ROOT"

declare -a ARCHITECTURES=()
declare -a FILE_TYPES=()
declare -a FILE_SOURCES=()
declare -a FILE_TARGETS=()

usage() {
  cat <<'EOF'
Usage:
  ./build_deb.sh [build_deb.yml]
EOF
}

fail() {
  echo "build failed: $*" >&2
  exit 1
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

strip_quotes() {
  local value
  value="$(trim "$1")"
  if [[ ${#value} -ge 2 ]]; then
    if [[ ${value:0:1} == '"' && ${value: -1} == '"' ]]; then
      value="${value:1:${#value}-2}"
    elif [[ ${value:0:1} == "'" && ${value: -1} == "'" ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi
  printf '%s' "$value"
}

normalize_rel_path() {
  local path="$1"
  path="${path#./}"
  path="${path#/}"
  printf '%s' "$path"
}

sanitize_zip_token() {
  local value="$1"
  value="$(printf '%s' "$value" | tr '[:space:]/' '--' | LC_ALL=C tr -cd '[:alnum:]._\n-')"
  value="${value#-}"
  value="${value%-}"
  [[ -n "$value" ]] || value="payload"
  printf '%s' "$value"
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "missing required command: $cmd"
}

ensure_rms_tool() {
  if [[ -x "$RMS_TOOL_DIR/build_package.sh" ]]; then
    return
  fi
  require_cmd git
  git clone --depth 1 "$RMS_TOOL_REPO" "$RMS_TOOL_DIR"
}

validate_arch() {
  local arch="$1"
  case "$arch" in
    arm64|amd64|all)
      ;;
    *)
      fail "unsupported architecture: $arch"
      ;;
  esac
}

add_arch() {
  local arch
  arch="$(strip_quotes "$1")"
  arch="$(trim "$arch")"
  [[ -n "$arch" ]] || return
  ARCHITECTURES+=("$arch")
}

parse_inline_arch_list() {
  local raw="$1"
  local items=()
  local item=""

  raw="${raw#\[}"
  raw="${raw%\]}"
  IFS=',' read -r -a items <<< "$raw"
  for item in "${items[@]}"; do
    add_arch "$item"
  done
}

set_file_field() {
  local index="$1"
  local key="$2"
  local value="$3"

  value="$(strip_quotes "$value")"

  case "$key" in
    type|kind)
      FILE_TYPES[$index]="$(trim "$value")"
      ;;
    source|src|localPath)
      FILE_SOURCES[$index]="$(trim "$value")"
      ;;
    target|targetPath|dest)
      FILE_TARGETS[$index]="$(trim "$value")"
      ;;
    *)
      fail "unsupported file config key: $key"
      ;;
  esac
}

parse_file_mapping() {
  local index="$1"
  local line="$2"
  local key=""
  local value=""

  [[ "$line" == *:* ]] || fail "invalid file config line: $line"
  key="$(trim "${line%%:*}")"
  value="$(trim "${line#*:}")"
  set_file_field "$index" "$key" "$value"
}

load_config() {
  local config_path="$1"
  local raw_line=""
  local line=""
  local indent_text=""
  local indent=0
  local current_section=""
  local current_file_index=-1
  local key=""
  local value=""
  local item_line=""

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    raw_line="${raw_line%$'\r'}"
    line="$(trim "$raw_line")"

    [[ -z "$line" ]] && continue
    [[ ${line:0:1} == "#" ]] && continue

    indent_text="${raw_line%%[^ ]*}"
    indent=${#indent_text}

    if (( indent == 0 )); then
      current_file_index=-1

      if [[ "$line" == "files:" ]]; then
        current_section="files"
        continue
      fi

      if [[ "$line" == "arch:" ]]; then
        current_section="arch"
        continue
      fi

      [[ "$line" == *:* ]] || fail "invalid config line: $line"
      key="$(trim "${line%%:*}")"
      value="$(trim "${line#*:}")"
      current_section=""

      case "$key" in
        PackgeID|PackageID|packageId)
          PACKAGE_ID="$(strip_quotes "$value")"
          ;;
        version)
          VERSION="$(strip_quotes "$value")"
          ;;
        description)
          DESCRIPTION="$(strip_quotes "$value")"
          ;;
        node)
          NODE="$(strip_quotes "$value")"
          ;;
        outputDir)
          OUTPUT_ROOT="$(strip_quotes "$value")"
          ;;
        arch)
          value="$(strip_quotes "$value")"
          if [[ -z "$value" ]]; then
            current_section="arch"
          elif [[ "$value" == \[*\] ]]; then
            parse_inline_arch_list "$value"
          else
            add_arch "$value"
          fi
          ;;
        zipName)
          ;;
        *)
          fail "unsupported config key: $key"
          ;;
      esac
      continue
    fi

    case "$current_section" in
      arch)
        [[ "$line" == -* ]] || fail "arch list item must start with '-': $line"
        add_arch "${line#-}"
        ;;
      files)
        if [[ "$line" == -* ]]; then
          FILE_TYPES+=("")
          FILE_SOURCES+=("")
          FILE_TARGETS+=("")
          current_file_index=$(( ${#FILE_TYPES[@]} - 1 ))
          item_line="$(trim "${line#-}")"
          if [[ -n "$item_line" ]]; then
            parse_file_mapping "$current_file_index" "$item_line"
          fi
        else
          [[ $current_file_index -ge 0 ]] || fail "file item field must follow '-': $line"
          parse_file_mapping "$current_file_index" "$line"
        fi
        ;;
      *)
        fail "unexpected indented config line: $line"
        ;;
    esac
  done < "$config_path"
}

normalize_source_path() {
  local path="$1"
  path="$(strip_quotes "$path")"
  path="$(trim "$path")"
  [[ -n "$path" ]] || fail "file source cannot be empty"

  if [[ "$path" == /* ]]; then
    printf '%s' "$path"
  else
    printf '%s/%s' "$SCRIPT_DIR" "$(normalize_rel_path "$path")"
  fi
}

ensure_safe_target_rel() {
  local target="$1"
  [[ -n "$target" ]] || fail "file target cannot be empty"
  [[ "$target" != *".."* ]] || fail "target cannot contain '..': $target"
}

normalize_script_target() {
  local target="$1"
  local source_path="$2"
  target="$(strip_quotes "$target")"
  target="$(trim "$target")"

  if [[ -z "$target" ]]; then
    [[ "$source_path" == "$SCRIPT_DIR/"* ]] || fail "script target is empty and source is outside repo: $source_path"
    target="${source_path#"$SCRIPT_DIR"/}"
    target="$(normalize_rel_path "$target")"
    case "$target" in
      tasks/v3/*)
        target="tasks/${target#tasks/v3/}"
        ;;
      tasks/v4/*)
        target="tasks/${target#tasks/v4/}"
        ;;
      generic/v3/*)
        target="generic/${target#generic/v3/}"
        ;;
      generic/v4/*)
        target="generic/${target#generic/v4/}"
        ;;
    esac
  else
    target="${target#/opt/.data/rbk/resources/scripts/}"
    target="${target#/.data/rbk/resources/scripts/}"
    target="${target#${SCRIPT_TARGET_PREFIX}/}"
    target="$(normalize_rel_path "$target")"
  fi

  ensure_safe_target_rel "$target"
  printf '%s/%s' "$SCRIPT_TARGET_PREFIX" "$target"
}

normalize_lib_target() {
  local target="$1"
  target="$(strip_quotes "$target")"
  target="$(trim "$target")"
  target="${target#/opt/data/rbk/}"
  target="${target#/data/rbk/}"
  target="${target#${LIB_TARGET_PREFIX}/}"
  target="$(normalize_rel_path "$target")"
  ensure_safe_target_rel "$target"
  printf '%s/%s' "$LIB_TARGET_PREFIX" "$target"
}

normalize_file_type() {
  local file_type="$1"
  file_type="$(strip_quotes "$file_type")"
  file_type="$(trim "$file_type")"
  file_type="${file_type,,}"

  case "$file_type" in
    script|py)
      printf 'script'
      ;;
    lib|so|libso|plugin)
      printf 'lib'
      ;;
    *)
      fail "unsupported file type: $file_type"
      ;;
  esac
}

validate_binary_arch() {
  local source_path="$1"
  local arch="$2"
  local file_info=""

  file_info="$(file -Lb "$source_path")"

  case "$arch" in
    arm64)
      [[ "$file_info" == *"ARM aarch64"* ]] || fail "binary architecture mismatch for $source_path: expected arm64, got: $file_info"
      ;;
    amd64)
      [[ "$file_info" == *"x86-64"* ]] || fail "binary architecture mismatch for $source_path: expected amd64, got: $file_info"
      ;;
    all)
      fail "binary file does not support architecture 'all': $source_path"
      ;;
    *)
      fail "unsupported architecture: $arch"
      ;;
  esac
}

stage_payload_files() {
  local payload_dir="$1"
  local arch="$2"
  local i=""
  local file_type=""
  local source_path=""
  local target_path=""
  local dest_path=""

  for i in "${!FILE_TYPES[@]}"; do
    file_type="$(normalize_file_type "${FILE_TYPES[$i]}")"
    source_path="$(normalize_source_path "${FILE_SOURCES[$i]}")"
    [[ -f "$source_path" ]] || fail "source file not found: $source_path"

    if [[ "$file_type" == "script" ]]; then
      target_path="$(normalize_script_target "${FILE_TARGETS[$i]}" "$source_path")"
    else
      validate_binary_arch "$source_path" "$arch"
      target_path="$(normalize_lib_target "${FILE_TARGETS[$i]}")"
    fi

    dest_path="$payload_dir/$target_path"
    mkdir -p "$(dirname "$dest_path")"
    cp "$source_path" "$dest_path"
  done
}

resolve_output_root() {
  local path="$1"
  path="$(strip_quotes "$path")"
  path="$(trim "$path")"
  [[ -n "$path" ]] || path="$DEFAULT_OUTPUT_ROOT"

  if [[ "$path" == /* ]]; then
    printf '%s' "$path"
  else
    printf '%s/%s' "$SCRIPT_DIR" "$(normalize_rel_path "$path")"
  fi
}

build_for_arch() {
  local arch="$1"
  local timestamp=""
  local version_value=""
  local description_slug=""
  local output_dir=""
  local work_dir=""
  local payload_dir=""
  local inner_zip=""

  validate_arch "$arch"

  timestamp="$(date +%Y%m%d%H%M%S)"
  version_value="$VERSION"
  [[ -n "$version_value" ]] || version_value="$(date +%Y.%m.%d.%H%M%S)"
  description_slug="$(sanitize_zip_token "${DESCRIPTION:-package}")"
  output_dir="$(resolve_output_root "$OUTPUT_ROOT")/dist_rms_${arch}_${timestamp}"

  work_dir="$(mktemp -d)"
  payload_dir="$work_dir/payload"
  inner_zip="$work_dir/${PACKAGE_ID}-${version_value}-${arch}-${description_slug}.zip"

  mkdir -p "$payload_dir"
  stage_payload_files "$payload_dir" "$arch"

  (
    cd "$payload_dir"
    zip -qr "$inner_zip" .
  )

  mkdir -p "$output_dir"
  (
    cd "$output_dir"
    printf '%s\n' \
      "$PACKAGE_ID" \
      "$version_value" \
      "$arch" \
      "${NODE:-$DEFAULT_NODE}" \
      "plugin" \
      "$DESCRIPTION" \
      "/opt" | \
      bash "$RMS_TOOL_DIR/build_package.sh" "$inner_zip"
  )

  rm -rf "$work_dir"
  echo "generated package dir: $output_dir"
  ls -la "$output_dir"
}

main() {
  local config_path=""
  local arch=""

  if [[ $# -gt 1 ]]; then
    usage
    exit 1
  fi

  config_path="${1:-$DEFAULT_CONFIG}"
  if [[ "$config_path" != /* ]]; then
    config_path="$SCRIPT_DIR/$(normalize_rel_path "$config_path")"
  fi
  [[ -f "$config_path" ]] || fail "config file not found: $config_path"

  require_cmd bash
  require_cmd zip
  require_cmd mktemp
  require_cmd cp
  require_cmd file
  ensure_rms_tool

  load_config "$config_path"

  [[ -n "$PACKAGE_ID" ]] || fail "PackageID is required"
  if [[ ${#ARCHITECTURES[@]} -eq 0 ]]; then
    ARCHITECTURES=("$DEFAULT_ARCH")
  fi
  [[ ${#FILE_TYPES[@]} -gt 0 ]] || fail "files must contain at least one item"

  for arch in "${ARCHITECTURES[@]}"; do
    build_for_arch "$arch"
  done
}

main "$@"
