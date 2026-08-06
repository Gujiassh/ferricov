#!/bin/sh
# In-container driver for installation wave-2 Oracle captures.
# Invoked as: capture-driver.sh <CASE_ID> <OUT_DIR>
# Commands run under env -i with an explicit variable set; process outcomes
# (exit/signal/timeout/cwd/argv/env/tree) are observed, not declared.
set -eu

CASE_ID="${1:?case id required}"
OUT_DIR="${2:?out dir required}"
SRC_RO="${SRC_RO:-/src-ro}"
PIN_INV="${PIN_INV:-/tmp/python-objects.inv}"
PIN_PY="${PIN_PY:-/tmp/pin-intersphinx.py}"
DIR_RECORDER="${DIR_RECORDER:-/tmp/installed-tree-directories.sh}"

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

: >"$STDOUT_BIN"
: >"$STDERR_BIN"
: >"$META_JSON"
: >"$STATUS_FILE"
: >"$OBS_ENV"
: >"$CLEANUP_LOG"
printf '[]\n' >"$OBS_CHILDREN"

# Explicit clean environment for case commands (no inherited image secrets).
# PATH/HOME/TERM are the minimum required for make/perl/python tooling.
BASE_ENV="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
BASE_ENV="$BASE_ENV HOME=/tmp"
BASE_ENV="$BASE_ENV TERM=dumb"
BASE_ENV="$BASE_ENV LANG=C"
BASE_ENV="$BASE_ENV LC_ALL=C"
BASE_ENV="$BASE_ENV TZ=UTC"
BASE_ENV="$BASE_ENV PYTHONHASHSEED=0"
BASE_ENV="$BASE_ENV SOURCE_DATE_EPOCH=1783375223"
BASE_ENV="$BASE_ENV LCOV_BUILD_DATE=2026-07-06"
BASE_ENV="$BASE_ENV BUILD_DATE=2026-07-06"
BASE_ENV="$BASE_ENV VERSION=2.5"
BASE_ENV="$BASE_ENV RELEASE=beta"

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
    # pin script may need normal env; run under explicit env -i subset
    env -i $BASE_ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      python3 "$PIN_PY" /tmp/src/docs/conf.py /tmp/src/docs/python-objects.inv
  fi
}

record_cleanup() {
  # shellcheck disable=SC2068
  for target in "$@"; do
    if [ -e "$target" ] || [ -L "$target" ]; then
      rm -rf -- "$target"
      echo "removed:$target" >>"$CLEANUP_LOG"
    else
      echo "absent:$target" >>"$CLEANUP_LOG"
    fi
  done
}

# run_cmd WORKDIR TIMEOUT_SECONDS EXECUTABLE -- argv...
# Executes under env -i + timeout; records status, observed env, argv, cwd.
run_cmd() {
  workdir="$1"
  timeout_sec="$2"
  executable="$3"
  shift 3
  if [ "$1" = "--" ]; then
    shift
  fi

  # Serialize argv as JSON for host binding.
  python3 - "$OBS_ARGV" "$@" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:], indent=2) + "\n")
