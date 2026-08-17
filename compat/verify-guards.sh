#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly work_dir="$(mktemp -d)"
trap 'rm -rf "${work_dir}"' EXIT

# Prefer a live local Oracle image (CI rebuild alias) when present. Historical
# launcher digests are capture pins and may not exist on the runner.
oracle_image="${FERRICOV_ORACLE_IMAGE:-}"
if [[ -z "${oracle_image}" ]]; then
  if docker image inspect ferricov/lcov-oracle:v2.5 >/dev/null 2>&1; then
    oracle_image="$(docker image inspect --format '{{.Id}}' ferricov/lcov-oracle:v2.5)"
  else
    oracle_image="$(jq -r '.runtime.image' "${root_dir}/compat/launchers/lcov-v2.5-oracle.json")"
  fi
fi

write_launcher() {
  local src="$1"
  local dst="$2"
  jq --arg image "${oracle_image}" '
    .runtime.image = $image
    | .environment.image = $image
  ' "${src}" >"${dst}"
}

write_launcher \
  "${root_dir}/compat/launchers/lcov-v2.5-oracle.json" \
  "${work_dir}/oracle.json"
write_launcher \
  "${root_dir}/compat/launchers/different-oracle.json" \
  "${work_dir}/different-oracle.json"

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
  "${work_dir}/oracle.json" \
  >"${work_dir}/renamed-oracle.json"
jq '.evidence_scope = "compatibility"' \
  "${root_dir}/compat/cases/harness-self-test.json" \
  >"${work_dir}/compatibility-self-identity.json"

expect_rejected \
  'compatibility evidence cannot compare identical runtime identity' \
  cargo run --locked -p ferricov-oracle --bin differential -- \
    "${work_dir}/compatibility-self-identity.json" \
    "${work_dir}/oracle.json" \
    "${work_dir}/renamed-oracle.json" \
    "${work_dir}/self-identity-results"

jq '.cases += [(.cases[0] | .arguments = ["--ferricov-unknown-option"])]' \
  "${root_dir}/compat/cases/harness-reverse-test.json" \
  >"${work_dir}/duplicate-case-id.json"

expect_rejected \
  'duplicate case ID: lcov-version-must-fail' \
  cargo run --locked -p ferricov-oracle --bin differential -- \
    "${work_dir}/duplicate-case-id.json" \
    "${work_dir}/oracle.json" \
    "${work_dir}/different-oracle.json" \
    "${work_dir}/duplicate-case-results"
