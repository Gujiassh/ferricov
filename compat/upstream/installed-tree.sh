#!/bin/sh
set -eu

root="${1:-/usr/local}"
LC_ALL=C find "${root}" -xdev \( -type f -o -type l \) -print \
  | LC_ALL=C sort \
  | while IFS= read -r path; do
      mode="$(stat -c '%a' "${path}")"
      if [ -L "${path}" ]; then
        printf 'symlink\t%s\t%s\t%s\n' \
          "${mode}" "$(readlink "${path}")" "${path}"
      else
        digest="$(sha256sum "${path}" | cut -d' ' -f1)"
        printf 'file\t%s\t%s\t%s\n' "${mode}" "${digest}" "${path}"
      fi
    done
