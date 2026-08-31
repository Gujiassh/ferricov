#!/bin/sh
# In-container driver for installation wave-2 Oracle captures.
# Invoked as: capture-driver.sh <CASE_ID> <OUT_DIR>
# Subject processes run under a clean env via process-observer.py (ptrace
# exec-stop). Live /proc evidence provides exe/argv/cwd and real wait status.
set -eu

CASE_ID="${1:?case id required}"
OUT_DIR="${2:?out dir required}"
SRC_RO="${SRC_RO:-/src-ro}"
PIN_INV="${PIN_INV:-/tmp/python-objects.inv}"
PIN_PY="${PIN_PY:-/tmp/pin-intersphinx.py}"
DIR_RECORDER="${DIR_RECORDER:-/tmp/installed-tree-directories.sh}"
OBSERVER="${OBSERVER:-/tmp/process-observer.py}"

mkdir -p "$OUT_DIR"
STDOUT_BIN="$OUT_DIR/stdout.bin"
STDERR_BIN="$OUT_DIR/stderr.bin"
META_JSON="$OUT_DIR/meta.env"
TREE_JSON="$OUT_DIR/tree-effects.json"
STATUS_FILE="$OUT_DIR/status.env"
OBS_ENV="$OUT_DIR/observed-env.env"
OBS_ARGV="$OUT_DIR/observed-argv.json"
OBS_CHILDREN="$OUT_DIR/observed-children.json"
CLEANUP_LOG="$OUT_DIR/cleanup.log"
ENV_FILE="$OUT_DIR/clean-env.env"
RUN_META="$OUT_DIR/run-meta.env"

: >"$STDOUT_BIN"
: >"$STDERR_BIN"
: >"$META_JSON"
: >"$STATUS_FILE"
: >"$OBS_ENV"
: >"$CLEANUP_LOG"
: >"$RUN_META"
printf '[]\n' >"$OBS_CHILDREN"

# Explicit clean environment for case commands (no inherited image secrets).
BASE_ENV_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
write_clean_env() {
  # Writes KEY=VALUE lines used by process-observer (env -i equivalent).
  {
    echo "PATH=$BASE_ENV_PATH"
    echo "HOME=/tmp"
    echo "TERM=dumb"
    echo "LANG=C"
    echo "LC_ALL=C"
    echo "TZ=UTC"
    echo "PYTHONHASHSEED=0"
    echo "SOURCE_DATE_EPOCH=1783375223"
    echo "LCOV_BUILD_DATE=2026-07-06"
    echo "BUILD_DATE=2026-07-06"
    echo "VERSION=2.5"
    echo "RELEASE=beta"
    # EXTRA_ENV_LINES may add KEY=VALUE overrides (e.g. LCOV_PERL=...).
    if [ -n "${EXTRA_ENV_LINES:-}" ]; then
      printf '%s\n' "$EXTRA_ENV_LINES"
    fi
  } | LC_ALL=C sort >"$ENV_FILE"
}

# Helper for fixture steps that are not the attested subject.
base_env_run() {
  env -i \
    PATH="$BASE_ENV_PATH" \
    HOME=/tmp \
    TERM=dumb \
    LANG=C \
    LC_ALL=C \
    TZ=UTC \
    PYTHONHASHSEED=0 \
    SOURCE_DATE_EPOCH=1783375223 \
    LCOV_BUILD_DATE=2026-07-06 \
    BUILD_DATE=2026-07-06 \
    VERSION=2.5 \
    RELEASE=beta \
    "$@"
}

append_meta() {
  printf '%s\n' "$@" >>"$META_JSON"
}

