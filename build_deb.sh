#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DEFAULT_CONFIG="$SCRIPT_DIR/build_deb.yml"
DEFAULT_NODE="master"
DEFAULT_ARCH="arm64"
DEFAULT_OUTPUT_ROOT="$SCRIPT_DIR"
DEFAULT_MANIFEST_VERSION="2.0"
RMS_TOOL_DIR="/tmp/rms-controller-packaging-tool"
RMS_TOOL_REPO="https://cnb.cool/seer-robotics/EIC/RMS/rms-controller-packaging-tool.git"
RMS_TOOL_ENTRY="build-manifest-package.py"
SCRIPT_TARGET_PREFIX=".data/rbk/resources/scripts"
LIB_TARGET_PREFIX="data/rbk"
PAYLOAD_TARGET_PREFIX="/opt"

PACKAGE_ID=""
VERSION=""
DESCRIPTION=""
NODE="$DEFAULT_NODE"
OUTPUT_ROOT="$DEFAULT_OUTPUT_ROOT"
MANIFEST_VERSION="$DEFAULT_MANIFEST_VERSION"
DEBUG_OUTPUT=0

declare -a ARCHITECTURES=()
declare -a FILE_TYPES=()
declare -a FILE_SOURCES=()
declare -a FILE_TARGETS=()

usage() {
  cat <<'EOF'
Usage:
  ./build_deb.sh [--debug] [build_deb.yml]
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
  if [[ -f "$RMS_TOOL_DIR/$RMS_TOOL_ENTRY" ]]; then
    return
  fi
  if [[ -e "$RMS_TOOL_DIR" ]]; then
    fail "manifest tool dir exists but $RMS_TOOL_ENTRY not found: $RMS_TOOL_DIR"
  fi
  require_cmd git
  git clone --depth 1 "$RMS_TOOL_REPO" "$RMS_TOOL_DIR"
  [[ -f "$RMS_TOOL_DIR/$RMS_TOOL_ENTRY" ]] || fail "manifest tool clone succeeded but $RMS_TOOL_ENTRY is missing"
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

validate_manifest_version() {
  local version="$1"
  case "$version" in
    1.0|2.0)
      ;;
    *)
      fail "unsupported manifest version: $version"
      ;;
  esac
}

add_arch() {
  local arch
  arch="$(strip_quotes "$1")"
  arch="$(trim "$arch")"
  [[ -n "$arch" ]] || return
  validate_arch "$arch"
  ARCHITECTURES+=("$arch")
}

