#!/usr/bin/env bash
set -euo pipefail

readonly root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly upstream_dir="${root_dir}/compat/upstream"
readonly source_root="${LCOV_SOURCE_ROOT:-${root_dir}/../lcov-upstream-reference}"
readonly build_network="${ORACLE_BUILD_NETWORK:-default}"
readonly build_inputs_lock="${upstream_dir}/build-inputs.lock"
readonly source_archive="${upstream_dir}/lcov-v2.5.tar.gz"
readonly intersphinx_inventory="${upstream_dir}/python-objects.inv"
readonly snapshot_ca_bundle="${upstream_dir}/snapshot-ca-certificates.crt"

lock_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "${build_inputs_lock}"
}

readonly source_date_epoch="$(lock_value source_date_epoch)"
readonly source_commit="$(lock_value lcov_source_commit)"
readonly source_tree="$(lock_value lcov_source_tree)"
readonly source_archive_sha256="$(lock_value lcov_source_archive_sha256)"
readonly source_archive_bytes="$(lock_value lcov_source_archive_bytes)"
readonly intersphinx_inventory_sha256="$(lock_value python_objects_inv_sha256)"
readonly intersphinx_inventory_bytes="$(lock_value python_objects_inv_bytes)"
readonly snapshot_ca_bundle_sha256="$(lock_value snapshot_ca_bundle_sha256)"
readonly snapshot_ca_bundle_bytes="$(lock_value snapshot_ca_bundle_bytes)"
readonly build_inputs_lock_sha256="$(sha256sum "${build_inputs_lock}" | cut -d' ' -f1)"
readonly build_id="${ORACLE_BUILD_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
readonly build_tag_a="ferricov/lcov-oracle:rebuild-${build_id}-a"
readonly build_tag_b="ferricov/lcov-oracle:rebuild-${build_id}-b"
readonly manifest="${ORACLE_MANIFEST:-/tmp/ferricov-oracle-${build_id}.json}"
readonly build_context="$(mktemp -d /tmp/ferricov-oracle-build.XXXXXX)"
readonly evidence_root="$(mktemp -d /tmp/ferricov-oracle-evidence.XXXXXX)"
readonly regenerated_archive="$(mktemp /tmp/ferricov-oracle-source.XXXXXX.tar.gz)"

cleanup() {
  rm -rf "${build_context}" "${evidence_root}" "${regenerated_archive}"
}
trap cleanup EXIT

if [[ "$(git -C "${source_root}" rev-parse HEAD)" != "${source_commit}" ]]; then
  printf 'LCOV source checkout is not at the pinned commit: %s\n' "${source_root}" >&2
  exit 1
fi
if [[ "$(git -C "${source_root}" rev-parse HEAD^{tree})" != "${source_tree}" ]]; then
  printf 'LCOV source checkout tree identity mismatch: %s\n' "${source_root}" >&2
  exit 1
fi
if [[ -n "$(git -C "${source_root}" status --porcelain --untracked-files=all)" ]]; then
  printf 'LCOV source checkout is dirty: %s\n' "${source_root}" >&2
  exit 1
fi
git -C "${source_root}" -c tar.umask=0022 archive \
  --format=tar --prefix=lcov-v2.5/ \
  "${source_commit}" \
  | gzip -n -9 >"${regenerated_archive}"
if ! cmp -s "${regenerated_archive}" "${source_archive}"; then
  printf 'committed source archive does not match the clean pinned checkout\n' >&2
  exit 1
fi

for path in \
  Dockerfile build-inputs.lock packages.lock packages.full.lock installed-tree.sh \
  installed-tree.lock lcov-v2.5.tar.gz python-objects.inv pin-intersphinx.py \
  snapshot-ca-certificates.crt
do
  cp "${upstream_dir}/${path}" "${build_context}/${path}"
done

