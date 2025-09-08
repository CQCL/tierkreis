#!/usr/bin/env bash

# Boilerplate for reading WorkerCallArgs in Bash.

worker_call_args_file=$1

echo "START openssl_worker $worker_call_args_file"
echo $(jq "." $worker_call_args_file)

function_name=$(jq -r ".function_name" $worker_call_args_file)
done_path=$(jq -r ".done_path" $worker_call_args_file)
error_path=$(jq -r ".error_path" $worker_call_args_file)
logs_path=$(jq -r ".logs_path" $worker_call_args_file)
output_dir=$(jq -r ".output_dir" $worker_call_args_file)

while read key ; do
    declare "input_${key}_file"="$(jq -r ".inputs.$key" $worker_call_args_file)"
done < <(jq -r '.inputs|keys[]' $worker_call_args_file)

while read key ; do
    declare "output_${key}_file"="$(jq -r ".outputs.$key" $worker_call_args_file)"
done < <(jq -r '.outputs|keys[]' $worker_call_args_file)
