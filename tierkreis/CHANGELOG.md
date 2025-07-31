# Changelog


## [0.5.0] (2024-02-15)


### Features

* New `OpaqueModel` which derives from pydantic `BaseModel` to defer Tierkreis
  serialization to pydantic.
* New `TierkreisType.register_alternative` method to register
  Tierkreis-compatible alternatives to types to use for
  serialization/deserialization for arbitrary types.
* `UnpackRow` base dataclass for defining rows that should be unpacked in Tierkreis
  (e.g. multiple outputs in a worker function).

### Breaking changes

* Graph, Signature and Worker protos updated to v1alpha1 to add `FunctionNode`
  message to graph proto, with optional `retry_secs` field. Graphs serialized
  with v1alpha would deserialize as containing functions with empty names.
* `ServerRuntime` simplified to only offer `run_graph` for execution, all "task"
  related methods removed. `runtime.proto` updated to v1alpha1 to match.
* `TierkreisValue.from_python` uses python type to guide conversion - takes an
  optional annotation or uses `type(value)` as default.
  Subclasses of supported types will no longer converted as the supported super type.


## [0.4.1] (2024-02-07)


### Bug Fixes
* Fix bug in `val_known_tk_type` (assumed dataclass for all structures).
* Fix protobuf versioning
* Fix shebang in pytket worker


## [0.4.0] (2024-02-01)


### Features

* Support Pydantic `BaseModel` automated conversion to
  `StructType`/`StructValue`.
* `UnpackRow` base dataclass for defining rows that should be unpacked in Tierkreis
  (e.g. multiple outputs in a worker function).

### Breaking changes

* `TierkreisStruct` and `register_struct_convertible` are removed. Now automated
  conversion will be attempted on any dataclass or Pydantic `BaseModel`.
* `ServerRuntime` simplified to only offer `run_graph` for execution, all "task"
  related methods removed. `runtime.proto` updated to v1alpha1 to match.

### Minor changes

* `CircStruct` simplified to just contain the JSON string of a Pytket Circuit
  (essentially acts as an opaque newtype).