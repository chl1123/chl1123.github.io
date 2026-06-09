#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  ./submit_pr.sh
  ./submit_pr.sh e047c541
  ./submit_pr.sh --source-branch mazj e047c541 0fd7f77d
  ./submit_pr.sh --source-branch mazj HEAD~1 HEAD
  ./submit_pr.sh --path syspy/actions.py --source-branch mazj HEAD
  ./submit_pr.sh --path submit_pr.sh --path build_deb.sh --path build_deb.yml --path README.md --source-branch mazj HEAD
  ./submit_pr.sh --submit-branch mazj-release-submit-v2 e047c541
  ./submit_pr.sh --title "fix: xxx" --body-file pr.md e047c541
  ./submit_pr.sh --reuse-branch --update-pr 8 --submit-branch feature-fix-v2 --path syspy/actions.py --body-file pr.md HEAD
  ./submit_pr.sh --dry-run e047c541

说明:
  - 默认源分支: 当前分支
  - 默认 commit: 源分支的 HEAD
  - 默认 base 分支: release
  - 默认 PR 标题: 复用最后一个 commit 的 subject
  - 多个 commit 时, PR body 会列出所有 commit subject
  - `--path` 模式下不会 cherry-pick commit, 而是把指定文件从源快照复制到 base 分支后生成一个新的提交
  - `--path` 模式当前只支持一个 commit/ref, 适合做“只提交 actions.py”或“只提交几个脚本/文档”的 PR
  - 更新已有 PR 时, 用 `--reuse-branch --update-pr <编号>` 复用远端分支并 PATCH 标题/正文

选项:
  --source-branch <branch>  指定源分支, 默认当前分支
  --base <branch>           指定目标分支, 默认 release
  --submit-branch <branch>  指定 submit 分支名
  --path <file>             只提交指定文件, 可重复传入多个路径
  --title <title>           手动覆盖 PR 标题
  --body-file <file>        从文件读取 PR 正文
  --reuse-branch            允许复用已存在的 submit 分支, push 时使用 --force-with-lease
  --update-pr <number>      不新建 PR, 改为更新指定 PR 的标题/正文
  --dry-run                 只执行到本地 cherry-pick, 不 push 不开 PR
  -h, --help                查看帮助

示例:
  1. 普通 commit PR:
     ./submit_pr.sh --source-branch mazj 4e8ce316

  2. 只提交一个文件:
     ./submit_pr.sh \
       --source-branch mazj \
       --path syspy/actions.py \
       --title "feat: m-6998182168 refactor actions rotate flow" \
       HEAD

  3. 只提交多个文件:
     ./submit_pr.sh \
       --source-branch mazj \
       --path submit_pr.sh \
       --path build_deb.sh \
       --path build_deb.yml \
       --path README.md \
       --title "chore: update pr helper and packaging docs" \
       HEAD

  4. 更新已有 PR:
     ./submit_pr.sh \
       --source-branch mazj \
       --submit-branch mazj-actions-release-v2 \
       --path syspy/actions.py \
       --reuse-branch \
       --update-pr 8 \
       --title "feat: m-6998182168 refactor actions rotate flow" \
       --body-file pr.md \
       HEAD
EOF
}

log() {
  printf '[submit_pr] %s\n' "$*"
}

die() {
  printf '[submit_pr] %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || die "缺少命令: $cmd"
  done
}

parse_remote_info() {
  local remote_url="$1"
  local host=""
  local repo_path=""
  case "$remote_url" in
    https://*|http://*)
      local no_proto="${remote_url#*://}"
      host="${no_proto%%/*}"
      repo_path="${no_proto#*/}"
      ;;
    git@*:* )
      local no_user="${remote_url#git@}"
      host="${no_user%%:*}"
      repo_path="${no_user#*:}"
      ;;
    ssh://git@*/*)
      local no_proto="${remote_url#ssh://git@}"
      host="${no_proto%%/*}"
      repo_path="${no_proto#*/}"
      ;;
    *)
      die "暂不支持的 origin url: $remote_url"
      ;;
  esac
  repo_path="${repo_path%.git}"
  [[ -n "$host" ]] || die "无法解析 remote host: $remote_url"
  [[ -n "$repo_path" ]] || die "无法解析 remote repo path: $remote_url"
  printf '%s\n%s\n' "$host" "$repo_path"
}

get_credential_token() {
  local host="$1"
  local credential_output=""
  local token=""

  credential_output="$(printf 'protocol=https\nhost=%s\n\n' "$host" | git credential fill)"
  token="$(printf '%s\n' "$credential_output" | awk -F= '$1 == "password" {print substr($0, index($0, "=") + 1)}')"
  [[ -n "$token" ]] || die "未获取到 ${host} 的访问凭据, 请先配置 git credential"
  printf '%s\n' "$token"
}

