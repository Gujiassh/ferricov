FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818

ARG DEBIAN_FRONTEND=noninteractive
ARG LCOV_REF=v2.5
ARG LCOV_SHA=74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        g++ \
        gcc \
        git \
        libcapture-tiny-perl \
        libdatetime-perl \
        libdevel-cover-perl \
        libdevel-stacktrace-perl \
        libgd-perl \
        libjson-xs-perl \
        libtimedate-perl \
        make \
        perl \
        python3 \
        python3-coverage \
        python3-xlsxwriter \
        python3-sphinx \
        python3-sphinx-rtd-theme \
        time \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --branch "${LCOV_REF}" --depth 1 \
        https://github.com/linux-test-project/lcov.git /opt/lcov \
    && test "$(git -C /opt/lcov rev-parse HEAD)" = "${LCOV_SHA}" \
    && LCOV_BUILD_DATE=2026-07-06 make -C /opt/lcov install \
    && test "$(stat -c '%a' /usr/local/bin/xml2lcovutil.py)" = 755 \
    && rm -rf /opt/lcov

WORKDIR /work

CMD ["lcov", "--version"]