test "$(sha256sum "${source_archive}" | cut -d' ' -f1)" = "${source_archive_sha256}"
test "$(stat -c '%s' "${source_archive}")" = "${source_archive_bytes}"
test "$(sha256sum "${intersphinx_inventory}" | cut -d' ' -f1)" = "${intersphinx_inventory_sha256}"
test "$(stat -c '%s' "${intersphinx_inventory}")" = "${intersphinx_inventory_bytes}"
test "$(sed -n '2p' "${intersphinx_inventory}")" = '# Project: Python'
test "$(sed -n '3p' "${intersphinx_inventory}")" = '# Version: 3.14'
test "$(sha256sum "${upstream_dir}/pin-intersphinx.py" | cut -d' ' -f1)" = \
  "$(lock_value pin_intersphinx_sha256)"
test "$(stat -c '%s' "${upstream_dir}/pin-intersphinx.py")" = \
  "$(lock_value pin_intersphinx_bytes)"
test "$(sha256sum "${snapshot_ca_bundle}" | cut -d' ' -f1)" = \
  "${snapshot_ca_bundle_sha256}"
test "$(stat -c '%s' "${snapshot_ca_bundle}")" = "${snapshot_ca_bundle_bytes}"

readonly archived_commit="$(gzip -dc "${source_archive}" | git get-tar-commit-id)"
if [[ "${archived_commit}" != "${source_commit}" ]]; then
  printf 'source archive commit mismatch: %s\n' "${archived_commit}" >&2
  exit 1
fi

do_build() {
  local tag="$1"
  docker build \
    --pull=false \
    --no-cache \
    --network "${build_network}" \
    --target oracle \
    --build-arg "SOURCE_DATE_EPOCH=${source_date_epoch}" \
    --build-arg "BUILD_INPUTS_LOCK_SHA256=${build_inputs_lock_sha256}" \
    --build-arg "SOURCE_ARCHIVE_SHA256=${source_archive_sha256}" \
    --build-arg "INTERSPHINX_INVENTORY_SHA256=${intersphinx_inventory_sha256}" \
    --build-arg "SNAPSHOT_CA_BUNDLE_SHA256=${snapshot_ca_bundle_sha256}" \
    --tag "${tag}" \
    "${build_context}"
}