build_default_pr_body() {
  if [[ ${#PATHS[@]} -gt 0 ]]; then
    local body=""
    local path=""
    body=$'Auto-created by submit_pr.sh.\n\n'
    body+="Mode: path-copy"$'\n'
    body+="Source branch: ${SOURCE_BRANCH}"$'\n'
    body+="Source snapshot: ${SOURCE_SNAPSHOT}"$'\n'
    body+="Base branch: ${BASE_BRANCH}"$'\n'
    body+="Submit branch: ${SUBMIT_BRANCH}"$'\n'
    body+=$'\nPaths:\n'
    for path in "${PATHS[@]}"; do
      body+="- ${path}"$'\n'
    done
    printf '%s' "$body"
    return
  fi

  if [[ ${#COMMIT_SHAS[@]} -eq 1 ]]; then
    local commit_body=""
    commit_body="$(git -C "$REPO_ROOT" show -s --format=%b "$last_sha")"
    if [[ "$commit_body" =~ [^[:space:]] ]]; then
      printf '%s\n' "$commit_body"
      return
    fi
  fi

  local body=""
  body=$'Auto-created by submit_pr.sh.\n\n'
  body+="Source branch: ${SOURCE_BRANCH}"$'\n'
  body+="Base branch: ${BASE_BRANCH}"$'\n'
  body+="Submit branch: ${SUBMIT_BRANCH}"$'\n'
  body+=$'\nCherry-picked commits:\n'

  local i
  for i in "${!COMMIT_SHAS[@]}"; do
    body+="- ${COMMIT_SHAS[$i]:0:8} ${COMMIT_SUBJECTS[$i]}"$'\n'
  done

  printf '%s' "$body"
}

resolve_commit_ref() {
  local source_branch="$1"
  local commit_ref="$2"
  local resolved_ref="$commit_ref"

  if [[ "$commit_ref" == HEAD* ]]; then
    resolved_ref="${source_branch}${commit_ref#HEAD}"
  fi

  git -C "$REPO_ROOT" rev-parse --verify "${resolved_ref}^{commit}"
}

build_pr_payload() {
  python3 - "$1" "$2" "$3" "$4" "$5" <<'PY'
import json
import sys

base, head, repo, title, body = sys.argv[1:6]
print(json.dumps({
    "base": base,
    "head": head,
    "head_repo": repo,
    "title": title,
    "body": body,
}, ensure_ascii=False))
PY
}

extract_pr_number() {
  python3 - <<'PY'
import json
import sys

data = json.load(sys.stdin)
print(data.get("number", ""))
PY
}

apply_paths_from_ref() {
  local source_ref="$1"
  local path=""

  for path in "${PATHS[@]}"; do
    if git -C "$REPO_ROOT" cat-file -e "${source_ref}:${path}" 2>/dev/null; then
      git -C "$WORKTREE_DIR" checkout "$source_ref" -- "$path"
    else
      git -C "$WORKTREE_DIR" rm -f --ignore-unmatch -- "$path" >/dev/null 2>&1 || true
    fi
  done

  git -C "$WORKTREE_DIR" add -A -- "${PATHS[@]}"
}

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REMOTE="origin"
BASE_BRANCH="release"
SOURCE_BRANCH=""
SUBMIT_BRANCH=""
TITLE_OVERRIDE=""
BODY_FILE=""
DRY_RUN=0
WORKTREE_DIR=""
KEEP_WORKTREE=1
DELETE_LOCAL_BRANCH=0
COMMITS=()
PATHS=()
REUSE_BRANCH=0
UPDATE_PR=""
SOURCE_SNAPSHOT=""
LOCAL_BRANCH_EXISTS=0
REMOTE_BRANCH_EXISTS=0

require_cmd git curl python3 mktemp

while (($# > 0)); do
  case "$1" in
    --source-branch)
      (($# >= 2)) || die "--source-branch 缺少参数"
      SOURCE_BRANCH="$2"
      shift 2
      ;;
    --base)
      (($# >= 2)) || die "--base 缺少参数"
      BASE_BRANCH="$2"
      shift 2
      ;;
    --submit-branch)
      (($# >= 2)) || die "--submit-branch 缺少参数"
      SUBMIT_BRANCH="$2"
      shift 2
      ;;
    --path)
      (($# >= 2)) || die "--path 缺少参数"
      PATHS+=("$2")
      shift 2
      ;;
    --title)
      (($# >= 2)) || die "--title 缺少参数"
      TITLE_OVERRIDE="$2"
      shift 2
      ;;
    --body-file)
      (($# >= 2)) || die "--body-file 缺少参数"
      BODY_FILE="$2"
      shift 2
      ;;
    --reuse-branch)
      REUSE_BRANCH=1
      shift
      ;;
    --update-pr)
      (($# >= 2)) || die "--update-pr 缺少参数"
      UPDATE_PR="$2"
      REUSE_BRANCH=1
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while (($# > 0)); do
        COMMITS+=("$1")
        shift
      done
      ;;
    -*)
      die "未知参数: $1"
      ;;
    *)
      COMMITS+=("$1")
      shift
      ;;
  esac
done

cleanup() {
  if [[ -n "$WORKTREE_DIR" && -d "$WORKTREE_DIR" ]]; then
    if [[ "$KEEP_WORKTREE" == 0 ]]; then
      git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_DIR" >/dev/null 2>&1 || rm -rf "$WORKTREE_DIR"
    else
      printf '[submit_pr] 临时 worktree 已保留: %s\n' "$WORKTREE_DIR" >&2
    fi
  fi

  if [[ "$DELETE_LOCAL_BRANCH" == 1 ]]; then
    git -C "$REPO_ROOT" branch -D "$SUBMIT_BRANCH" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

git -C "$REPO_ROOT" rev-parse --show-toplevel >/dev/null 2>&1 || die "脚本目录不是 git 仓库"

if [[ -z "$SOURCE_BRANCH" ]]; then
  SOURCE_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
  [[ -n "$SOURCE_BRANCH" ]] || die "当前是 detached HEAD, 请使用 --source-branch 指定源分支"
fi

git -C "$REPO_ROOT" rev-parse --verify "$SOURCE_BRANCH" >/dev/null 2>&1 || die "源分支不存在: $SOURCE_BRANCH"

if [[ ${#COMMITS[@]} -eq 0 ]]; then
  COMMITS=("HEAD")
fi

if [[ ${#PATHS[@]} -gt 0 && ${#COMMITS[@]} -ne 1 ]]; then
  die "--path 模式当前只支持一个 commit/ref"
fi

COMMIT_SHAS=()
COMMIT_SUBJECTS=()
for commit_ref in "${COMMITS[@]}"; do
  commit_sha="$(resolve_commit_ref "$SOURCE_BRANCH" "$commit_ref")"
  commit_subject="$(git -C "$REPO_ROOT" show -s --format=%s "$commit_sha")"
  COMMIT_SHAS+=("$commit_sha")
  COMMIT_SUBJECTS+=("$commit_subject")
done

last_index=$((${#COMMIT_SHAS[@]} - 1))
last_sha="${COMMIT_SHAS[$last_index]}"
last_subject="${COMMIT_SUBJECTS[$last_index]}"
SOURCE_SNAPSHOT="$last_sha"

if [[ -z "$SUBMIT_BRANCH" ]]; then
  sanitized_source_branch="$(printf '%s' "$SOURCE_BRANCH" | sed 's/[^A-Za-z0-9._-]/-/g')"
  SUBMIT_BRANCH="${sanitized_source_branch}-${BASE_BRANCH}-submit-${last_sha:0:8}"
fi

if [[ -n "$BODY_FILE" ]]; then
  [[ -f "$BODY_FILE" ]] || die "body 文件不存在: $BODY_FILE"
fi

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$SUBMIT_BRANCH"; then
  LOCAL_BRANCH_EXISTS=1
fi

if git -C "$REPO_ROOT" ls-remote --exit-code --heads "$REMOTE" "$SUBMIT_BRANCH" >/dev/null 2>&1; then
  REMOTE_BRANCH_EXISTS=1
fi

if [[ "$REUSE_BRANCH" != 1 && "$LOCAL_BRANCH_EXISTS" == 1 ]]; then
  die "本地分支已存在: $SUBMIT_BRANCH"
fi

if [[ "$REUSE_BRANCH" != 1 && "$REMOTE_BRANCH_EXISTS" == 1 ]]; then
  die "远端分支已存在: $SUBMIT_BRANCH"
fi

pr_title="$last_subject"
if [[ -n "$TITLE_OVERRIDE" ]]; then
  pr_title="$TITLE_OVERRIDE"
fi
[[ "$pr_title" =~ [^[:space:]] ]] || die "PR 标题不能为空"

if [[ -n "$BODY_FILE" ]]; then
  pr_body="$(cat "$BODY_FILE")"
else
  pr_body="$(build_default_pr_body)"
fi

log "source branch: $SOURCE_BRANCH"
log "base branch: $BASE_BRANCH"
log "submit branch: $SUBMIT_BRANCH"
if [[ ${#PATHS[@]} -gt 0 ]]; then
  log "mode: path-copy"
  log "source snapshot: ${SOURCE_SNAPSHOT:0:8}"
  for path in "${PATHS[@]}"; do
    log "  - path: ${path}"
  done
else
  log "commits:"
  for i in "${!COMMIT_SHAS[@]}"; do
    log "  - ${COMMIT_SHAS[$i]:0:8} ${COMMIT_SUBJECTS[$i]}"
  done
fi

WORKTREE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/submit-pr-XXXXXX")"

log "fetch ${REMOTE}/${BASE_BRANCH}"
git -C "$REPO_ROOT" fetch "$REMOTE" "$BASE_BRANCH"

log "create temporary worktree: $WORKTREE_DIR"
git -C "$REPO_ROOT" worktree add --detach "$WORKTREE_DIR" "${REMOTE}/${BASE_BRANCH}" >/dev/null
if [[ "$REUSE_BRANCH" == 1 ]]; then
  git -C "$WORKTREE_DIR" switch -C "$SUBMIT_BRANCH" >/dev/null
else
  git -C "$WORKTREE_DIR" switch -c "$SUBMIT_BRANCH" >/dev/null
fi

if [[ ${#PATHS[@]} -gt 0 ]]; then
  log "apply paths from ${SOURCE_SNAPSHOT:0:8}"
  apply_paths_from_ref "$SOURCE_SNAPSHOT"
  if git -C "$WORKTREE_DIR" diff --cached --quiet -- "${PATHS[@]}"; then
    die "选中的路径在 base 上没有变化, 无需提交"
  fi
  git -C "$WORKTREE_DIR" commit -m "$pr_title" >/dev/null
else
  log "cherry-pick commits"
  set +e
  git -C "$WORKTREE_DIR" cherry-pick "${COMMIT_SHAS[@]}"
  cherry_pick_status=$?
  set -e

  if [[ $cherry_pick_status -ne 0 ]]; then
    log "cherry-pick 失败, 请在临时 worktree 手动处理冲突后继续"
    log "continue: git -C $WORKTREE_DIR status"
    log "continue: git -C $WORKTREE_DIR cherry-pick --continue"
    exit $cherry_pick_status
  fi
fi

if [[ "$DRY_RUN" == 1 ]]; then
  DELETE_LOCAL_BRANCH=1
  KEEP_WORKTREE=0
  log "dry-run 完成, 未 push, 未创建 PR"
  exit 0
fi

log "push submit branch"
if [[ "$REUSE_BRANCH" == 1 ]]; then
  git -C "$WORKTREE_DIR" push --force-with-lease "$REMOTE" "${SUBMIT_BRANCH}:${SUBMIT_BRANCH}"
else
  git -C "$WORKTREE_DIR" push "$REMOTE" "${SUBMIT_BRANCH}:${SUBMIT_BRANCH}"
fi

remote_url="$(git -C "$REPO_ROOT" remote get-url "$REMOTE")"
mapfile -t remote_info < <(parse_remote_info "$remote_url")
remote_host="${remote_info[0]}"
repo_path="${remote_info[1]}"
api_base="https://api.${remote_host}"
token="$(get_credential_token "$remote_host")"

payload="$(build_pr_payload "$BASE_BRANCH" "$SUBMIT_BRANCH" "$repo_path" "$pr_title" "$pr_body")"
response_file="$(mktemp)"
trap 'rm -f "$response_file"; cleanup' EXIT

if [[ -n "$UPDATE_PR" ]]; then
  log "update PR #${UPDATE_PR}"
  http_code="$(
    curl -sS -o "$response_file" -w '%{http_code}' -X PATCH "${api_base}/${repo_path}/-/pulls/${UPDATE_PR}" \
      -H 'Accept: application/vnd.cnb.api+json' \
      -H "Authorization: Bearer ${token}" \
      -H 'Content-Type: application/json' \
      -d "$payload"
  )"
  response="$(cat "$response_file")"

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    die "PR 更新失败, HTTP ${http_code}: ${response}"
  fi

  pr_number="$UPDATE_PR"
  KEEP_WORKTREE=0
  pr_url="https://cnb.cool/${repo_path}/-/pulls/${pr_number}"
  log "PR updated: $pr_url"
  exit 0
fi

log "create PR"
http_code="$(
  curl -sS -o "$response_file" -w '%{http_code}' -X POST "${api_base}/${repo_path}/-/pulls" \
    -H 'Accept: application/vnd.cnb.api+json' \
    -H "Authorization: Bearer ${token}" \
    -H 'Content-Type: application/json' \
    -d "$payload"
)"
response="$(cat "$response_file")"

if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
  die "PR 创建失败, HTTP ${http_code}: ${response}"
fi

pr_number="$(printf '%s' "$response" | extract_pr_number)"
[[ -n "$pr_number" ]] || die "PR 创建成功但未解析到编号, 响应: ${response}"

KEEP_WORKTREE=0
pr_url="https://cnb.cool/${repo_path}/-/pulls/${pr_number}"
log "PR created: $pr_url"
