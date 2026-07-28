# ADR 0003: Initial Compiler And Platform Matrix

- Status: proposed; M0 acceptance pending reproducible environment records and
  an execution-manifest format
- Date: 2026-07-27
- Scope: LCOV 2.5 compatibility qualification

## Context

Ferricov must separate three different claims:

1. the environment that makes the pinned LCOV Oracle identifiable and
   reproducible;
2. the compiler matrix used to qualify coverage capture behavior;
3. the operating-system and filesystem matrix used for release claims.

The current Oracle Dockerfile pins the Debian 12 `bookworm-slim` base digest,
the LCOV source commit, and the LCOV build date. Its `apt-get` step does not pin
a Debian snapshot or package versions, however, so a clean rebuild at a later
date is not guaranteed to produce the same installed runtime or image. The
local image observed on 2026-07-27 had Docker image ID
`sha256:de569b0afa0d3ffb6c9bb8116f6fc2ddee9f0837e1aab08bdf965df5744bc65e`.
The tag `ferricov/lcov-oracle:v2.5` is only a mutable alias for an image; it is
not an environment identity or a reproducibility record.

The pinned upstream test workflow exercises GCC 9, GCC 10, and GCC 14. It
states that GCC 10 through 14 are assumed to behave alike and therefore skips
GCC 11 through 13. Ferricov will use that statement to prioritize the matrix,
not as evidence that the skipped versions are compatible. The same workflow
also contains an experimental GCC 16 lane; a prerelease compiler cannot define
a Ferricov release requirement.

LCOV 2.5 documents MC/DC capture support for GCC 14.2 or newer and LLVM 18.1
or newer. It also documents different MC/DC meanings for GCC and LLVM, so the
two compiler families require separate semantic fixtures and cannot share a
single expected-output shortcut.

## Decision

### Oracle Environment Identity And Rebuild Policy

The M0 correctness Oracle has the following required identity:

| Dimension | Required value |
| --- | --- |
| Container base input | Debian 12 `bookworm-slim` at the digest in `compat/upstream/Dockerfile` |
| Installed image | content-addressed OCI artifact digest or archive hash; pending |
| Architecture | `x86_64` |
| LCOV source | commit `74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5` |
| Perl | exact installed version recorded in the image manifest |
| Default compiler | exact GCC, G++, and gcov versions recorded in the image manifest |
| Packages | complete package names and versions recorded in the image manifest |
| Executables | hashes of Oracle entry points and relevant runtime tools |
| Locale | explicit `C` or `C.UTF-8` per case |
| Timezone | explicit `UTC` per case |
| Network | disabled during differential execution |
| Work directory | fresh isolated directory per implementation run |

An existing Oracle environment is reproducible only through a retained,
content-addressed OCI artifact whose digest is recorded with the evidence. A
clean image rebuild is reproducible only when it uses a dated Debian snapshot,
exact package versions, and verified source inputs, or another mechanism with
equivalent content-addressed guarantees. Pinning the base image alone does not
make the current unversioned `apt-get` build reproducible.

Evidence records must resolve any convenience tag to the immutable image
identity before execution. Changing an identity field creates a new
environment identity; results from different identities must not be compared
as if they came from the same Oracle.

### Capture Qualification Matrix

The version expressions below define requirement families and sampling
boundaries. They do not identify an executable environment. Every run must
reference a pinned execution manifest containing the exact compiler, linker,
libc, kernel, extractor, target triple, image or runner identity, and fixture
hashes. The manifest must also list the inventory entries to which the run
applies.

