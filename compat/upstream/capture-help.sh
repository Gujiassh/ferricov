#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly image="${ORACLE_IMAGE:-ferricov/lcov-oracle:v2.5}"
readonly docker_image_id="$(docker image inspect --format '{{.Id}}' "${image}")"
readonly output_dir="${root_dir}/compat/upstream/help"
readonly commands=(
  lcov genhtml geninfo genpng gendesc perl2lcov py2lcov xml2lcov
  xml2lcovutil.py llvm2lcov
)

mkdir -p "${output_dir}"
for command in "${commands[@]}"; do
  docker run --rm --network none "${docker_image_id}" "${command}" --help \
    >"${output_dir}/${command}.txt"
done
