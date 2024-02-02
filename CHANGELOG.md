# Changelog

## [0.4.0](https://github.com/CQCL/guppy/compare/v0.1.0...v0.2.0) (2024-02-01)


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