write_tree_effects() {
  root="$1"
  python3 - "$root" "$TREE_JSON" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
root = Path(sys.argv[1])
out = Path(sys.argv[2])
files = symlinks = dirs = 0
rows = []
if root.exists():
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dpath = Path(dirpath)
        if dpath.is_symlink():
            continue
        dirs += 1
        rows.append(
            {
                "kind": "directory",
                "mode": oct(dpath.stat().st_mode)[-3:],
                "identity": ".",
                "path": dpath.as_posix(),
            }
        )
        for name in sorted(dirnames):
            p = dpath / name
            if p.is_symlink():
                symlinks += 1
                rows.append(
                    {
                        "kind": "symlink",
                        "mode": oct(p.lstat().st_mode)[-3:],
                        "identity": os.readlink(p),
                        "path": p.as_posix(),
                    }
                )
        for name in sorted(filenames):
            p = dpath / name
            if p.is_symlink():
                symlinks += 1
                rows.append(
                    {
                        "kind": "symlink",
                        "mode": oct(p.lstat().st_mode)[-3:],
                        "identity": os.readlink(p),
                        "path": p.as_posix(),
                    }
                )
            elif p.is_file():
                files += 1
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                rows.append(
                    {
                        "kind": "file",
                        "mode": oct(p.stat().st_mode)[-3:],
                        "identity": digest,
                        "path": p.as_posix(),
                    }
                )
rows_sorted = sorted(rows, key=lambda r: r["path"])
row_lines = [
    f"{r['kind']}\t{r['mode']}\t{r['identity']}\t{r['path']}" for r in rows_sorted
]
payload = {
    "root": root.as_posix() if root.as_posix().startswith("/") else "/",
    "file_count": files,
    "symlink_count": symlinks,
    "directory_count": dirs,
    "paths_sha256": hashlib.sha256(
        ("\n".join(row_lines) + ("\n" if row_lines else "")).encode()
    ).hexdigest(),
    "rows": rows_sorted,
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(payload["paths_sha256"])
PY
}

prepare_src() {
  rm -rf /tmp/src
  cp -a "$SRC_RO" /tmp/src
  if [ -f "$PIN_INV" ] && [ -f "$PIN_PY" ]; then
    install -m 644 "$PIN_INV" /tmp/src/docs/python-objects.inv
    base_env_run python3 "$PIN_PY" /tmp/src/docs/conf.py /tmp/src/docs/python-objects.inv
  fi
}

record_cleanup() {
  for target in "$@"; do
    if [ -e "$target" ] || [ -L "$target" ]; then
      rm -rf -- "$target"
      echo "removed:$target" >>"$CLEANUP_LOG"
    else
      echo "absent:$target" >>"$CLEANUP_LOG"
    fi
  done
}

# run_subject WORKDIR TIMEOUT_SECONDS [qualification] -- argv...
# Live-process observation via ptrace supervisor. No declared exe/argv/cwd.
run_subject() {
  workdir="$1"
  timeout_sec="$2"
  shift 2
  qualification=""
  if [ "${1:-}" = "signal" ] || [ "${1:-}" = "timeout" ]; then
    qualification="$1"
    shift
  fi
  if [ "${1:-}" = "--" ]; then
    shift
  fi

  write_clean_env

  set +e
  python3 "$OBSERVER" \
    --workdir "$workdir" \
    --timeout-seconds "$timeout_sec" \
    --stdout "$STDOUT_BIN" \
    --stderr "$STDERR_BIN" \
    --status "$STATUS_FILE" \
    --observed-argv "$OBS_ARGV" \
    --observed-children "$OBS_CHILDREN" \
    --meta "$RUN_META" \
    --observed-env "$OBS_ENV" \
    --env-file "$ENV_FILE" \
    ${qualification:+--qualification "$qualification"} \
    -- "$@"
  observer_rc=$?
  set -e

  # Merge run-meta into cumulative meta.
  if [ -s "$RUN_META" ]; then
    cat "$RUN_META" >>"$META_JSON"
  fi
  append_meta "OBSERVER_RC=$observer_rc"
  append_meta "SUBJECT_DECLARED=$*"

  # Ensure status file exists even on observer failure.
  if [ ! -s "$STATUS_FILE" ]; then
    {
      echo "EXIT_STATUS=1"
      echo "SIGNAL="
      echo "TIMED_OUT=0"
      echo "HOST_OBSERVER_CODE=$observer_rc"
      echo "WORKDIR=$workdir"
      echo "EXECUTABLE_PATH="
      echo "EXECUTABLE_SHA256="
    } >"$STATUS_FILE"
  fi
  return 0
}

EXTRA_ENV_LINES=""

case "$CASE_ID" in
  INST-LAYOUT-001)
    append_meta "FIXTURE=image_payload_directories"
    append_meta "CLEANUP=none_required_read_only_payload_scan"
    # Subject is the directory companion recorder under /bin/sh (live observed).
    run_subject / 60 -- /bin/sh "$DIR_RECORDER" /usr/local
    cp "$STDOUT_BIN" "$OUT_DIR/installed-directories.lock"
    python3 - "$OUT_DIR/installed-directories.lock" "$TREE_JSON" <<'PY'
import hashlib, json, sys
from pathlib import Path
rows_raw = [r for r in Path(sys.argv[1]).read_text().splitlines() if r]
rows = []
for r in rows_raw:
    kind, mode, identity, path = r.split("\t")
    rows.append({"kind": kind, "mode": mode, "identity": identity, "path": path})