PY

  # Resolve executable identity from the actual binary that will run.
  if [ -e "$executable" ]; then
    exec_sha="$(sha256sum "$executable" | cut -d' ' -f1)"
  else
    exec_sha="$(printf '%064d' 0)"
  fi
  append_meta "EXECUTABLE_PATH=$executable"
  append_meta "EXECUTABLE_SHA256=$exec_sha"
  append_meta "WORKDIR=$workdir"
  append_meta "TIMEOUT_SECONDS=$timeout_sec"

  # Capture effective environment that will be used (env -i + BASE_ENV + extras).
  # EXTRA_ENV_ASSIGNMENTS is a newline-separated list of KEY=VALUE.
  {
    # shellcheck disable=SC2086
    env -i $BASE_ENV ${EXTRA_ENV:-} /usr/bin/env
  } | LC_ALL=C sort >"$OBS_ENV"

  set +e
  # shellcheck disable=SC2086
  (
    cd "$workdir" || exit 127
    # shellcheck disable=SC2086
    exec env -i $BASE_ENV ${EXTRA_ENV:-} /usr/bin/timeout --signal=TERM --kill-after=10s "${timeout_sec}s" "$@"
  ) >"$STDOUT_BIN" 2>"$STDERR_BIN"
  code=$?
  set -e

  timed_out=0
  signal=""
  exit_status=""
  if [ "$code" -eq 124 ]; then
    # GNU timeout: command timed out
    timed_out=1
    signal=15
    exit_status=""
  elif [ "$code" -eq 137 ]; then
    # kill-after SIGKILL
    timed_out=1
    signal=9
    exit_status=""
  elif [ "$code" -gt 128 ]; then
    signal=$((code - 128))
    exit_status=""
  else
    exit_status="$code"
  fi

  {
    echo "EXIT_STATUS=$exit_status"
    echo "SIGNAL=$signal"
    echo "TIMED_OUT=$timed_out"
    echo "HOST_OBSERVER_CODE=$code"
    echo "WORKDIR=$workdir"
  } >"$STATUS_FILE"

  # Single observed child: the timed command itself.
  python3 - "$OBS_CHILDREN" "$code" "$timed_out" "$signal" "$@" <<'PY'
import json, sys
from pathlib import Path
code = int(sys.argv[2])
timed_out = sys.argv[3] == "1"
signal = sys.argv[4]
argv = sys.argv[5:]
child = {
    "command": " ".join(argv),
    "argv": argv,
    "exit_status": None if timed_out or signal else code,
    "signal": int(signal) if signal else None,
    "timed_out": timed_out,
}
Path(sys.argv[1]).write_text(json.dumps([child], indent=2) + "\n")
PY
}

EXTRA_ENV=""