| Lane | Requirement family | Coverage pipeline | Initial applicability | Milestone |
| --- | --- | --- | --- | --- |
| `gcc-9` | GCC/gcov `>=9,<10` | `.gcno`/`.gcda` through gcov JSON intermediate output | Linux `x86_64`; forcing text mode produces `unsupported` behavior and selects intermediate mode only if that error is ignored | M4 |
| `gcc-10` | GCC/gcov `>=10,<11` | `.gcno`/`.gcda` through gcov | Linux `x86_64`; representative pre-MC/DC modern capture | M4 |
| `gcc-12` | GCC/gcov `>=12,<13`, initially 12.2 | `.gcno`/`.gcda` through gcov | Linux `x86_64`; Oracle-image baseline and default fixture | M0/M4 |
| `gcc-14` | GCC/gcov `>=14.2,<15` | `.gcno`/`.gcda` through gcov | Linux `x86_64`; MC/DC plus line/function/branch capture | M4 |
| `llvm-gcov-14` | LLVM/Clang `>=14,<15` | `.gcno`/`.gcda` through LLVM's gcov-compatible path | Linux `x86_64`; non-MC/DC LLVM gcov behavior | M4 |
| `llvm-export-18` | LLVM/Clang `>=18.1,<19` | `.profraw` -> binary `.profdata` -> `llvm-cov export` JSON -> `llvm2lcov` | Linux `x86_64`; LLVM MC/DC semantics | M4/M5 |
| `llvm-export-21` | LLVM/Clang `>=21,<22` | `.profraw` -> binary `.profdata` -> `llvm-cov export` JSON -> `llvm2lcov` | Linux `x86_64`; LLVM 21+ recommended for cleaner MC/DC data | M5/M6 |
| `linux-kernel-gcov` | kernel-supported GCC/gcov pair, exact versions pinned per run | `/sys/kernel/debug/gcov` through `geninfo`/`lcov` | Linux `x86_64`; kernel tree, module unload, path, and permission behavior | M4 |

For the LLVM export lanes, instrumented execution writes `.profraw` files;
`llvm-profdata merge` converts them to a binary indexed `.profdata` file;
`llvm-cov export -format=text -instr-profile=<file.profdata>` writes JSON; and
`llvm2lcov` converts that JSON to LCOV tracefile data. The counterintuitive
`-format=text` spelling is the exact upstream command for its JSON export
workflow. A `.profdata` file is not JSON and is never passed directly to
`llvm2lcov`.

GCC 11 and 13 are boundary sampling lanes for M6 rather than assumed aliases
of GCC 10, 12, or 14. GCC 16 remains observational until it is a stable,
generally available toolchain. Historical patched GCC 3.3 and GCC 4.6 modes
remain public contract entries. Their inventory applicability must be decided
explicitly; unavailable toolchains cannot be converted silently to
`not_applicable` or treated as covered by a modern GCC lane.

Each execution manifest must retain compiler, gcov, llvm-profdata, llvm-cov,
linker, libc, kernel, source, binary, raw coverage, and fixture versions or
hashes as applicable. A capture result qualifies only the inventory entries
and compiler-platform combinations named in that manifest. A family range in
this ADR never substitutes for exact manifest pins.

### Release Platform Matrix

| Platform lane | Architecture | Filesystem cases | Release role |
| --- | --- | --- | --- |
| Linux | `x86_64` | ext4 plus container overlayfs | primary development and required full v1 qualification |
| Linux | `aarch64` | ext4 | required v1 artifact and core qualification; no full platform claim until every applicable entry passes |
| macOS | Apple silicon | default case-insensitive APFS plus case-sensitive volume | required before a macOS compatibility claim |
| macOS | `x86_64` | case-insensitive APFS | packaging and compatibility lane when a runner remains available |
| WSL2 | `x86_64` | WSL virtual disk plus mounted Windows filesystem | pending Linux-hosted qualification; never evidence for native Windows |
| MSYS2 on Windows | `x86_64` | MSYS2 and Windows path/process boundaries | pending separate qualification; never inferred from WSL or Win32 |
| Native Windows/Win32 | `x86_64` | NTFS with native path/process behavior | pending and outside the initial v1 declared matrix |

WSL2, MSYS2, and native Win32 have different process, path, filesystem, and
toolchain behavior. Evidence from one lane does not qualify either of the
others. A WSL2 claim is a claim for the exact recorded WSL environment, not a
generic native Windows claim.

