#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <numeric>
#include <nlohmann/json.hpp>
#include <mpi.h>

static const std::string CHECKPOINTS_DIRECTORY = std::string(std::getenv("HOME")) + "/.tierkreis/checkpoints/";

// Use the nlohmann namespace for JSON parsing
using json = nlohmann::json;

void print_usage(const char *prog_name)
{
  std::cout << "Usage: " << prog_name << " <path_to_config.json>" << std::endl;
}

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

void parse_input(const json &call_args, std::vector<int> &input_data, int world_size)
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
  if (input_data.size() < world_size)
  {
    // not all process will receive data
    return;
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

int main(int argc, char **argv)
{
  // init
  MPI_Init(&argc, &argv);

  int world_size;
  MPI_Comm_size(MPI_COMM_WORLD, &world_size);

  int world_rank;
  MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);

  json call_args;
  std::vector<int> input_data;
  // parse worker_call_args
  if (world_rank == 0)
  {
    if (argc != 2)
    {
      print_usage(argv[0]);
      MPI_Abort(MPI_COMM_WORLD, 1);
      return 1;
    }
    std::cout << "parsing json" << std::endl;
    parse_json(argv[1], call_args);
    std::cout << "parsing inputs" << std::endl;
    parse_input(call_args, input_data, world_size);
  }

  // Dummy program
  int total_elements = input_data.size();
  MPI_Bcast(&total_elements, 1, MPI_INT, 0, MPI_COMM_WORLD);
  int elements_per_proc = total_elements / world_size;
  std::vector<int> local_data(elements_per_proc);
  MPI_Scatter(input_data.data(), elements_per_proc, MPI_INT,
              local_data.data(), elements_per_proc, MPI_INT,
              0, MPI_COMM_WORLD);

  for (int &val : local_data)
  {
    val *= 2;
  }
  std::vector<int> gathered_data;
  if (world_rank == 0)
  {
    gathered_data.resize(elements_per_proc * world_size);
  }
  MPI_Gather(local_data.data(), elements_per_proc, MPI_INT,
             gathered_data.data(), elements_per_proc, MPI_INT,
             0, MPI_COMM_WORLD);

  // write to output
  if (world_rank == 0)
  {
    std::cout << "Writing outputs" << std::endl;
    write_output(call_args, gathered_data);
  }

  MPI_Finalize();
  return 0;
}