payload = {
  "root": "/usr/local",
  "file_count": 0,
  "symlink_count": 0,
  "directory_count": len(rows),
  "paths_sha256": hashlib.sha256(("\n".join(rows_raw) + "\n").encode()).hexdigest(),
  "rows": rows,
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
    echo "cleanup:none" >>"$CLEANUP_LOG"
    ;;

  INST-STAGE-001)
    prepare_src
    append_meta "FIXTURE=clean_src_pinned_docs"
    append_meta "CLEANUP=rm -rf /tmp/destdir-stage /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-stage
    mkdir -p /tmp/destdir-stage
    run_subject /tmp/src 600 -- make install DESTDIR=/tmp/destdir-stage PREFIX=/usr/local
    write_tree_effects /tmp/destdir-stage
    record_cleanup /tmp/destdir-stage /tmp/src
    ;;

  INST-INTERP-001)
    prepare_src
    # LCOV_PERL is part of the clean subject environment (not a separate env argv0).
    EXTRA_ENV_LINES="LCOV_PERL=/opt/custom/bin/perl"
    append_meta "FIXTURE=clean_src_custom_LCOV_PERL"
    append_meta "CLEANUP=rm -rf /tmp/destdir-interp /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-interp
    mkdir -p /tmp/destdir-interp
    run_subject /tmp/src 600 -- make install DESTDIR=/tmp/destdir-interp PREFIX=/usr/local
    {
      echo "lcov=$(head -n1 /tmp/destdir-interp/usr/local/bin/lcov 2>/dev/null || true)"
      echo "py2lcov=$(head -n1 /tmp/destdir-interp/usr/local/bin/py2lcov 2>/dev/null || true)"
      echo "xml2lcovutil=$(head -n1 /tmp/destdir-interp/usr/local/bin/xml2lcovutil.py 2>/dev/null || true)"
      echo "custom_matches=$(grep -R \"/opt/custom/bin/perl\" -l /tmp/destdir-interp 2>/dev/null | wc -l)"
    } >"$OUT_DIR/observation.txt"
    write_tree_effects /tmp/destdir-interp
    record_cleanup /tmp/destdir-interp /tmp/src
    ;;

  INST-CONFIG-DISCOVERY-001)
    append_meta "FIXTURE=temp_home_and_lcov_home_files"
    append_meta "CLEANUP=rm -rf /tmp/h1 /tmp/lh /tmp/config-probe.pl"
    cat > /tmp/config-probe.pl <<'PL'
use strict;
use warnings;
use File::Spec;
use File::Path qw(make_path remove_tree);

sub probe {
  my (%env) = @_;
  local %ENV = %ENV;
  delete $ENV{HOME};
  delete $ENV{LCOV_HOME};
  $ENV{$_} = $env{$_} for keys %env;
  my $selected = 'none';
  foreach my $v (['HOME', '.lcovrc'], ['LCOV_HOME', 'etc', 'lcovrc']) {
    next unless exists($ENV{$v->[0]});
    my @parts = @$v;
    my $root = shift @parts;
    my $f = File::Spec->catfile($ENV{$root}, @parts);
    if (-r $f) {
      $selected = $f;
      last;
    }
  }
  print "SELECTED=$selected\n";
}

remove_tree('/tmp/h1', '/tmp/lh');
make_path('/tmp/h1', '/tmp/lh/etc');
open my $fh, '>', '/tmp/h1/.lcovrc' or die $!;
print {$fh} "genhtml_description=1\n";
close $fh;
open $fh, '>', '/tmp/lh/etc/lcovrc' or die $!;
print {$fh} "genhtml_description=0\n";
close $fh;

print "HOME only:\n"; probe(HOME => '/tmp/h1');
print "LCOV_HOME only:\n"; probe(LCOV_HOME => '/tmp/lh');
print "both HOME first:\n"; probe(HOME => '/tmp/h1', LCOV_HOME => '/tmp/lh');
print "empty both:\n"; probe();
PL
    run_subject /tmp 60 -- perl /tmp/config-probe.pl
    write_tree_effects /tmp/h1
    record_cleanup /tmp/h1 /tmp/lh /tmp/config-probe.pl
    ;;

  INST-UNINSTALL-001)
    prepare_src
    append_meta "FIXTURE=staged_install_with_foreign_sentinels"
    append_meta "CLEANUP=rm -rf /tmp/destdir-uninst /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-uninst
    mkdir -p /tmp/destdir-uninst
    (
      cd /tmp/src
      base_env_run make install DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local >>"$OUT_DIR/install.log" 2>&1
    )
    mkdir -p /tmp/destdir-uninst/usr/local/share/man/man1
    echo foreign > /tmp/destdir-uninst/usr/local/etc/foreign.conf
    echo extra > /tmp/destdir-uninst/usr/local/share/man/man1/extra.1
    run_subject /tmp/src 600 -- make uninstall DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local
    write_tree_effects /tmp/destdir-uninst
    record_cleanup /tmp/destdir-uninst /tmp/src
    ;;

  INST-PARTIAL-001)
    prepare_src
    append_meta "FIXTURE=fake_install_wrapper_fail_after_count"
    append_meta "CLEANUP=rm -rf /tmp/partial /tmp/src /tmp/fake-install /tmp/install-count"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    cat > /tmp/fake-install <<'SH'
