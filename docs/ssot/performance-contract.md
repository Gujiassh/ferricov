# Performance Contract

## Principle

Correctness gates performance. A benchmark result is invalid until the same
fixture passes the compatibility Oracle.

## Metrics

Each benchmark records:

- elapsed wall time
- total CPU time
- peak resident memory
- output size and file count
- effective throughput for bytes, records, or source files
- thread count and parallel scaling where supported

## Benchmark Families

1. process startup and help/version operations
2. tracefile parse, write, and round trip at small, medium, and large sizes
3. merge, extract, remove, substitute, filter, summary, and list operations
4. `genhtml` default and feature-heavy reports, including issue-derived cases
5. `geninfo` capture across the declared GCC and LLVM matrix
6. converters, callbacks, malformed inputs, and failure paths

Fixtures include upstream tests, real open-source projects, generated scale
cases, and regressions derived from upstream performance issues.

## Release Gates

Measured on the same pinned environment and fixture:

- The median wall time of every representative case must be no worse than the
  Perl baseline beyond a 5% measurement tolerance.
- The geometric mean wall time for each benchmark family must beat the Perl
  baseline.
- Large tracefile operations and large HTML reports must be at least 2x faster;
  3-5x is the project target.
- Peak RSS must not exceed the Perl baseline for representative cases and must
  improve on large cases.
- Parallel execution must improve throughput and must not reproduce upstream
  cases where adding workers makes execution materially slower.

The 5% tolerance accounts for measurement noise; it is not permission to ship
a known regression. A failed gate blocks the compatibility release.

## Method

- Build optimized binaries with a pinned Rust toolchain.
- Run both implementations in the same container or host environment.
- Pin CPU allocation when supported, record hardware and software versions,
  warm caches explicitly, and retain raw samples.
- Use enough repetitions to report median, dispersion, and outliers.
- Keep local exploratory results separate from committed release evidence.
