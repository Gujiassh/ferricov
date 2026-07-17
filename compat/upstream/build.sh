#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly image="ferricov/lcov-oracle:v2.5"

docker build --tag "${image}" "${root_dir}/compat/upstream"
for command in \
  lcov genhtml geninfo genpng gendesc perl2lcov py2lcov xml2lcov \
  xml2lcovutil.py llvm2lcov
do
  output="$(docker run --rm --network none "${image}" "${command}" --help)"
  if [[ "${command}" != "xml2lcovutil.py" && -z "${output}" ]]; then
    printf 'installed command produced empty help: %s\n' "${command}" >&2
    exit 1
  fi
done

docker run --rm --network none --entrypoint sh "${image}" -c '
  test "$(stat -c "%a" /usr/local/bin/xml2lcovutil.py)" = 755
  test "$(lcov --version)" = "lcov: LCOV version 2.5-beta"
  test "$(genhtml --version)" = "genhtml: LCOV version 2.5-beta"
  test "$(geninfo --version)" = "geninfo: LCOV version 2.5-beta"
'
