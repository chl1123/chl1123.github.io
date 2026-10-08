# RBK HTTP API and Documentation MCP

## Source of Truth

The `seer_spg_http_api_docs` MCP exposes an OpenAPI document without a `servers` entry. Determine the target base URL from the running robot configuration. This environment has used `http://127.0.0.1:8081`; treat that as an observed default, not a universal constant.

Use the MCP in this order:

1. Call `read_project_oas_gandze` to list paths and the spec download timestamp.
2. Select the required `$ref` values, such as `/paths/_navigate.json`.
3. Call `read_project_oas_ref_r_f7d7a1b846c1` with those exact paths.
4. Call `refresh_project_oas_gandze` first when current behavior or RBK version may be newer than the cached spec.

Relevant refs:

- `/paths/_getSpecifiedFieldsAIO.json`
- `/paths/_getTaskStatusByIds.json`
- `/paths/_navigate.json`
- `/paths/_cancelNavigate.json`
- `/paths/_setGoodsContainer.json`

For TCP/IP message-number to HTTP endpoint mapping, also consult the maintained
[multi-protocol API table](https://seer-group.feishu.cn/wiki/UYCWw4MP2iMhXek5Uj1c8QSanOe),
sheet `多协议API`. Relevant verified mappings include:

| TCP/IP number | HTTP endpoint | Meaning |
| --- | --- | --- |
| 1100 | `/getSpecifiedFieldsAIO` | Query batched robot fields |
| 1110 | `/getTaskStatusByIds` | Query task status by exact IDs |
| 3003 | `/cancelNavigate` | Cancel current navigation |
| 3051 | `/navigate` | Path navigation |
| 3066 | `/multiPathNavigate` | Specified-path, multi-segment navigation |

Do not submit a 3066 `moveTaskList` payload through `/navigate`. Use
`/multiPathNavigate`; the two endpoints have different task semantics even when
some payload fields overlap.

Always validate both HTTP status and JSON `retCode`; HTTP 200 alone does not establish success.

## Read Navigation and Container State

```bash
curl -sS --max-time 4 \
  'http://127.0.0.1:8081/getSpecifiedFieldsAIO?includedFields=navigation'
```

Depending on the gateway/version, the payload may expose `navigation` at the root or under `data`. Normalize both. `moveStatusInfo` is itself a JSON-encoded string and must be parsed as JSON, not searched with string slicing.

```bash
curl -sS --max-time 4 \
  'http://127.0.0.1:8081/getSpecifiedFieldsAIO?includedFields=navigation' |
jq -c '
  (.data.navigation // .navigation) as $nav |
  ($nav.moveStatusInfo | fromjson) as $move |
  {taskId:$nav.taskId, taskStatus:$nav.taskStatus,
   runningStatus:$nav.runningStatus, containers:$move.containers,
   objectFile:$move.objectFile}'
```

Navigation task status values documented by `/getTaskStatusByIds` are:

- `0`: none
- `1`: waiting
- `2`: running
- `3`: suspended
- `4`: completed
- `5`: failed
- `6`: canceled
- `7`: overtime
- `404`: not found

Use repeated `taskIds` query parameters when querying multiple task IDs, subject to the current spec.

## Submit a Stage-3 Script Task

The script path is relative to `/opt/.data/rbk/resources/scripts/`.

```bash
curl -sS --max-time 5 -X POST http://127.0.0.1:8081/navigate \
  -H 'Content-Type: application/json' \
  -d '{
    "id":"SELF_POSITION",
    "sourceId":"SELF_POSITION",
    "taskId":"debug-example-unique-id",
    "skillName":"Action",
    "script":{
      "name":"tasks/v3/standard/module/example.py",
      "args":{"operation":"example"},
      "stage":3
    },
    "scriptStage":3
  }'
```

Use a unique task ID and retain the exact payload. Existing tests such as `tests/fork_flow.py` and `tests/actions_flow.py` already implement robust submission and polling; prefer them over ad hoc loops.

## Cancel Without Killing the Script

```bash
curl -sS --max-time 4 -X POST \
  http://127.0.0.1:8081/cancelNavigate \
  -H 'Content-Type: application/json' -d '{}'
```

Cancel only when a task is active or cleanup is needed. Query terminal state afterward.

## Container Mutation

The current MCP schema requires `type`, `containerId`, `goodsName`, and `desc`. It documents `type=bind`. RBK 3.5.4.0054 was also observed accepting `type=unbind`, but that behavior is not described by the cached schema; refresh and verify before relying on it.

```bash
curl -sS --max-time 4 -X POST \
  http://127.0.0.1:8081/setGoodsContainer \
  -H 'Content-Type: application/json' \
  -d '{"type":"bind","containerId":"0","goodsName":"test","desc":""}'
```

Do not use container mutation to conceal a script lifecycle defect. Record state before and after, and label any mutation used solely to reset a test fixture.
