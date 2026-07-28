# syntax=docker/dockerfile:1

FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818 AS oracle-build

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBIAN_SNAPSHOT=20260713T000000Z
ARG LCOV_REF=v2.5
ARG LCOV_SHA=74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5
ARG LCOV_BUILD_DATE=2026-07-06
ARG SOURCE_DATE_EPOCH=1783375223
ARG SOURCE_ARCHIVE_SHA256
ARG INTERSPHINX_INVENTORY_SHA256
ARG BUILD_INPUTS_LOCK_SHA256
ARG SNAPSHOT_CA_BUNDLE_SHA256

LABEL org.opencontainers.image.source="https://github.com/linux-test-project/lcov" \
      org.opencontainers.image.version="${LCOV_REF}" \
      org.opencontainers.image.revision="${LCOV_SHA}" \
      dev.ferricov.base-image-digest="sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818" \
      dev.ferricov.build-date="${LCOV_BUILD_DATE}" \
      dev.ferricov.build-inputs-lock-sha256="sha256:${BUILD_INPUTS_LOCK_SHA256}" \
      dev.ferricov.debian-snapshot="${DEBIAN_SNAPSHOT}" \
      dev.ferricov.intersphinx-inventory-sha256="sha256:${INTERSPHINX_INVENTORY_SHA256}" \
      dev.ferricov.snapshot-ca-bundle-sha256="sha256:${SNAPSHOT_CA_BUNDLE_SHA256}" \
      dev.ferricov.source-archive-sha256="sha256:${SOURCE_ARCHIVE_SHA256}" \
      dev.ferricov.source-date-epoch="${SOURCE_DATE_EPOCH}"

COPY packages.lock /tmp/oracle-packages.lock
COPY packages.full.lock /tmp/oracle-packages.full.lock
COPY build-inputs.lock /tmp/build-inputs.lock
COPY lcov-v2.5.tar.gz /tmp/lcov-v2.5.tar.gz
COPY python-objects.inv /tmp/python-objects.inv
COPY pin-intersphinx.py /tmp/pin-intersphinx.py
COPY snapshot-ca-certificates.crt /tmp/snapshot-ca-certificates.crt

