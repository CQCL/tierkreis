# tierkreis

Quantum-classical hybrid workflow orchestration tool.
This is the top level repository containing the python packages.

## Packages
- **Tierkreis**: the core functionality `pip install tierkreis`
- **Tierkreis Visualization**: A simple web visualization tool for debugging workflows `pip install tierkreis-visualization`
- **Tierkreis Workers**: A collection of commonly used workers `pip install tkr-<name>-worker`
  - Qiskit Aer
  - Quantinuum Nexus
  - Quantinuum PyTKet


## CLI

Tierkreis comes with a command line interface for running workflows.
To see all available options use `tkr --help`.
To run the hello world example from the cli
```
uv run tkr -g examples/hello_world/hello_world_graph.py:hello_graph -i data.json --uv --registry-path examples/hello_world/ -o
```
Explanation:
* `-g` specifies the graph to run by specifying the location and function to run.
* `-i` specifies the input for the graph function. In this case it loads a json file from the project root with the contents `{"value": "world!"}`
* `--uv` enables the use of the UV executor.
* `--registry-path` specifies the location of the registry to use for the UV executor.
* `-o` enables output printing.



## Development
Requirements
- `uv` >= 0.4


See the justfile (requires `just`) for common development commands. For example:

```sh
just test
```

## License

This project is licensed under Apache License, Version 2.0 ([LICENSE][] or http://www.apache.org/licenses/LICENSE-2.0).


  [LICENSE]: https://github.com/CQCL/tierkreis/blob/main/LICENCE