image_id() {
  local tag="$1"
  local value
  value="$(docker image inspect --format '{{.Id}}' "${tag}")"
  if [[ ! "${value}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
    printf 'invalid Docker image ID for %s: %s\n' "${tag}" "${value}" >&2
    return 1
  fi
  printf '%s\n' "${value}"
}

capture_packages() {
  local immutable_image_id="$1"
  docker run --rm --network none --entrypoint dpkg-query \
    "${immutable_image_id}" -W '-f=${binary:Package}=${Version}\n' \
    | LC_ALL=C sort
}

capture_installed_tree() {
  local immutable_image_id="$1"
  docker run --rm --network none --entrypoint /tmp/installed-tree.sh \
    "${immutable_image_id}"
}

capture_key_files() {
  local immutable_image_id="$1"
  docker run --rm --network none --entrypoint sh "${immutable_image_id}" -c '
    set -eu
    for path in \
      /usr/local/bin/lcov \
      /usr/local/bin/genhtml \
      /usr/local/bin/geninfo \
      /usr/local/bin/genpng \
      /usr/local/bin/gendesc \
      /usr/local/bin/perl2lcov \
      /usr/local/bin/py2lcov \
      /usr/local/bin/xml2lcov \
      /usr/local/bin/xml2lcovutil.py \
      /usr/local/bin/llvm2lcov \
      /usr/local/etc/lcovrc \
      /usr/local/lib/lcov/lcovutil.pm \
      /usr/local/share/lcov/support-scripts/context.pm \
      /usr/local/share/lcov/support-scripts/gitblame \
      /usr/local/share/lcov/support-scripts/history.pm \
      /usr/local/share/lcov/html/index.html \
      /usr/local/share/lcov/html/objects.inv \
      /usr/local/share/man/man1/lcov.1
    do
      test -f "$path"
      sha256sum "$path"
    done
  '
}

capture_smoke() {
  local immutable_image_id="$1"
  local output="$2"
  local scratch="${evidence_root}/smoke-work-$3"
  mkdir -p "${scratch}"
  : >"${output}"
  for command in \
    lcov genhtml geninfo genpng gendesc perl2lcov py2lcov xml2lcov \
    xml2lcovutil.py llvm2lcov
  do
    local status
    set +e
    docker run --rm --network none "${immutable_image_id}" \
      "${command}" --help >"${scratch}/stdout" 2>"${scratch}/stderr"
    status=$?
    set -e
    if [[ "${status}" -ne 0 ]]; then
      printf 'help smoke failed: command=%s status=%s\n' "${command}" "${status}" >&2
      return 1
    fi
    if [[ "${command}" != "xml2lcovutil.py" && ! -s "${scratch}/stdout" ]]; then
      printf 'help smoke produced empty stdout: command=%s\n' "${command}" >&2
      return 1
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${command}" "${status}" \
      "$(wc -c <"${scratch}/stdout")" "$(sha256sum "${scratch}/stdout" | cut -d' ' -f1)" \
      "$(wc -c <"${scratch}/stderr")" "$(sha256sum "${scratch}/stderr" | cut -d' ' -f1)" \
      >>"${output}"
  done
  docker run --rm --network none --entrypoint sh "${immutable_image_id}" -c '
    set -eu
    test "$(lcov --version)" = "lcov: LCOV version 2.5-beta"
    test "$(genhtml --version)" = "genhtml: LCOV version 2.5-beta"
    test "$(geninfo --version)" = "geninfo: LCOV version 2.5-beta"
    test "$(stat -c "%a" /usr/local/bin/xml2lcovutil.py)" = 755
  '
}

compare_exact() {
  local label="$1" path_a="$2" path_b="$3"
  if ! cmp -s "${path_a}" "${path_b}"; then
    printf '%s differs between clean builds\n' "${label}" >&2
    diff -u "${path_a}" "${path_b}" || true
    return 1
  fi
  printf 'REPRO_MATCH field=%s sha256=%s lines=%s\n' \
    "${label}" "$(sha256sum "${path_a}" | cut -d' ' -f1)" \
    "$(wc -l <"${path_a}")"
}

do_build "${build_tag_a}"
readonly image_id_a="$(image_id "${build_tag_a}")"
capture_packages "${image_id_a}" >"${evidence_root}/packages-a"
capture_installed_tree "${image_id_a}" >"${evidence_root}/tree-a"
capture_key_files "${image_id_a}" >"${evidence_root}/keys-a"
capture_smoke "${image_id_a}" "${evidence_root}/smoke-a" a

do_build "${build_tag_b}"
readonly image_id_b="$(image_id "${build_tag_b}")"
capture_packages "${image_id_b}" >"${evidence_root}/packages-b"
capture_installed_tree "${image_id_b}" >"${evidence_root}/tree-b"
capture_key_files "${image_id_b}" >"${evidence_root}/keys-b"
capture_smoke "${image_id_b}" "${evidence_root}/smoke-b" b

test "$(wc -l <"${evidence_root}/packages-a")" -eq 284
test "$(wc -l <"${evidence_root}/tree-a")" -eq 321
test "$(wc -l <"${evidence_root}/keys-a")" -eq 18
test "$(wc -l <"${evidence_root}/smoke-a")" -eq 10

compare_exact packages "${evidence_root}/packages-a" "${evidence_root}/packages-b"
compare_exact installed-tree "${evidence_root}/tree-a" "${evidence_root}/tree-b"
compare_exact key-files "${evidence_root}/keys-a" "${evidence_root}/keys-b"
compare_exact smoke "${evidence_root}/smoke-a" "${evidence_root}/smoke-b"
compare_exact package-lock "${evidence_root}/packages-a" "${upstream_dir}/packages.full.lock"
compare_exact installed-tree-lock "${evidence_root}/tree-a" "${upstream_dir}/installed-tree.lock"

python3 "${upstream_dir}/record-manifest.py" \
  --image "${image_id_a}" \
  --rebuild-peer "${image_id_b}" \
  --output "${manifest}"
python3 "${root_dir}/compat/manifests/validate.py" \
  --verify-runtime "${manifest}"

printf 'ORACLE_BUILD_OK image_a=%s image_b=%s manifest=%s\n' \
  "${image_id_a}" "${image_id_b}" "${manifest}"