case "$CASE_ID" in
  INST-LAYOUT-001)
    append_meta "FIXTURE=image_payload_directories"
    append_meta "CLEANUP=none_required_read_only_payload_scan"
    run_cmd / 60 /usr/bin/find -- sh "$DIR_RECORDER" /usr/local
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
      # docs required for install; keep under same clean env
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-stage
    mkdir -p /tmp/destdir-stage
    run_cmd /tmp/src 600 /usr/bin/make -- make install DESTDIR=/tmp/destdir-stage PREFIX=/usr/local
    write_tree_effects /tmp/destdir-stage
    record_cleanup /tmp/destdir-stage /tmp/src
    ;;

  INST-INTERP-001)
    prepare_src
    EXTRA_ENV="LCOV_PERL=/opt/custom/bin/perl"
    append_meta "FIXTURE=clean_src_custom_LCOV_PERL"
    append_meta "CLEANUP=rm -rf /tmp/destdir-interp /tmp/src"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-interp
    mkdir -p /tmp/destdir-interp
    run_cmd /tmp/src 600 /usr/bin/make -- env LCOV_PERL=/opt/custom/bin/perl make install DESTDIR=/tmp/destdir-interp PREFIX=/usr/local
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
    run_cmd /tmp 60 /usr/bin/perl -- perl /tmp/config-probe.pl
    write_tree_effects /tmp/h1
    record_cleanup /tmp/h1 /tmp/lh /tmp/config-probe.pl
    ;;

  INST-UNINSTALL-001)
    prepare_src
    append_meta "FIXTURE=staged_install_with_foreign_sentinels"
    append_meta "CLEANUP=rm -rf /tmp/destdir-uninst /tmp/src"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-uninst
    mkdir -p /tmp/destdir-uninst
    (
      cd /tmp/src
      env -i $BASE_ENV make install DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local >>"$OUT_DIR/install.log" 2>&1
    )
    mkdir -p /tmp/destdir-uninst/usr/local/share/man/man1
    echo foreign > /tmp/destdir-uninst/usr/local/etc/foreign.conf
    echo extra > /tmp/destdir-uninst/usr/local/share/man/man1/extra.1
    run_cmd /tmp/src 600 /usr/bin/make -- make uninstall DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local
    write_tree_effects /tmp/destdir-uninst
    record_cleanup /tmp/destdir-uninst /tmp/src
    ;;

  INST-PARTIAL-001)
    prepare_src
    append_meta "FIXTURE=fake_install_wrapper_fail_after_count"
    append_meta "CLEANUP=rm -rf /tmp/partial /tmp/src /tmp/fake-install /tmp/install-count"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
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
    run_cmd /tmp/src 600 /usr/bin/make -- make install DESTDIR=/tmp/partial PREFIX=/usr/local INSTALL=/tmp/fake-install
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
    run_cmd /tmp/src 300 /usr/bin/make -- make install DESTDIR=/tmp/docfail PREFIX=/usr/local
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
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    run_cmd /tmp/src 120 /usr/bin/make -- make install DESTDIR=rel-dest PREFIX=/usr/local
    write_tree_effects /tmp/src/rel-dest
    record_cleanup /tmp/src
    ;;

  INST-PATH-SPACE-001)
    prepare_src
    append_meta "FIXTURE=space_containing_destdir"
    append_meta "CLEANUP=rm -rf /tmp/destdir space /tmp/src"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf "/tmp/destdir space"
    mkdir -p "/tmp/destdir space"
    # Pass DESTDIR with embedded space as a single argv element.
    run_cmd /tmp/src 300 /usr/bin/make -- make install "DESTDIR=/tmp/destdir space" PREFIX=/usr/local
    write_tree_effects "/tmp/destdir space"
    record_cleanup "/tmp/destdir space" /tmp/src
    ;;

  INST-DIRTY-ASSET-001)
    prepare_src
    append_meta "FIXTURE=untracked_script_in_scripts"
    append_meta "CLEANUP=rm -rf /tmp/destdir-dirty /tmp/src"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    printf '#!/bin/sh\necho dirty\n' > /tmp/src/scripts/zz_dirty_wave2_sentinel
    chmod +x /tmp/src/scripts/zz_dirty_wave2_sentinel
    rm -rf /tmp/destdir-dirty
    mkdir -p /tmp/destdir-dirty
    run_cmd /tmp/src 600 /usr/bin/make -- make install DESTDIR=/tmp/destdir-dirty PREFIX=/usr/local
    write_tree_effects /tmp/destdir-dirty
    record_cleanup /tmp/destdir-dirty /tmp/src
    ;;

  INST-TEST-RUN-001)
    append_meta "FIXTURE=installed_tests_unset_LCOV_HOME"
    append_meta "CLEANUP=none_required_read_only"
    # Observe make -np without LCOV_HOME (exact argv used by prior evidence).
    EXTRA_ENV=""
    # Unset LCOV_HOME by not including it; BASE_ENV has no LCOV_HOME.
    run_cmd /usr/local/share/lcov/tests 60 /usr/bin/make -- make -np
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
    run_cmd /tmp/src 60 /usr/bin/python3 -- python3 /tmp/extract_readme_paths.py
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
    run_cmd /tmp/src 60 /usr/bin/python3 -- python3 /tmp/scan_genhtml_assets.py
    write_tree_effects /tmp/src/bin
    record_cleanup /tmp/src /tmp/scan_genhtml_assets.py
    ;;

  INST-LICENSE-001)
    prepare_src
    append_meta "FIXTURE=copying_source_and_payload_probe"
    append_meta "CLEANUP=rm -rf /tmp/destdir-lic /tmp/src"
    (
      cd /tmp/src
      env -i $BASE_ENV make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    )
    rm -rf /tmp/destdir-lic
    mkdir -p /tmp/destdir-lic
    run_cmd /tmp/src 600 /usr/bin/make -- make install DESTDIR=/tmp/destdir-lic PREFIX=/usr/local
    {
      echo "SOURCE_HAS_COPYING=$([ -f /tmp/src/COPYING ] && echo yes || echo no)"
      echo "PAYLOAD_COPYING_COUNT=$(find /tmp/destdir-lic -name COPYING 2>/dev/null | wc -l)"
      echo "DIST_CONTENT_LINE=$(grep -n 'DIST_CONTENT' /tmp/src/Makefile | head -1)"
    } >"$OUT_DIR/observation.txt"
    write_tree_effects /tmp/destdir-lic
    record_cleanup /tmp/destdir-lic /tmp/src
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