array_contains() {
  local needle="$1"
  shift
  local item=""

  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

expand_architectures() {
  local resolved_architectures=()
  local arch=""
  local expanded_arch=""

  for arch in "${ARCHITECTURES[@]}"; do
    if [[ "$arch" == "all" ]]; then
      for expanded_arch in arm64 amd64; do
        if ! array_contains "$expanded_arch" "${resolved_architectures[@]}"; then
          resolved_architectures+=("$expanded_arch")
        fi
      done
      continue
    fi

    if ! array_contains "$arch" "${resolved_architectures[@]}"; then
      resolved_architectures+=("$arch")
    fi
  done

  ARCHITECTURES=("${resolved_architectures[@]}")
}

ensure_arch_all_supported() {
  local file_type=""

  if ! array_contains "all" "${ARCHITECTURES[@]}"; then
    return
  fi

  for file_type in "${FILE_TYPES[@]}"; do
    if [[ "$(normalize_file_type "$file_type")" != "script" ]]; then
      fail "arch 'all' only supports script files; binary/plugin files must declare concrete architectures"
    fi
  done
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
        manifestVersion|manifest-version)
          MANIFEST_VERSION="$(strip_quotes "$value")"
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

infer_script_target_from_source() {
  local source_path="$1"
  local target=""

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

  printf '%s' "$target"
}

normalize_script_target() {
  local target="$1"
  local source_path="$2"
  target="$(strip_quotes "$target")"
  target="$(trim "$target")"

  if [[ -z "$target" ]]; then
    target="$(infer_script_target_from_source "$source_path")"
  fi

  target="${target#/opt/.data/rbk/resources/scripts/}"
  target="${target#/.data/rbk/resources/scripts/}"
  target="${target#${SCRIPT_TARGET_PREFIX}/}"
  target="$(normalize_rel_path "$target")"
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
  local package_slug=""
  local output_root=""
  local output_name=""
  local output_dir=""
  local work_dir=""
  local payload_dir=""
  local inner_zip=""
  local resource_zip=""
  local final_package_zip=""
  local -a tool_args=()

  validate_arch "$arch"

  timestamp="$(date +%Y%m%d%H%M%S)"
  version_value="$VERSION"
  [[ -n "$version_value" ]] || version_value="$(date +%Y.%m.%d.%H%M%S)"
  description_slug="$(sanitize_zip_token "${DESCRIPTION:-package}")"
  package_slug="$(sanitize_zip_token "$PACKAGE_ID")"
  output_root="$(resolve_output_root "$OUTPUT_ROOT")"
  output_name="${package_slug}-manifest-${version_value}-${arch}"
  output_dir="$output_root/$output_name"

  work_dir="$(mktemp -d)"
  payload_dir="$work_dir/payload"
  inner_zip="$work_dir/${PACKAGE_ID}-${version_value}-${arch}-${description_slug}.zip"

  mkdir -p "$payload_dir"
  stage_payload_files "$payload_dir" "$arch"

  (
    cd "$payload_dir"
    zip -qr "$inner_zip" .
  )

  mkdir -p "$output_root"
  tool_args=(
    zip
    --zip "$inner_zip"
    --target-path "$PAYLOAD_TARGET_PREFIX"
    --manifest-version "$MANIFEST_VERSION"
    --output-name "$output_name"
    --output-root "$output_root"
    --resource-name "$PACKAGE_ID"
    --package-id "$PACKAGE_ID"
    --package-type "plugin"
    --package-version "$version_value"
    --arch "$arch"
    --force
  )
  if [[ -n "$NODE" ]]; then
    tool_args+=(--node "$NODE")
  fi
  if [[ -n "$DESCRIPTION" ]]; then
    tool_args+=(--description "$DESCRIPTION")
  fi

  python3 "$RMS_TOOL_DIR/$RMS_TOOL_ENTRY" "${tool_args[@]}"

  resource_zip="$output_dir/$(basename "$inner_zip")"
  final_package_zip="$output_root/$output_name.zip"

  [[ -f "$final_package_zip" ]] || fail "final manifest package zip not found: $final_package_zip"
  if (( DEBUG_OUTPUT )); then
    rm -f "$resource_zip"
  else
    rm -rf "$output_dir"
  fi

  rm -rf "$work_dir"
  if (( DEBUG_OUTPUT )); then
    echo "debug manifest dir: $output_dir"
    ls -la "$output_dir"
  fi
  echo "final manifest package zip: $final_package_zip"
}

main() {
  local config_path="$DEFAULT_CONFIG"
  local config_explicit=0
  local arch=""
  local arg=""

  while [[ $# -gt 0 ]]; do
    arg="$1"
    shift

    case "$arg" in
      --debug)
        DEBUG_OUTPUT=1
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      -*)
        fail "unknown option: $arg"
        ;;
      *)
        if (( config_explicit )); then
          fail "only one config file can be specified"
        fi
        config_path="$arg"
        config_explicit=1
        ;;
    esac
  done

  if [[ "$config_path" != /* ]]; then
    config_path="$SCRIPT_DIR/$(normalize_rel_path "$config_path")"
  fi
  [[ -f "$config_path" ]] || fail "config file not found: $config_path"

  require_cmd bash
  require_cmd zip
  require_cmd mktemp
  require_cmd cp
  require_cmd file
  require_cmd python3
  ensure_rms_tool

  load_config "$config_path"
  validate_manifest_version "$MANIFEST_VERSION"

  [[ -n "$PACKAGE_ID" ]] || fail "PackageID is required"
  if [[ ${#ARCHITECTURES[@]} -eq 0 ]]; then
    ARCHITECTURES=("$DEFAULT_ARCH")
  fi
  ensure_arch_all_supported
  expand_architectures
  [[ ${#FILE_TYPES[@]} -gt 0 ]] || fail "files must contain at least one item"

  for arch in "${ARCHITECTURES[@]}"; do
    build_for_arch "$arch"
  done
}

main "$@"
