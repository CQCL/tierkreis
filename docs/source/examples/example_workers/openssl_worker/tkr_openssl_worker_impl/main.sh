#!/usr/bin/env bash
set -euo pipefail

worker_args=${1:?Expected the Tierkreis worker call definition path}
function_name=$(jq -r '.function_name' "$worker_args")
if [[ $function_name != "genrsa" ]]; then
    echo "Unknown task: $function_name" >&2
    exit 1
fi

numbits_file=$(jq -r '.inputs.numbits' "$worker_args")
passphrase_file=$(jq -r '.inputs.passphrase' "$worker_args")
private_key_file=$(jq -r '.outputs.private_key' "$worker_args")
public_key_file=$(jq -r '.outputs.public_key' "$worker_args")
numbits=$(<"$numbits_file")

openssl genrsa -out "$private_key_file" -aes128 -passout "file:$passphrase_file" "$numbits"
openssl rsa -in "$private_key_file" -passin "file:$passphrase_file" -pubout -out "$public_key_file"
