# RBK Script Debugging

## Separate Platform Health from Script Health

Before editing Python, query robot status and inspect startup logs.

Known platform-state indicators:

- `ss@pyCrashed`: sticky script-system failure. It generally cannot be cleared through the normal abnormal-clear flow; coordinate an RBK restart.
- `walk motor number is not 2 or 4!!!{1}`, `modelName=unknown`, `motorInfo=[]`: RBK or the model has not fully initialized, or residual processes are serving incomplete state. Do not diagnose motor code from this state.
- A motor that moves through manual position commands while a script does not move it usually points to command lifecycle, configuration, or script logic rather than an RBK motor fault.

Do not restart RBK casually. Record current task/error state and explain why a restart is required.

## Repository and Import Discipline

- Read repository `AGENTS.md` and `CLAUDE.md` first.
- Migrate old SDK scripts only through APIs already present in the current repository.
- In standard fork modules, import the base and helpers through the same namespace, for example `standard.fork` and `standard.fork_utils`. Mixing `standard.fork_utils` with `tasks.v3.standard.fork_utils` can load two Python module objects: the base binds runtime config in one while an action reads `_CONFIG` from the other, causing `RuntimeError: fork utils runtime is not initialized`.
- Instantiate the `Fork` subclass before running tasks. Its constructor calls `_initialize_fork_script`, which binds `fork_utils` to `ConfigParams` before actions use `_config()`.
- Do not instantiate runtime-dependent actions at module import time before that initialization.

This installation resolves `/opt/.data/rbk/resources/scripts` to `/mnt/log/3.5/rbk/resources/scripts`, while `syspy.utils.SCRIPTS_DIR` is hard-coded to the `/opt` spelling. If `python -m unittest` fails during import with `script path error`, execute the test file by its absolute `/opt/.data/...` path instead:

```bash
sudo env PYTHONPATH=/opt/.data/rbk/resources/scripts \
  python3 /opt/.data/rbk/resources/scripts/tests/test_example.py TestClass.test_name
```

## Motor Command Lifecycle

For position-controlled motors:

1. Resolve and validate the model motor key and configured speed limits.
2. Call `Motor.resetMotor(name)` to clear stale command state.
3. Call `Motor.setMotorPosition(name, target, speed, stop_di)` and check its return value.
4. Only after a successful command, poll `Motor.isMotorReached(name)` and/or an explicit position tolerance.
5. Reset the motor promptly on finish, command rejection, timeout, failure, or cancellation. Make reset idempotent when multiple terminal paths can run.

For coupled motors, issue both commands in one action lifecycle, compare their positions against a synchronization tolerance, and reset both together. Never let `isMotorReached` from an earlier command satisfy a new action.

## Fork and Container Lifecycle

For symptom → channel routing and the fork channel map (load/unload, fork motor, policy,
recognition), see [fork-channels.md](fork-channels.md).

Treat two concepts separately:

- `Container`: logical cargo ownership and persisted load/unload state.
- Navigation goods shape: collision/planning geometry associated with cargo.

On successful load completion:

1. Set the goods shape.
2. Bind the logical container with `Container.bindContainer`.

On successful unload completion:

1. Unbind through the module/container lifecycle (`self.unbindContainer(...)` where available).
2. Let the container implementation clear the goods shape when no containers remain loaded.

Use `Container.hasGoods("0")` for load/unload preconditions, loaded speed limits, and cargo DI decisions. Capture `Navigation.hasGoods()` only as a separate diagnostic signal. They can disagree in either direction and can change asynchronously; never derive one from the other in a test report.

A specific contradictory state to recognize: `Navigation.hasGoods()=True` together with
`Container.hasGoods("0")=False` and an empty `Container.getContainers()`. Seen in
simulation after an aborted task. `load` cases then fail in ~0.2 s with
`hasGoods True->True`. **Reproduce on the unmodified revision before attributing it to a
code change** — the failure signature is identical.

When comparing them, record values before submission, during the task, at terminal state, and after a short bounded settle window. A mismatch may be an RBK consistency defect, but first rule out that the script updates only one lifecycle.

## Reproduction and Cleanup

- Prefer JSON-driven tests under `tests/` and model-specific cases over manual RPC snippets.
- Give every submission a timestamped unique task ID.
- Capture test stdout and a JSON report.
- Poll for the submitted task ID; stale global terminal state can otherwise produce a false result.
- Use HTTP `/cancelNavigate` for timeouts or interruption. Do not kill the persistent script process.
- If temporarily restoring old behavior to reproduce a regression, record the exact diff, reproduce, collect logs, then restore the fixed behavior before validation.
- Report skipped and failed rounds honestly. A defect that blocks the second half of a load/unload cycle is still a reproduced round, not a passing cycle.

Example Type E fork flow:

```bash
sudo env PYTHONPATH=/opt/.data/rbk/resources/scripts \
  python3 /opt/.data/rbk/resources/scripts/tests/fork_flow.py \
  --case type_e_load_lift_no_target \
  --case type_e_unload_lift_no_target \
  --script tasks/v3/standard/module/robotTypeE.py \
  --report-path /tmp/type_e_fork_flow.json
```

Finish with `py_compile`, `git diff --check`, targeted unit tests, current HTTP state, and a check for active exec sessions.
