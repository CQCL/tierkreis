cmake_minimum_required(VERSION 3.10)
project(tkr_mpi_workers CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find MPI package
find_package(MPI REQUIRED)

# Add an include directory for the json library
include_directories(.)

# Add the executable
add_executable(tkr_mpi_worker main.cpp)
target_link_libraries(tkr_mpi_worker PRIVATE MPI::MPI_CXX)
target_include_directories(tkr_mpi_worker PRIVATE ${MPI_CXX_INCLUDE_PATH})

# A message to show where the executable will be
message(STATUS "Executable will be created at ${CMAKE_BINARY_DIR}/mpi_cli")