RUN set -eu; \
    test -n "${SNAPSHOT_CA_BUNDLE_SHA256}"; \
    test "$(sha256sum /tmp/snapshot-ca-certificates.crt | cut -d' ' -f1)" = "${SNAPSHOT_CA_BUNDLE_SHA256}"; \
    grep -Fx "snapshot_ca_bundle_sha256=${SNAPSHOT_CA_BUNDLE_SHA256}" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_bytes=$(stat -c '%s' /tmp/snapshot-ca-certificates.crt)" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_certificates=142" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_producer=concatenate-sorted-ca-certificates-mozilla-crt" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_source_package=ca-certificates=20230311+deb12u1" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_source_url=https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/pool/main/c/ca-certificates/ca-certificates_20230311%2Bdeb12u1_all.deb" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_source_sha256=0d5f444f594e48c1e16a41d8fc628a09b24c658916a1274025c2330f2a802bed" /tmp/build-inputs.lock; \
    grep -Fx "snapshot_ca_bundle_source_bytes=155260" /tmp/build-inputs.lock; \
    sed -i \
        -e "s|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}|" \
        -e "s|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}|" \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get --quiet=2 \
        -o Acquire::Check-Valid-Until=false \
        -o Acquire::Retries=5 \
        -o Acquire::https::CaInfo=/tmp/snapshot-ca-certificates.crt \
        -o Acquire::http::Pipeline-Depth=0 \
        -o Acquire::https::Pipeline-Depth=0 \
        -o Acquire::Queue-Mode=access \
        update \
    && xargs -r apt-get --quiet=2 \
        -o Acquire::Retries=5 \
        -o Acquire::https::CaInfo=/tmp/snapshot-ca-certificates.crt \
        -o Acquire::http::Pipeline-Depth=0 \
        -o Acquire::https::Pipeline-Depth=0 \
        -o Acquire::Queue-Mode=access \
        install --yes --no-install-recommends \
        </tmp/oracle-packages.lock \
    && dpkg-query -W -f='${binary:Package}=${Version}\n' \
        $(cut -d= -f1 /tmp/oracle-packages.lock) \
        | LC_ALL=C sort \
        | diff -u /tmp/oracle-packages.lock - \
    && dpkg-query -W -f='${binary:Package}=${Version}\n' \
        | LC_ALL=C sort \
        | diff -u /tmp/oracle-packages.full.lock - \
    && rm -rf /var/lib/apt/lists/* /tmp/snapshot-ca-certificates.crt

RUN set -eu; \
    test -n "${SOURCE_ARCHIVE_SHA256}"; \
    test -n "${INTERSPHINX_INVENTORY_SHA256}"; \
    test -n "${BUILD_INPUTS_LOCK_SHA256}"; \
    test "$(sha256sum /tmp/build-inputs.lock | cut -d' ' -f1)" = "${BUILD_INPUTS_LOCK_SHA256}"; \
    test "$(sha256sum /tmp/lcov-v2.5.tar.gz | cut -d' ' -f1)" = "${SOURCE_ARCHIVE_SHA256}"; \
    test "$(sha256sum /tmp/python-objects.inv | cut -d' ' -f1)" = "${INTERSPHINX_INVENTORY_SHA256}"; \
    grep -Fx "lcov_source_commit=${LCOV_SHA}" /tmp/build-inputs.lock; \
    grep -Fx "lcov_source_tree=2b923cc012113c191db5969a8a5b81caf4d22c10" /tmp/build-inputs.lock; \
    grep -Fx "lcov_source_archive_producer=git-archive-tar-umask-0022+gzip-n-9" /tmp/build-inputs.lock; \
    grep -Fx "lcov_source_archive_sha256=${SOURCE_ARCHIVE_SHA256}" /tmp/build-inputs.lock; \
    grep -Fx "python_objects_inv_sha256=${INTERSPHINX_INVENTORY_SHA256}" /tmp/build-inputs.lock; \
    grep -Fx "python_objects_inv_url=https://docs.python.org/3.14/objects.inv" /tmp/build-inputs.lock; \
    grep -Fx "python_objects_inv_project=Python" /tmp/build-inputs.lock; \
    grep -Fx "python_objects_inv_version=3.14" /tmp/build-inputs.lock; \
    grep -Fx "pin_intersphinx_sha256=$(sha256sum /tmp/pin-intersphinx.py | cut -d' ' -f1)" /tmp/build-inputs.lock; \
    grep -Fx "pin_intersphinx_bytes=$(stat -c '%s' /tmp/pin-intersphinx.py)" /tmp/build-inputs.lock; \
    grep -Fx "source_date_epoch=${SOURCE_DATE_EPOCH}" /tmp/build-inputs.lock; \
    test "$(gzip -dc /tmp/lcov-v2.5.tar.gz | git get-tar-commit-id)" = "${LCOV_SHA}"; \
    mkdir -p /opt/lcov; \
    tar -xzf /tmp/lcov-v2.5.tar.gz --strip-components=1 -C /opt/lcov; \
    install -m 644 /tmp/python-objects.inv /opt/lcov/docs/python-objects.inv; \
    python3 /tmp/pin-intersphinx.py \
        /opt/lcov/docs/conf.py /opt/lcov/docs/python-objects.inv; \
    find /opt/lcov -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +; \
    LC_ALL=C TZ=UTC PYTHONHASHSEED=0 SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" \
        BUILD_DATE="${LCOV_BUILD_DATE}" LCOV_BUILD_DATE="${LCOV_BUILD_DATE}" \
        VERSION=2.5 RELEASE=beta \
        make -C /opt/lcov install; \
    test "$(stat -c '%a' /usr/local/bin/xml2lcovutil.py)" = 755; \
    rm -rf /opt/lcov /tmp/lcov-v2.5.tar.gz /tmp/python-objects.inv \
        /tmp/pin-intersphinx.py

FROM oracle-build AS oracle

COPY installed-tree.sh /tmp/installed-tree.sh
COPY installed-tree.lock /tmp/installed-tree.lock

RUN set -eu; \
    /tmp/installed-tree.sh > /tmp/observed-installed-tree.lock; \
    diff -u /tmp/installed-tree.lock /tmp/observed-installed-tree.lock; \
    rm /tmp/observed-installed-tree.lock

WORKDIR /work

CMD ["lcov", "--version"]
