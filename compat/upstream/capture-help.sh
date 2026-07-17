#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly image="ferricov/lcov-oracle:v2.5"
readonly output_dir="${root_dir}/compat/upstream/help"
readonly commands=(
  lcov genhtml geninfo genpng gendesc perl2lcov py2lcov xml2lcov
  xml2lcovutil.py llvm2lcov
)

mkdir -p "${output_dir}"
for command in "${commands[@]}"; do
  docker run --rm --network none "${image}" "${command}" --help \
    >"${output_dir}/${command}.txt"
done