Filesystem fixtures must cover relative and absolute paths, symlinks,
hardlinks, permission failures, non-UTF-8 path bytes where the platform permits
them, case collisions, spaces, glob characters, and cleanup after partial
failure. Platform-specific unavailable behavior is recorded as
`not_applicable` only when the inventory entry has a reviewed applicability
rationale; it is never converted to `pass`.

## Acceptance Gates

- M0 baseline suites run against a retained content-addressed Oracle artifact,
  or against an image rebuilt from dated repositories and exact package pins.
- Every compiler and integration run has an immutable execution manifest and
  an explicit inventory-entry applicability set.
- M4 does not close until every required compiler and kernel-integration lane
  has raw differential evidence. A blocked required lane keeps M4 open; closing
  the milestone requires resolving it or revising this ADR and the declared
  support matrix before the gate is evaluated again.
- Every capture inventory entry passes on every compiler-platform combination
  to which its reviewed applicability mapping assigns it.
- GCC and LLVM MC/DC fixtures assert their respective encoded meanings rather
  than comparing only aggregate counts.
- M6 samples GCC 11 and 13 instead of inheriting upstream's equivalence
  assumption without evidence.
- A platform is named in a compatibility claim only after every applicable
  public inventory entry passes there. Installation, CLI, tracefile,
  filesystem, representative capture, and report smoke suites are necessary
  evidence but cannot replace entry-level coverage.
- The v1 drop-in claim requires all applicable inventory entries to pass on
  every compiler-platform combination in the exact published v1 matrix.
- Performance comparisons use the same platform, architecture, filesystem,
  toolchain, CPU allocation, execution manifest, and fixture identity on both
  sides.

## Source Evidence

- `compat/upstream/Dockerfile`: pinned Debian base digest and LCOV source
  commit, plus the currently unpinned Debian package installation.
- `compat/upstream/verification.md`: observed 10-command installation and
  immutable LCOV source identity; it does not yet retain an OCI artifact
  digest or a rebuild package manifest.
- LCOV v2.5 `.github/workflows/run_test_suite.yml`: upstream GCC 9, 10, and 14
  coverage plus the explicit GCC 10-14 equivalence assumption.
- LCOV v2.5 `bin/geninfo:350-379`: JSON/intermediate selection and the
  `unsupported` behavior when text mode is forced with gcov 9 or newer.
- LCOV v2.5 `docs/man/lcov.rst`: GCC 14.2 and LLVM 18.1 MC/DC minimums.
- LCOV v2.5 `bin/llvm2lcov` and `docs/man/llvm2lcov.rst`: the `.profraw` to
  `.profdata` to `llvm-cov export` JSON to `llvm2lcov` pipeline;
  LLVM 21+ recommended for cleaner MC/DC data.
- LCOV v2.5 `docs/man/genhtml.rst`: distinct GCC and LLVM MC/DC semantics.
- LCOV v2.5 `bin/geninfo:100-102,1937-1963,2404-2408`: MSYS-specific Win32
  path handling and the MSYS GCC 9 JSON path workaround.
- LCOV v2.5 `README.rst:335-356`, `docs/man/lcov.rst:190-197`, and
  `bin/lcov:1995-2040`: documented Linux kernel capture workflow and runtime
  discovery of `/sys/kernel/debug/gcov` or `/proc/gcov`.

## Consequences

The matrix is intentionally narrower than every compiler LCOV has ever
encountered, but broader than the single Oracle image. It prevents a version
family, mutable tag, smoke suite, or blocked lane from being presented as
compatibility evidence. Adding a compiler or platform requires reviewed
inventory applicability, fixtures, immutable execution manifests,
differential evidence, and an update to this ADR or a superseding decision.

This ADR remains proposed until the Oracle has either a retained
content-addressed artifact or a clean reproducible rebuild definition, and the
execution-manifest format is recorded for the required lanes. Those are M0
acceptance prerequisites, not deferred release documentation.