#!/bin/sh
cfile=/tmp/install-count
n=$(cat "$cfile" 2>/dev/null || echo 0)
n=$((n+1)); echo $n > "$cfile"
case " $* " in
  *" -d "*) exec /usr/bin/install "$@" ;;
esac
if [ "$n" -gt 20 ]; then
  echo "induced failure at install count=$n args=$*" >&2
  exit 1
fi
exec /usr/bin/install "$@"
SH
    chmod +x /tmp/fake-install
    echo 0 > /tmp/install-count
    rm -rf /tmp/partial
    mkdir -p /tmp/partial
    run_subject /tmp/src 600 -- make install DESTDIR=/tmp/partial PREFIX=/usr/local INSTALL=/tmp/fake-install
    write_tree_effects /tmp/partial
    record_cleanup /tmp/partial /tmp/src /tmp/fake-install /tmp/install-count
    ;;

  INST-DOC-FAIL-001)
    prepare_src
    append_meta "FIXTURE=sphinx_build_hidden"
    append_meta "CLEANUP=restore sphinx-build; rm -rf /tmp/docfail /tmp/src"
    if [ -x /usr/bin/sphinx-build ]; then
      mv /usr/bin/sphinx-build /usr/bin/sphinx-build.hidden
    fi
    rm -f /tmp/src/doc_finished
    rm -rf /tmp/src/docs/_build /tmp/docfail
    mkdir -p /tmp/docfail
    run_subject /tmp/src 300 -- make install DESTDIR=/tmp/docfail PREFIX=/usr/local
    if [ -x /usr/bin/sphinx-build.hidden ]; then
      mv /usr/bin/sphinx-build.hidden /usr/bin/sphinx-build
      echo "restored:/usr/bin/sphinx-build" >>"$CLEANUP_LOG"
    fi
    write_tree_effects /tmp/docfail
    record_cleanup /tmp/docfail /tmp/src
    ;;

  INST-PATH-REL-001)
    prepare_src
    append_meta "FIXTURE=relative_destdir"
    append_meta "CLEANUP=rm -rf /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    run_subject /tmp/src 120 -- make install DESTDIR=rel-dest PREFIX=/usr/local
    write_tree_effects /tmp/src/rel-dest
    record_cleanup /tmp/src
    ;;

  INST-PATH-SPACE-001)
    prepare_src
    append_meta "FIXTURE=space_containing_destdir"
    append_meta "CLEANUP=rm -rf /tmp/destdir space /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf "/tmp/destdir space"
    mkdir -p "/tmp/destdir space"
    run_subject /tmp/src 300 -- make install "DESTDIR=/tmp/destdir space" PREFIX=/usr/local
    write_tree_effects "/tmp/destdir space"
    record_cleanup "/tmp/destdir space" /tmp/src
    ;;

  INST-DIRTY-ASSET-001)
    prepare_src
    append_meta "FIXTURE=untracked_script_in_scripts"
    append_meta "CLEANUP=rm -rf /tmp/destdir-dirty /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    printf '#!/bin/sh\necho dirty\n' > /tmp/src/scripts/zz_dirty_wave2_sentinel
    chmod +x /tmp/src/scripts/zz_dirty_wave2_sentinel
    rm -rf /tmp/destdir-dirty
    mkdir -p /tmp/destdir-dirty
    run_subject /tmp/src 600 -- make install DESTDIR=/tmp/destdir-dirty PREFIX=/usr/local
    write_tree_effects /tmp/destdir-dirty
    record_cleanup /tmp/destdir-dirty /tmp/src
    ;;

  INST-TEST-RUN-001)
    append_meta "FIXTURE=installed_tests_unset_LCOV_HOME"
    append_meta "CLEANUP=none_required_read_only"
    # Deterministic dry-run of installed tests `info` without LCOV_HOME.
    # Clean env never includes LCOV_HOME (equivalent to `env -u LCOV_HOME make -n info`).
    # Direct make subject so live exe/argv/cwd match the intended make identity.
    EXTRA_ENV_LINES=""
    run_subject /usr/local/share/lcov/tests 60 -- make -n info
    write_tree_effects /usr/local/share/lcov/tests
    echo "cleanup:none" >>"$CLEANUP_LOG"
    ;;

  INST-DOC-PATH-001)
    prepare_src
    append_meta "FIXTURE=readme_path_extraction"
    append_meta "CLEANUP=rm -rf /tmp/src"
    cat > /tmp/extract_readme_paths.py <<'PY'
