#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DEFAULT_CONFIG="$SCRIPT_DIR/build_deb.yml"
OUTPUT_DIR="$SCRIPT_DIR/deb"
DEFAULT_DESCRIPTION="Monthly release: RBK + navigation plugin + config update"
TARGET_PATH="/opt"
ISPY_PREFIX=".data/rbk/resources/scripts"
DEFAULT_NODE="master"

PACKAGE_ID=""
VERSION=""
ZIP_NAME=""
DESCRIPTION=""
NODE="$DEFAULT_NODE"
IS_PY="false"
declare -a ARCHITECTURES=()
declare -a ORIGIN_PATHS=()
declare -a ORIGIN_FILES=()

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

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '%s' "$value"
}

normalize_bool() {
  local value
  value="$(strip_quotes "$1")"
  value="$(trim "$value")"
  value="${value,,}"
  case "$value" in
    true|yes|1|on)
      printf 'true'
      ;;
    false|no|0|off|"")
      printf 'false'
      ;;
    *)
      fail "unsupported boolean value: $1"
      ;;
  esac
}

require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "missing required command: $cmd"
}

parse_inline_list() {
  local raw="$1"
  local list_name="$2"
  local item=""
  local items=()

  raw="${raw#\[}"
  raw="${raw%\]}"
  IFS=',' read -r -a items <<< "$raw"
  for item in "${items[@]}"; do
    item="$(strip_quotes "$item")"
    item="$(trim "$item")"
    [[ -n "$item" ]] || continue
    case "$list_name" in
      arch)
        ARCHITECTURES+=("$item")
        ;;
      originPath)
        ORIGIN_PATHS+=("$item")
        ;;
      *)
        fail "unsupported list key: $list_name"
        ;;
    esac
  done
}

load_config() {
  local config_path="$1"
  local current_list=""
  local raw_line=""
  local line=""
  local key=""
  local value=""
  local item=""

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="${raw_line%$'\r'}"
    line="$(trim "$line")"

    [[ -z "$line" ]] && continue
    [[ ${line:0:1} == "#" ]] && continue

    if [[ "$line" == -* ]]; then
      item="$(strip_quotes "${line#-}")"
      item="$(trim "$item")"
      case "$current_list" in
        arch)
          ARCHITECTURES+=("$item")
          ;;
        originPath)
          ORIGIN_PATHS+=("$item")
          ;;
        *)
          fail "list item must follow arch or originPath: $line"
          ;;
      esac
      continue
    fi

    key="$(trim "${line%%:*}")"
    value="$(trim "${line#*:}")"

    case "$key" in
      PackgeID|PackageID)
        PACKAGE_ID="$(strip_quotes "$value")"
        current_list=""
        ;;
      version)
        VERSION="$(strip_quotes "$value")"
        current_list=""
        ;;
      zipName)
        ZIP_NAME="$(strip_quotes "$value")"
        current_list=""
        ;;
      description)
        DESCRIPTION="$(strip_quotes "$value")"
        current_list=""
        ;;
      ispy)
        IS_PY="$(normalize_bool "$value")"
        current_list=""
        ;;
      node)
        NODE="$(strip_quotes "$value")"
        current_list=""
        ;;
      arch)
        value="$(strip_quotes "$value")"
        if [[ -n "$value" ]]; then
          if [[ "$value" == \[*\] ]]; then
            parse_inline_list "$value" arch
          else
            ARCHITECTURES+=("$value")
          fi
          current_list=""
        else
          current_list="arch"
        fi
        ;;
      originPath)
        value="$(strip_quotes "$value")"
        if [[ -n "$value" ]]; then
          if [[ "$value" == \[*\] ]]; then
            parse_inline_list "$value" originPath
          else
            ORIGIN_PATHS+=("$value")
          fi
          current_list=""
        else
          current_list="originPath"
        fi
        ;;
      *)
        fail "unsupported config key: $key"
        ;;
    esac
  done < "$config_path"
}

validate_arch() {
  local arch="$1"
  case "$arch" in
    amd64|arm64|all|x86|x64|noarch)
      ;;
    *)
      fail "unsupported architecture: $arch"
      ;;
  esac
}

normalize_rel_path() {
  local path="$1"
  path="${path#./}"
  path="${path#/}"
  printf '%s' "$path"
}

