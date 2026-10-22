# Logging, errors, and restarting workflows

## Static errors

The graph builder's `TKR` types let a Python type checker catch incompatible
edges before expensive work is submitted. Runtime errors can still occur when
a worker raises an exception, exits unsuccessfully, or returns invalid data.

## Runtime diagnostics

`wait_for` raises `ValueError` when a workflow attempt fails. The exception
includes related diagnostics for the failed node. The run remains available
for inspection:

```python
try:
    await runtime.wait_for(run_id)
except ValueError as error:
    print(error)
    summary = await runtime.get_summary(run_id)
    print(summary.errored_locations)
```

`get_summary(run_id, attempt)` reports timestamps, duration, and errored
locations. For lower-level debugging,
`debug_read_node_states(run_id, attempt, locations)` returns the state, task
name, and execution context for the requested location strings.

Set `-v` on `tkr run`, or call `config.set_log_level("debug")` before
`new_from_config(config)`, to enable runtime debug logging. Worker logs remain
owned by the selected executor or remote service.

## Restarting failed or selected work

Restarting creates a new attempt and leaves the source attempt unchanged. With
no locations, every errored node is restarted. Supplying locations restarts
those nodes and transitively invalidates their dependent results:

```python
new_attempt, invalidated = await runtime.restart_task(run_id)
await runtime.wait_for(run_id, new_attempt)
outputs = await runtime.get_outputs(run_id, new_attempt)
```

```python
new_attempt, invalidated = await runtime.restart_task(run_id, ["N3"])
```

Locations may identify nodes nested inside Eval, Loop, or Map. Their containing
nodes are partially invalidated as needed, while unaffected work is reused.
See the [restart example](../examples/restart.ipynb) for a complete workflow.

## Recovering after the runtime stops

With persistent SQLite state, starting another runtime over the same
configuration recovers active runs and resumes orchestration. Keep the same
state database, asset storage, and worker configuration. This process recovery
is distinct from `restart_task`: recovery continues the current attempt,
whereas a task restart creates a new attempt after a failure or manual choice.

## Current limitations

The Rust runtime does not currently implement graph breakpoints or the legacy
interactive `debug_graph` helper. Use run summaries, node states, executor
logs, and targeted restarts instead.