from pathlib import Path
text = Path('/tmp/src/README.rst').read_text(encoding='utf-8', errors='replace')
for needle in ['share/lcov/man', 'share/test', 'share/lcov/html', 'share/man']:
    print(f'NEEDLE={needle} PRESENT={str(needle in text).lower()}')
print('ACTUAL_MAN=/usr/local/share/man')
print('ACTUAL_TESTS=/usr/local/share/lcov/tests')
print('ACTUAL_HTML=/usr/local/share/lcov/html')
PY
    run_subject /tmp/src 60 -- python3 /tmp/extract_readme_paths.py
    write_tree_effects /tmp/src
    record_cleanup /tmp/src /tmp/extract_readme_paths.py
    ;;

  INST-REPORT-ASSET-001)
    prepare_src
    append_meta "FIXTURE=genhtml_asset_symbol_scan"
    append_meta "CLEANUP=rm -rf /tmp/src"
    cat > /tmp/scan_genhtml_assets.py <<'PY'
from pathlib import Path
import re
text = Path('/tmp/src/bin/genhtml').read_text(encoding='utf-8', errors='replace')
assets = sorted(set(re.findall(r'"(ruby\.png|amber\.png|emerald\.png|updown\.png|gcov\.css)"', text)))
print('ASSETS=' + ','.join(assets))
print('HAS_WRITE_CSS=' + str('write_css_file' in text).lower())
print('HAS_RATE_PNG=' + str('@rate_png' in text or 'rate_png' in text).lower())
print('OBSERVATION_COUNT=4')
print('OPTIONAL_UPDOWN_OPEN=true')
PY
    run_subject /tmp/src 60 -- python3 /tmp/scan_genhtml_assets.py
    write_tree_effects /tmp/src/bin
    record_cleanup /tmp/src /tmp/scan_genhtml_assets.py
    ;;

  INST-LICENSE-001)
    prepare_src
    append_meta "FIXTURE=copying_source_and_payload_probe"
    append_meta "CLEANUP=rm -rf /tmp/destdir-lic /tmp/src"
    (
      cd /tmp/src
      base_env_run make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-lic
    mkdir -p /tmp/destdir-lic
    run_subject /tmp/src 600 -- make install DESTDIR=/tmp/destdir-lic PREFIX=/usr/local
    {
      echo "SOURCE_HAS_COPYING=$([ -f /tmp/src/COPYING ] && echo yes || echo no)"
      echo "PAYLOAD_COPYING_COUNT=$(find /tmp/destdir-lic -name COPYING 2>/dev/null | wc -l)"
      echo "DIST_CONTENT_LINE=$(grep -n 'DIST_CONTENT' /tmp/src/Makefile | head -1)"
    } >"$OUT_DIR/observation.txt"
    write_tree_effects /tmp/destdir-lic
    record_cleanup /tmp/destdir-lic /tmp/src
    ;;

  # Runner qualification probes: retained executable evidence for signal/timeout.
  INST-RUNNER-SIGNAL-001)
    append_meta "FIXTURE=runner_qualification_signal"
    append_meta "CLEANUP=none_required"
    run_subject /tmp 30 signal -- sleep 30
    write_tree_effects /tmp
    echo "cleanup:none" >>"$CLEANUP_LOG"
    ;;

  INST-RUNNER-TIMEOUT-001)
    append_meta "FIXTURE=runner_qualification_timeout"
    append_meta "CLEANUP=none_required"
    run_subject /tmp 1 timeout -- sleep 30
    write_tree_effects /tmp
    echo "cleanup:none" >>"$CLEANUP_LOG"
    ;;

  *)
    echo "unknown case $CASE_ID" >&2
    exit 2
    ;;
esac

if [ ! -s "$STATUS_FILE" ]; then
  {
    echo "EXIT_STATUS=1"
    echo "SIGNAL="
    echo "TIMED_OUT=0"
    echo "HOST_OBSERVER_CODE=1"
    echo "WORKDIR="
  } >"$STATUS_FILE"
fi

append_meta "DONE=$CASE_ID"
