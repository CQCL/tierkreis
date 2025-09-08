#!/usr/bin/env bash

## To test run ./main.sh ./test/args

worker_call_args_file=$1

echo "START openssl_worker $worker_call_args_file"
echo $(jq "." $worker_call_args_file)

function_name=$(jq -r ".function_name" $worker_call_args_file)
done_path=$(jq -r ".done_path" $worker_call_args_file)
logs_path=$(jq -r ".logs_path" $worker_call_args_file)
output_dir=$(jq -r ".output_dir" $worker_call_args_file)

while read key ; do
    declare "input_${key}_file"="$(jq -r ".inputs.$key" $worker_call_args_file)"
done < <(jq -r '.inputs|keys[]' $worker_call_args_file)

while read key ; do
    declare "output_${key}_file"="$(jq -r ".outputs.$key" $worker_call_args_file)"
done < <(jq -r '.outputs|keys[]' $worker_call_args_file)

# numbits_file=$(jq -r ".inputs.numbits" $worker_call_args_file)
# numbits=$(jq -r "." $numbits_file)

# private_key_file=$(jq -r ".outputs.private_key" $worker_call_args_file)
# public_key_file=$(jq -r ".outputs.public_key" $worker_call_args_file)

# mkdir -p $output_dir
# touch $private_key_file
# touch $public_key_file
