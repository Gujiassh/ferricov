#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

expect_rejected() {
  local expected="$1"
  shift
  local log="${work_dir}/guard.log"
  if "$@" >"${log}" 2>&1; then
    printf 'guard unexpectedly passed: %s\n' "${expected}" >&2
    exit 1
  fi
  if ! grep -F -- "${expected}" "${log}" >/dev/null; then
    cat "${log}" >&2
    printf 'guard failed without expected reason: %s\n' "${expected}" >&2
    exit 1
  fi
  printf 'GUARD_OK reason=%s\n' "${expected}"
}

jq '.name = "renamed-lcov-v2.5-oracle"' \
  "${root_dir}/compat/launchers/lcov-v2.5-oracle.json" \
  >"${work_dir}/renamed-oracle.json"
jq '.evidence_scope = "compatibility"' \
  "${root_dir}/compat/cases/harness-self-test.json" \
  >"${work_dir}/compatibility-self-identity.json"

expect_rejected \
  'compatibility evidence cannot compare identical runtime identity' \
  cargo run --locked -p ferricov-oracle --bin differential -- \
    "${work_dir}/compatibility-self-identity.json" \
    "${root_dir}/compat/launchers/lcov-v2.5-oracle.json" \
    "${work_dir}/renamed-oracle.json" \
    "${work_dir}/self-identity-results"

jq '.cases += [(.cases[0] | .arguments = ["--ferricov-unknown-option"])]' \
  "${root_dir}/compat/cases/harness-reverse-test.json" \
  >"${work_dir}/duplicate-case-id.json"

expect_rejected \
  'duplicate case ID: lcov-version-must-fail' \
  cargo run --locked -p ferricov-oracle --bin differential -- \
    "${work_dir}/duplicate-case-id.json" \
    "${root_dir}/compat/launchers/lcov-v2.5-oracle.json" \
    "${root_dir}/compat/launchers/different-oracle.json" \
    "${work_dir}/duplicate-case-results"
