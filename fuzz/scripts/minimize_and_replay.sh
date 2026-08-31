#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 TARGET CASE_ID RAW_ARTIFACT" >&2
  exit 2
fi
target=$1
case_id=$2
raw=$3
test -f "$raw"
out="${raw}.minimized"
seed="$(python3 fuzz/scripts/validate_artifacts.py --seed-for "$target" --case-id "$case_id")"
common=(-seed="$seed" -timeout=2 -rss_limit_mb=512 -max_len=1048576)

# tmin must reproduce the finding under the same resource and deterministic
# seed envelope as CI. The final command is a plain one-run replay, so the
# retained result is not accepted solely on minimizer instrumentation.
timeout --signal=KILL 60s cargo +nightly fuzz tmin "$target" "$raw" \
  --output "$out" -- "${common[@]}"
timeout --signal=KILL 60s cargo +nightly fuzz run "$target" "$out" -- \
  "${common[@]}" -runs=1

sha256sum "$raw" "$out"
echo "Retain the raw input as CASE.raw, the minimized input as CASE.minimized, and CASE.minimized.json with both hashes conforming to fuzz/failure-sidecar.schema.json"