expand_origin_entry() {
  local entry="$1"
  local clean_entry=""
  local prefix="$SCRIPT_DIR/"
  local matches=()
  local match=""
  local file=""

  entry="$(strip_quotes "$entry")"
  entry="$(trim "$entry")"
  [[ -n "$entry" ]] || fail "originPath cannot be empty"
  [[ "$entry" != /* ]] || fail "originPath must be relative to build_deb.sh: $entry"

  clean_entry="$(normalize_rel_path "$entry")"

  if [[ "$clean_entry" == *"*"* || "$clean_entry" == *"?"* || "$clean_entry" == *"["* ]]; then
    shopt -s nullglob
    matches=( "$SCRIPT_DIR"/$clean_entry )
    shopt -u nullglob
    [[ ${#matches[@]} -gt 0 ]] || fail "originPath pattern matched no files: $entry"

    for match in "${matches[@]}"; do
      if [[ -d "$match" ]]; then
        while IFS= read -r -d '' file; do
          printf '%s\n' "${file#$prefix}"
        done < <(find "$match" -type f -print0)
      elif [[ -f "$match" ]]; then
        printf '%s\n' "${match#$prefix}"
      fi
    done
    return
  fi

  if [[ -d "$SCRIPT_DIR/$clean_entry" ]]; then
    while IFS= read -r -d '' file; do
      printf '%s\n' "${file#$prefix}"
    done < <(find "$SCRIPT_DIR/$clean_entry" -type f -print0)
    return
  fi

  if [[ -f "$SCRIPT_DIR/$clean_entry" ]]; then
    printf '%s\n' "$clean_entry"
    return
  fi

  fail "originPath not found: $entry"
}

collect_origin_files() {
  local entry=""
  local file=""
  declare -A seen=()
  ORIGIN_FILES=()

  for entry in "${ORIGIN_PATHS[@]}"; do
    while IFS= read -r file; do
      [[ -n "$file" ]] || continue
      if [[ -z "${seen[$file]+x}" ]]; then
        seen["$file"]=1
        ORIGIN_FILES+=("$file")
      fi
    done < <(expand_origin_entry "$entry")
  done
}

remove_version_dir_from_path() {
  local path="$1"
  local part=""
  local result=()

  case "$path" in
    "$ISPY_PREFIX"/tasks/*|"$ISPY_PREFIX"/generic/*)
      ;;
    *)
      printf '%s' "$path"
      return
      ;;
  esac

  IFS='/' read -r -a _parts <<< "$path"
  for part in "${_parts[@]}"; do
    if [[ "$part" == "v3" || "$part" == "v4" ]]; then
      continue
    fi
    [[ -n "$part" ]] && result+=("$part")
  done

  (IFS='/'; printf '%s' "${result[*]}")
}

stage_origin_files() {
  local stage_dir="$1"
  local src_rel=""
  local archive_rel=""
  local dest_rel=""
  local dest_path=""
  local src_priority=0
  local old_priority=0
  local old_src=""
  declare -A staged_src=()
  declare -A staged_priority=()

  get_source_priority() {
    local path="$1"

    case "$path" in
      "$ISPY_PREFIX"/tasks/*|"$ISPY_PREFIX"/generic/*)
        ;;
      *)
        printf '2'
        return
        ;;
    esac

    if [[ "$path" == *"/v3/"* || "$path" == v3/* ]]; then
      printf '3'
    elif [[ "$path" == *"/v4/"* || "$path" == v4/* ]]; then
      printf '1'
    else
      printf '2'
    fi
  }

  for src_rel in "${ORIGIN_FILES[@]}"; do
    if [[ "$IS_PY" == "true" ]]; then
      archive_rel="$(normalize_rel_path "$ISPY_PREFIX/$src_rel")"
    else
      archive_rel="$(normalize_rel_path "$src_rel")"
    fi

    dest_rel="$(remove_version_dir_from_path "$archive_rel")"
    [[ -n "$dest_rel" ]] || fail "empty archive path after removing v3/v4: $src_rel"
    src_priority="$(get_source_priority "$archive_rel")"

    if [[ -n "${staged_src[$dest_rel]+x}" ]]; then
      old_src="${staged_src[$dest_rel]}"
      old_priority="${staged_priority[$dest_rel]}"

      if (( src_priority > old_priority )); then
        staged_src["$dest_rel"]="$src_rel"
        staged_priority["$dest_rel"]="$src_priority"
      elif (( src_priority == old_priority )) && [[ "$old_src" != "$src_rel" ]]; then
        fail "archive path conflict with same priority: $old_src and $src_rel -> $dest_rel"
      fi
    else
      staged_src["$dest_rel"]="$src_rel"
      staged_priority["$dest_rel"]="$src_priority"
    fi
  done

  for dest_rel in "${!staged_src[@]}"; do
    src_rel="${staged_src[$dest_rel]}"
    dest_path="$stage_dir/$dest_rel"
    if [[ "${staged_priority[$dest_rel]}" == "1" ]]; then
      echo "skip v4 override kept for archive path: $dest_rel"
    fi

    mkdir -p "$(dirname "$dest_path")"
    cp "$SCRIPT_DIR/$src_rel" "$dest_path"
  done
}

build_manifest() {
  local plugin_zip_name="$1"
  local plugin_sha256="$2"
  local arch="$3"

  cat <<EOF
{
  "manifestVersion": "1.0",
  "metadata": {
    "packageId": "$(json_escape "$PACKAGE_ID")",
    "version": "$(json_escape "$VERSION")",
    "arch": "$(json_escape "$arch")",
    "node": "$(json_escape "$NODE")",
    "type": "plugin",
    "description": "$(json_escape "$DESCRIPTION")"
  },
  "resources": [
    {
      "type": "plugin",
      "order": 1,
      "name": "$(json_escape "$PACKAGE_ID")",
      "version": "$(json_escape "$VERSION")",
      "method": "zip_extract",
      "fileName": "$(json_escape "$plugin_zip_name")",
      "sha256": "$plugin_sha256",
      "required": true,
      "targetPath": "$TARGET_PATH"
    }
  ],
  "lifecycle": {
    "afterAll": {
      "commands": [
        "sync",
        "systemctl reboot"
      ],
      "timeout": 60
    }
  }
}
EOF
}

build_outer_zip_name() {
  local arch="$1"
  local arch_count="${#ARCHITECTURES[@]}"
  local base_name="${ZIP_NAME%.zip}"

  if [[ "$arch_count" -gt 1 ]]; then
    printf '%s-%s.zip' "$base_name" "$arch"
  else
    printf '%s.zip' "$base_name"
  fi
}

package_for_arch() {
  local arch="$1"
  local plugin_zip_name="plugin-${PACKAGE_ID}-${VERSION}-${arch}.zip"
  local plugin_zip_path=""
  local outer_zip_name=""
  local outer_zip_path=""
  local plugin_sha256=""
  local temp_dir=""
  local stage_dir=""
  local plugin_stage_dir=""
  local manifest_path=""
  local manifest_sha256=""

  outer_zip_name="$(build_outer_zip_name "$arch")"
  outer_zip_path="$OUTPUT_DIR/$outer_zip_name"

  [[ ! -e "$outer_zip_path" ]] || fail "outer zip already exists: $outer_zip_path"
  temp_dir="$(mktemp -d)"
  stage_dir="$temp_dir/stage"
  plugin_stage_dir="$temp_dir/plugin"
  plugin_zip_path="$temp_dir/$plugin_zip_name"
  manifest_path="$temp_dir/manifest.json"
  mkdir -p "$stage_dir"
  mkdir -p "$plugin_stage_dir"

  stage_origin_files "$plugin_stage_dir"
  (
    cd "$plugin_stage_dir"
    zip -qr "$plugin_zip_path" .
  )

  plugin_sha256="$(sha256sum "$plugin_zip_path" | awk '{print $1}')"
  build_manifest "$plugin_zip_name" "$plugin_sha256" "$arch" > "$manifest_path"
  manifest_sha256="$(sha256sum "$manifest_path" | awk '{print $1}')"
  printf '%s  manifest.json\n' "$manifest_sha256" > "$temp_dir/manifest.json.sha256"

  cp "$plugin_zip_path" "$stage_dir/$plugin_zip_name"
  cp "$manifest_path" "$stage_dir/manifest.json"
  cp "$temp_dir/manifest.json.sha256" "$stage_dir/manifest.json.sha256"

  (
    cd "$stage_dir"
    zip -qr "$outer_zip_path" "$plugin_zip_name" manifest.json manifest.json.sha256
  )

  rm -rf "$temp_dir"

  echo "generated outer zip: $outer_zip_path"
}

main() {
  local config_path=""

  if [[ $# -gt 1 ]]; then
    usage
    exit 1
  fi

  if [[ $# -eq 1 ]]; then
    config_path="$1"
  else
    config_path="$DEFAULT_CONFIG"
  fi

  [[ -f "$config_path" ]] || fail "config file not found: $config_path"

  require_cmd zip
  require_cmd sha256sum
  require_cmd awk
  require_cmd mktemp
  require_cmd find

  load_config "$config_path"

  [[ -n "$PACKAGE_ID" ]] || fail "PackgeID is required"
  [[ -n "$VERSION" ]] || fail "version is required"
  [[ -n "$ZIP_NAME" ]] || fail "zipName is required"
  [[ ${#ARCHITECTURES[@]} -gt 0 ]] || fail "arch must contain at least one item"
  [[ ${#ORIGIN_PATHS[@]} -gt 0 ]] || fail "originPath must contain at least one item"

  PACKAGE_ID="${PACKAGE_ID%.zip}"
  ZIP_NAME="${ZIP_NAME%.zip}"
  DESCRIPTION="${DESCRIPTION:-$DEFAULT_DESCRIPTION}"
  NODE="${NODE:-$DEFAULT_NODE}"

  mkdir -p "$OUTPUT_DIR"

  for arch in "${ARCHITECTURES[@]}"; do
    validate_arch "$arch"
  done

  collect_origin_files
  [[ ${#ORIGIN_FILES[@]} -gt 0 ]] || fail "originPath resolved to no files"

  for arch in "${ARCHITECTURES[@]}"; do
    package_for_arch "$arch"
  done
}

main "$@"
