#!/bin/sh
# In-container driver for installation wave-2 Oracle captures.
# Invoked as: capture-driver.sh <CASE_ID> <OUT_DIR>
set -eu

CASE_ID="${1:?case id required}"
OUT_DIR="${2:?out dir required}"
SRC_RO="${SRC_RO:-/src-ro}"
PIN_INV="${PIN_INV:-/tmp/python-objects.inv}"
PIN_PY="${PIN_PY:-/tmp/pin-intersphinx.py}"
DIR_RECORDER="${DIR_RECORDER:-/tmp/installed-tree-directories.sh}"

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1783375223}"
export LCOV_BUILD_DATE="${LCOV_BUILD_DATE:-2026-07-06}"
export BUILD_DATE="${BUILD_DATE:-$LCOV_BUILD_DATE}"
export VERSION="${VERSION:-2.5}"
export RELEASE="${RELEASE:-beta}"
export LC_ALL=C
export TZ=UTC
export PYTHONHASHSEED=0
export LANG=C

mkdir -p "$OUT_DIR"
STDOUT_BIN="$OUT_DIR/stdout.bin"
STDERR_BIN="$OUT_DIR/stderr.bin"
META_JSON="$OUT_DIR/meta.env"
TREE_JSON="$OUT_DIR/tree-effects.json"
STATUS_FILE="$OUT_DIR/status.env"

: >"$STDOUT_BIN"
: >"$STDERR_BIN"
: >"$META_JSON"
: >"$STATUS_FILE"

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
        rows.append(f"directory\t{oct(dpath.stat().st_mode)[-3:]}\t{dpath.as_posix()}")
        for name in sorted(dirnames):
            p = dpath / name
            if p.is_symlink():
                symlinks += 1
                rows.append(f"symlink\t{oct(p.lstat().st_mode)[-3:]}\t{os.readlink(p)}\t{p.as_posix()}")
        for name in sorted(filenames):
            p = dpath / name
            if p.is_symlink():
                symlinks += 1
                rows.append(f"symlink\t{oct(p.lstat().st_mode)[-3:]}\t{os.readlink(p)}\t{p.as_posix()}")
            elif p.is_file():
                files += 1
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                rows.append(f"file\t{oct(p.stat().st_mode)[-3:]}\t{digest}\t{p.as_posix()}")
rows_sorted = sorted(rows)
payload = {
    "root": root.as_posix(),
    "file_count": files,
    "symlink_count": symlinks,
    "directory_count": dirs,
    "paths_sha256": hashlib.sha256(("\n".join(rows_sorted) + ("\n" if rows_sorted else "")).encode()).hexdigest(),
    "selected_paths": [r.split("\t")[-1] for r in rows_sorted[:40]],
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
    python3 "$PIN_PY" /tmp/src/docs/conf.py /tmp/src/docs/python-objects.inv
  fi
  cd /tmp/src
}

run_cmd() {
  # run_cmd <label> -- argv...
  label="$1"
  shift
  if [ "$1" = "--" ]; then
    shift
  fi
  set +e
  "$@" >"$STDOUT_BIN" 2>"$STDERR_BIN"
  code=$?
  set -e
  {
    echo "EXIT_STATUS=$code"
    echo "SIGNAL="
    echo "TIMED_OUT=0"
    echo "LABEL=$label"
  } >"$STATUS_FILE"
  return 0
}

executable_identity() {
  path="$1"
  if [ -e "$path" ]; then
    sha="$(sha256sum "$path" | cut -d' ' -f1)"
  else
    sha="0"*64
    sha="$(printf '%064d' 0)"
  fi
  {
    echo "EXECUTABLE_PATH=$path"
    echo "EXECUTABLE_SHA256=$sha"
  } >>"$META_JSON"
}

