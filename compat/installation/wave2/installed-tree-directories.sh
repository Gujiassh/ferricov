#!/bin/sh
# Wave-2 companion recorder for LCOV installed-tree directory modes.
#
# The baseline compat/upstream/installed-tree.sh remains file/symlink-only so
# the historical 321-entry Docker lock and execution-manifest script hash stay
# byte-stable. This companion records directory rows only:
#   directory<TAB>mode<TAB>.<TAB>absolute-path
#
# Usage:
#   ./installed-tree-directories.sh [/usr/local]
set -eu

root="${1:-/usr/local}"
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT

# Payload roots only. Ancestors under ${root} are added without walking them.
payload_roots="
${root}/bin
${root}/etc
${root}/lib/lcov
${root}/share/man
${root}/share/lcov
"

# shellcheck disable=SC2086
for payload_root in ${payload_roots}; do
  if [ -d "${payload_root}" ] && [ ! -L "${payload_root}" ]; then
    LC_ALL=C find "${payload_root}" -xdev -type d ! -type l -print >>"${tmp}"
  fi
done

# Pure path ancestors required by the payload.
for ancestor in \
  "${root}" \
  "${root}/lib" \
  "${root}/share"
do
  if [ -d "${ancestor}" ] && [ ! -L "${ancestor}" ]; then
    printf '%s\n' "${ancestor}" >>"${tmp}"
  fi
done

LC_ALL=C sort -u "${tmp}" | while IFS= read -r path; do
  [ -n "${path}" ] || continue
  mode="$(stat -c '%a' "${path}")"
  printf 'directory\t%s\t.\t%s\n' "${mode}" "${path}"
done
