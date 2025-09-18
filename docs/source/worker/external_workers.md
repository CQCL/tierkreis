# External Workers

Tierkreis does not put any restrictions on workers except the general [contract](../executors/overview.md).
This means that you can also write workers in your preferred language and interface it with Tierkreis.
To use the worker in tierkreis you can do two things:

- Describe the interface using a subset of [TypeSpec](https://typespec.io) to generate stubs for your worker
- Define an executor, although for most cases if you can run your code as a commandline script, the [ShellWorker](../executors/shell.md) should be sufficient.

For full example without stubs you can have a look at the `signing_graph.py` exmaple.

## IDL

A TypeSpec defines the inputs and outputs of the tasks in your workers.
Tierkreis is restricted to a subset of the full specification:

- Interfaces: defining the available tasks in your worker
- Models: to define the types of the task in- and outputs
  Additionally, you may use the `@portmapping` decorator on models to indicate tasks with multiple outputs.

For example you could define the following interface in `namespace.tsp`

```tsp
@portmapping
model Person {
  name: string;
  age: uint8;
}

model Dog{
  name: string;
  color: string;
}

@portmapping
model Creature<T> {
  name: string;
  t: T;
}
interface TestNamespace {
  foo(age: integer, name: string): Person;
  bar(): Dog;
  baz<T>(c: Creature<T>): Creatur<T>;
}
```

From which you could generate stubs.
This is currently only available through a python script:

```py
# /// script
# requires-python = ">=3.12"
# dependencies = ["tierkreis"]
# ///

import logging
from pathlib import Path
import shutil
import subprocess
from tierkreis.codegen import format_namespace, Namespace


def write_stubs(namespace: Namespace, stubs_path: Path) -> None:
    with open(stubs_path, "w+") as fh:
        fh.write(format_namespace(namespace))

    ruff_binary = shutil.which("ruff")
    if ruff_binary:
        subprocess.run([ruff_binary, "format", stubs_path])
        subprocess.run([ruff_binary, "check", "--fix", stubs_path])
    else:
        logging.warning("No ruff binary found. Stubs will contain raw codegen.")


if __name__ == "__main__":
    namespace = Namespace.from_spec_file(
        Path("<path to your spec file>")
    )
    write_stubs(namespace, Path("<path to the generated stubs>"))
```

## Parsing Inputs and Outputs

There are two possible scenarios to parse input and outputs for workers.
You can either define a custom executor in python; this has the advantage of interacting with the storage from Tierkreis, making it simpler to read inputs.
But you also have to make sure the outputs are written to the correct places.
Alternatively you can use an existing executor, which means you have to do the parsing inside the worker.
Tierkreis typically hands over a single argument to the invoked script: the `NodeCallArgs`
This contains all the information specified in the the contract of a worker.
Parsing this file will provide the locations of inputs and expected outputs.

### C++ Example

This example shows how to parse the following interface:

```tsp

interface MyWorker {
    double(value: Array<integer>): Array<integer>;
}
```

using [nlohmann/json](https://github.com/nlohmann/json).

```cpp
void parse_json(const std::string &call_args_path, json &call_args)
{
  std::ifstream call_args_file(call_args_path);
  if (!call_args_file.is_open()) // check if open is necessary for << syntax
  {
    std::cerr << "Error: Could not open configuration file: " << call_args_path << std::endl;
    MPI_Abort(MPI_COMM_WORLD, 1);
    return;
  }
  try
  {
    call_args = json::parse(call_args_file);
  }
  catch (json::parse_error &e)
  {
    std::cerr << "Error: JSON parsing failed: " << e.what() << std::endl;
    MPI_Abort(MPI_COMM_WORLD, 1);
    return;
  }
  call_args_file.close();
}

void parse_input(const json &call_args, std::vector<int> &input_data)
{
  json inputs = call_args["inputs"];
  std::cout << inputs << std::endl;
  for (auto &[key, path] : inputs.items())
  {
    if (key != "value")
      continue; // we only want to load value

    auto abs_path = CHECKPOINTS_DIRECTORY + path.template get<std::string>();
    std::cout << "parsing input: " << key << " at: " << abs_path << std::endl;
    json data;
    parse_json(abs_path, data);
    std::cout << "Read data" << data << std::endl;
    auto tmp = data.template get<std::string>();
    std::vector<int> ret = json::parse(tmp);
    input_data.resize(ret.size());
    std::copy(ret.begin(), ret.end(), input_data.begin());
  }
}

void write_output(const json &call_args, const std::vector<int> &gathered_data)
{

  json outputs = call_args["outputs"];
  for (auto &[key, path] : outputs.items())
  {
    if (key != "value")
      continue; // we only want to write value
    std::cout << "writing output: " << key << " at: " << path << std::endl;
    auto out_path = CHECKPOINTS_DIRECTORY + path.template get<std::string>();
    std::ofstream output_file(out_path);
    if (!output_file.is_open())
    {
      std::cerr << "Error: Could not open output file for writing: " << out_path << std::endl;
      MPI_Abort(MPI_COMM_WORLD, 1);
      return;
    }
    json data = gathered_data;
    output_file << data << std::endl;
    output_file.close();
  }

  auto done_file_path = CHECKPOINTS_DIRECTORY + call_args["done_path"].template get<std::string>();
  std::ofstream done_file(done_file_path);
  if (done_file.is_open())
  {
    done_file.close();
  }
  else
  {
    std::cerr << "Error: Could not create done file at " << done_file_path << std::endl;
  }
}
```

```

```