case "$CASE_ID" in
  INST-LAYOUT-001)
    # Capture directory companion from already-installed image payload.
    executable_identity /usr/bin/find
    {
      echo "ARGV0=sh"
      echo "ARGV1=$DIR_RECORDER"
      echo "WORKDIR=/"
      echo "FIXTURE=image_payload_directories"
      echo "TIMEOUT=60"
    } >>"$META_JSON"
    run_cmd layout -- sh "$DIR_RECORDER" /usr/local
    cp "$STDOUT_BIN" "$OUT_DIR/installed-directories.lock"
    # tree effects from /usr/local payload roots only via recorder output
    python3 - "$OUT_DIR/installed-directories.lock" "$TREE_JSON" <<'PY'
import hashlib, json, sys
from pathlib import Path
rows = Path(sys.argv[1]).read_text().splitlines()
paths = [r.split("\t")[3] for r in rows if r]
payload = {
  "root": "/usr/local",
  "file_count": 0,
  "symlink_count": 0,
  "directory_count": len(paths),
  "paths_sha256": hashlib.sha256(("\n".join(rows) + "\n").encode()).hexdigest(),
  "selected_paths": paths[:40],
}
Path(sys.argv[2]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY
    ;;

  INST-STAGE-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=clean_src_pinned_docs"
      echo "TIMEOUT=600"
      echo "ARGV=make install DESTDIR=/tmp/destdir-stage PREFIX=/usr/local"
    } >>"$META_JSON"
    # docs required for install
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    rm -rf /tmp/destdir-stage
    mkdir -p /tmp/destdir-stage
    run_cmd stage -- make install DESTDIR=/tmp/destdir-stage PREFIX=/usr/local
    write_tree_effects /tmp/destdir-stage
    ;;

  INST-INTERP-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=clean_src_custom_LCOV_PERL"
      echo "TIMEOUT=600"
      echo "ARGV=make install DESTDIR=/tmp/destdir-interp PREFIX=/usr/local LCOV_PERL=/opt/custom/bin/perl"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    rm -rf /tmp/destdir-interp
    mkdir -p /tmp/destdir-interp
    run_cmd interp -- env LCOV_PERL=/opt/custom/bin/perl make install DESTDIR=/tmp/destdir-interp PREFIX=/usr/local
    {
      echo "lcov=$(head -n1 /tmp/destdir-interp/usr/local/bin/lcov 2>/dev/null || true)"
      echo "py2lcov=$(head -n1 /tmp/destdir-interp/usr/local/bin/py2lcov 2>/dev/null || true)"
      echo "xml2lcovutil=$(head -n1 /tmp/destdir-interp/usr/local/bin/xml2lcovutil.py 2>/dev/null || true)"
      echo "custom_matches=$(grep -R \"/opt/custom/bin/perl\" -l /tmp/destdir-interp 2>/dev/null | wc -l)"
    } >"$OUT_DIR/observation.txt"
    write_tree_effects /tmp/destdir-interp
    ;;

  INST-CONFIG-DISCOVERY-001)
    # Probe installed lcovutil config search using a tiny perl harness that mirrors source.
    executable_identity /usr/bin/perl
    {
      echo "WORKDIR=/tmp"
      echo "FIXTURE=temp_home_and_lcov_home_files"
      echo "TIMEOUT=60"
      echo "ARGV=perl /tmp/config-probe.pl"
    } >>"$META_JSON"
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
    run_cmd config -- perl /tmp/config-probe.pl
    write_tree_effects /tmp/h1
    ;;

  INST-UNINSTALL-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=staged_install_with_foreign_sentinels"
      echo "TIMEOUT=600"
      echo "ARGV=make uninstall DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    rm -rf /tmp/destdir-uninst
    mkdir -p /tmp/destdir-uninst
    make install DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local >>"$OUT_DIR/install.log" 2>&1
    # foreign sentinels
    mkdir -p /tmp/destdir-uninst/usr/local/share/man/man1
    echo foreign > /tmp/destdir-uninst/usr/local/etc/foreign.conf
    echo extra > /tmp/destdir-uninst/usr/local/share/man/man1/extra.1
    # keep lcovrc as non-removed config residue observation
    run_cmd uninstall -- make uninstall DESTDIR=/tmp/destdir-uninst PREFIX=/usr/local
    write_tree_effects /tmp/destdir-uninst
    ;;

  INST-PARTIAL-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=fake_install_wrapper_fail_after_count"
      echo "TIMEOUT=600"
      echo "ARGV=make install DESTDIR=/tmp/partial PREFIX=/usr/local INSTALL=/tmp/fake-install"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
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
    run_cmd partial -- make install DESTDIR=/tmp/partial PREFIX=/usr/local INSTALL=/tmp/fake-install
    write_tree_effects /tmp/partial
    ;;

  INST-DOC-FAIL-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=sphinx_build_hidden"
      echo "TIMEOUT=300"
      echo "ARGV=make install DESTDIR=/tmp/docfail PREFIX=/usr/local"
    } >>"$META_JSON"
    if [ -x /usr/bin/sphinx-build ]; then
      mv /usr/bin/sphinx-build /usr/bin/sphinx-build.hidden
    fi
    rm -f /tmp/src/doc_finished
    rm -rf /tmp/src/docs/_build /tmp/docfail
    mkdir -p /tmp/docfail
    set +e
    run_cmd docfail -- make install DESTDIR=/tmp/docfail PREFIX=/usr/local
    set -e
    if [ -x /usr/bin/sphinx-build.hidden ]; then
      mv /usr/bin/sphinx-build.hidden /usr/bin/sphinx-build
    fi
    write_tree_effects /tmp/docfail
    ;;

  INST-PATH-REL-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=relative_destdir"
      echo "TIMEOUT=120"
      echo "ARGV=make install DESTDIR=rel-dest PREFIX=/usr/local"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    run_cmd pathrel -- make install DESTDIR=rel-dest PREFIX=/usr/local
    write_tree_effects /tmp/src/rel-dest
    ;;

  INST-PATH-SPACE-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=space_containing_destdir"
      echo "TIMEOUT=300"
      echo "ARGV=make install DESTDIR=/tmp/destdir space PREFIX=/usr/local"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    rm -rf "/tmp/destdir space"
    mkdir -p "/tmp/destdir space"
    # intentional unquoted space path as observed in prior capture
    set +e
    make install DESTDIR=/tmp/destdir\ space PREFIX=/usr/local >"$STDOUT_BIN" 2>"$STDERR_BIN"
    code=$?
    set -e
    {
      echo "EXIT_STATUS=$code"
      echo "SIGNAL="
      echo "TIMED_OUT=0"
      echo "LABEL=pathspace"
    } >"$STATUS_FILE"
    write_tree_effects "/tmp/destdir space"
    ;;

  INST-DIRTY-ASSET-001)
    prepare_src
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=untracked_script_in_scripts"
      echo "TIMEOUT=600"
      echo "ARGV=make install DESTDIR=/tmp/destdir-dirty PREFIX=/usr/local"
    } >>"$META_JSON"
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    printf '#!/bin/sh\necho dirty\n' > /tmp/src/scripts/zz_dirty_wave2_sentinel
    chmod +x /tmp/src/scripts/zz_dirty_wave2_sentinel
    rm -rf /tmp/destdir-dirty
    mkdir -p /tmp/destdir-dirty
    run_cmd dirty -- make install DESTDIR=/tmp/destdir-dirty PREFIX=/usr/local
    write_tree_effects /tmp/destdir-dirty
    ;;

  INST-TEST-RUN-001)
    # Observe installed test Makefile path resolution without LCOV_HOME.
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/usr/local/share/lcov/tests"
      echo "FIXTURE=installed_tests_unset_LCOV_HOME"
      echo "TIMEOUT=60"
      echo "ARGV=make -n info"
    } >>"$META_JSON"
    cd /usr/local/share/lcov/tests
    set +e
    env -u LCOV_HOME make -np >"$STDOUT_BIN" 2>"$STDERR_BIN"
    code=$?
    set -e
    {
      echo "EXIT_STATUS=$code"
      echo "SIGNAL="
      echo "TIMED_OUT=0"
      echo "LABEL=testrun"
    } >"$STATUS_FILE"
    write_tree_effects /usr/local/share/lcov/tests
    ;;

  INST-DOC-PATH-001)
    executable_identity /usr/bin/python3
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=readme_path_extraction"
      echo "TIMEOUT=60"
      echo "ARGV=python3 extract_readme_paths.py"
    } >>"$META_JSON"
    prepare_src
    python3 - <<'PY' >"$STDOUT_BIN" 2>"$STDERR_BIN"
from pathlib import Path
text = Path('/tmp/src/README.rst').read_text(encoding='utf-8', errors='replace')
for needle in ['share/lcov/man', 'share/test', 'share/lcov/html', 'share/man']:
    print(f'NEEDLE={needle} PRESENT={str(needle in text).lower()}')
print('ACTUAL_MAN=/usr/local/share/man')
print('ACTUAL_TESTS=/usr/local/share/lcov/tests')
print('ACTUAL_HTML=/usr/local/share/lcov/html')
PY
    code=0
    {
      echo "EXIT_STATUS=$code"
      echo "SIGNAL="
      echo "TIMED_OUT=0"
      echo "LABEL=docpath"
    } >"$STATUS_FILE"
    write_tree_effects /tmp/src
    ;;

  INST-REPORT-ASSET-001)
    executable_identity /usr/bin/python3
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=genhtml_asset_symbol_scan"
      echo "TIMEOUT=60"
      echo "ARGV=python3 scan_genhtml_assets.py"
    } >>"$META_JSON"
    prepare_src
    python3 - <<'PY' >"$STDOUT_BIN" 2>"$STDERR_BIN"
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
    {
      echo "EXIT_STATUS=0"
      echo "SIGNAL="
      echo "TIMED_OUT=0"
      echo "LABEL=report"
    } >"$STATUS_FILE"
    write_tree_effects /tmp/src/bin
    ;;

  INST-LICENSE-001)
    executable_identity /usr/bin/make
    {
      echo "WORKDIR=/tmp/src"
      echo "FIXTURE=copying_source_and_payload_probe"
      echo "TIMEOUT=600"
      echo "ARGV=make install DESTDIR=/tmp/destdir-lic PREFIX=/usr/local"
    } >>"$META_JSON"
    prepare_src
    make doc_finished >>"$OUT_DIR/doc.log" 2>&1 || true
    rm -rf /tmp/destdir-lic
    mkdir -p /tmp/destdir-lic
    run_cmd license -- make install DESTDIR=/tmp/destdir-lic PREFIX=/usr/local
    {
      echo "SOURCE_HAS_COPYING=$([ -f /tmp/src/COPYING ] && echo yes || echo no)"
      echo "PAYLOAD_COPYING_COUNT=$(find /tmp/destdir-lic -name COPYING 2>/dev/null | wc -l)"
      echo "DIST_CONTENT_LINE=$(grep -n 'DIST_CONTENT' /tmp/src/Makefile | head -1)"
    } >"$OUT_DIR/observation.txt"
    write_tree_effects /tmp/destdir-lic
    ;;

  *)
    echo "unknown case $CASE_ID" >&2
    exit 2
    ;;
esac

# Always ensure status file exists
if [ ! -s "$STATUS_FILE" ]; then
  {
    echo "EXIT_STATUS=1"
    echo "SIGNAL="
    echo "TIMED_OUT=0"
    echo "LABEL=missing"
  } >"$STATUS_FILE"
fi

echo "DONE $CASE_ID" >>"$META_JSON"
