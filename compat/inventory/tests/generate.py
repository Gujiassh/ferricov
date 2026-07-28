#!/usr/bin/env python3
"""Generate the pinned LCOV v2.5 upstream-test inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
UPSTREAM_RELEASE = "v2.5"
EXPECTED_SOURCE_FILES = 205
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", REPOSITORY_ROOT.parent / "lcov-upstream-reference")
)
DEFAULT_OUTPUT = Path(__file__).with_name("upstream-test-map.json")


@dataclass(frozen=True)
class Context:
    owners: tuple[str, ...]
    groups: tuple[str, ...]
    subject: str
    evidence: tuple[str, ...] = ()


OWNERS = {
    "command:genhtml": ("command", "genhtml", "HTML report generator"),
    "command:geninfo": ("command", "geninfo", "GCC coverage capture command"),
    "command:lcov": ("command", "lcov", "Coverage capture and tracefile operations command"),
    "command:llvm2lcov": ("command", "llvm2lcov", "LLVM export converter"),
    "command:perl2lcov": ("command", "perl2lcov", "Devel::Cover database converter"),
    "command:py2lcov": ("command", "py2lcov", "Coverage.py database converter"),
    "command:xml2lcov": ("command", "xml2lcov", "Cobertura XML converter"),
    "support-script:P4version.pm": (
        "support_script",
        "P4version.pm",
        "Perforce version callback module",
    ),
    "support-script:batchGitVersion.pm": (
        "support_script",
        "batchGitVersion.pm",
        "Batch Git version callback module",
    ),
    "support-script:getp4version": (
        "support_script",
        "getp4version",
        "Perforce version callback executable",
    ),
    "support-script:gitblame": (
        "support_script",
        "gitblame",
        "Git annotation callback executable",
    ),
    "support-script:gitblame.pm": (
        "support_script",
        "gitblame.pm",
        "Git annotation callback module",
    ),
    "support-script:gitdiff": (
        "support_script",
        "gitdiff",
        "Git revision-diff helper",
    ),
    "support-script:gitversion": (
        "support_script",
        "gitversion",
        "Git version callback executable",
    ),
    "support-script:gitversion.pm": (
        "support_script",
        "gitversion.pm",
        "Git version callback module",
    ),
    "support-script:p4annotate": (
        "support_script",
        "p4annotate",
        "Perforce annotation callback executable",
    ),
    "support-script:p4annotate.pm": (
        "support_script",
        "p4annotate.pm",
        "Perforce annotation callback module",
    ),
    "support-script:p4udiff": (
        "support_script",
        "p4udiff",
        "Perforce revision-diff helper",
    ),
}


GROUPS = {
    "converter.llvm": "LLVM coverage JSON conversion, filtering, counters, and CLI failures.",
    "converter.perl": "Devel::Cover conversion, exclusions, checksums, and CLI failures.",
    "converter.python": "Coverage.py conversion, legacy input, exclusions, checksums, and CLI failures.",
    "converter.xml": "Cobertura XML conversion, version callbacks, aggregation, and CLI failures.",
    "coverage.mcdc": "GCC and LLVM MC/DC capture, conversion, filtering, merge, and report behavior.",
    "genhtml.coverage-rates": "HTML reports for synthetic zero, partial, target, and full coverage rates.",
    "genhtml.demangling": "C++ demangler command and argument behavior during report generation.",
    "genhtml.diagnostics-and-config": (
        "Shared CLI diagnostics, config inclusion, ignore handling, and callback failures."
    ),
    "genhtml.exception-differential": "Exception coverage and baseline/current differential report behavior.",
    "genhtml.function-differential": "Function extents, aliases, versions, and baseline/current categorization.",
    "genhtml.lambda-display": "Lambda function extents and display in HTML reports.",
    "genhtml.path-case": "Case-insensitive source paths, annotations, versions, and merge behavior.",
    "genhtml.relative-paths": "Relative source paths and report output path resolution.",
    "genhtml.report-options": "General HTML layout, callbacks, navigation, thresholds, and report options.",
    "genhtml.tracefile-synthesis": "Synthesis and rejection of missing or inconsistent tracefile coverpoints.",
    "geninfo.capture-cli": "Capture CLI help, errors, compatibility modes, recursion, temp paths, and initial capture.",
    "lcov.add-and-prune": "Tracefile addition, input ordering, pruning, and function mapping.",
    "lcov.branch-coverage": "GCC branch capture, filtering, merging, and source-level branch identities.",
    "lcov.capture-and-filter": "Capture paths, markers, callbacks, substitutions, checksums, and source filtering.",
    "lcov.demangling": "Demangling, simplification callbacks, exclusions, and function end lines.",
    "lcov.diagnostics": "Malformed tracefile, consistency, ignore, keep-going, and message-count behavior.",
    "lcov.exception-branches": "Exception branch capture and coverage filtering.",
    "lcov.follow-symlinks": "Follow and no-follow source-directory traversal behavior.",
    "lcov.format": "Tracefile record parsing, ordering, duplicate handling, and malformed input.",
    "lcov.gcov-tool": "Absolute, relative, missing, and default gcov tool resolution.",
    "lcov.initializer-filter": "C++ initializer-list coverage filtering during capture.",
    "lcov.lambda-filter": "Lambda function coalescing and derived function extents.",
    "lcov.multi-directory": "Initial capture across multiple directories and case-insensitive paths.",
    "lcov.operations-and-packages": "List, remove, intersect, subtract, package, and kernel-capture paths.",
    "lcov.set-operations": "Tracefile union, intersection, subtraction, and generated coverpoints.",
    "lcov.startup": "Help, version, option parsing, and startup output.",
    "lcov.summary": "Text summaries for synthetic and concatenated coverage inputs.",
    "shared.coverage-filter": "Source-driven line, branch, directive, brace, and trivial-function filters.",
    "support-script.batch-git-version": "Batch Git blob-version callback behavior.",
    "support-script.git-annotation": "Git source annotation callback behavior.",
    "support-script.git-diff": "Git revision-diff generation and filtering behavior.",
    "support-script.git-version": "Git source-version callback behavior.",
    "support-script.p4-annotation": "Perforce source annotation callback behavior.",
    "support-script.p4-diff": "Perforce revision-diff generation and filtering behavior.",
    "support-script.p4-version": "Perforce source-version callback behavior.",
    "test-harness.cleanup": "Test cleanup discovery and execution.",
    "test-harness.configuration": "Stable test command, environment, and configuration setup.",
    "test-harness.dependencies": "Test prerequisite discovery and validation.",
    "test-harness.documentation": "Upstream test-suite documentation.",
    "test-harness.execution": "Test process execution, isolation, and coverage wrapping.",
    "test-harness.orchestration": "Make-based test discovery and orchestration.",
    "test-harness.results": "Test logging, result accounting, skips, and resource reporting.",
    "test-harness.synthetic-tracefiles": "Generation and validation of synthetic tracefile inputs.",
}


def ctx(
    owners: tuple[str, ...],
    groups: tuple[str, ...],
    subject: str,
    evidence: tuple[str, ...] = (),
) -> Context:
    return Context(
        tuple(sorted(owners)),
        tuple(sorted(groups)),
        subject,
        tuple(sorted(evidence)),
    )


def file_contexts(context: Context, *paths: str) -> dict[str, Context]:
    return {path: context for path in paths}


DIRECTORY_CONTEXTS = {
    "genhtml/errs": ctx(
        ("command:genhtml", "command:geninfo", "command:lcov"),
        ("genhtml.diagnostics-and-config",),
        "diagnostic, configuration, and callback failure cases",
    ),
    "genhtml/exception": ctx(
        ("command:genhtml", "command:geninfo", "command:lcov", "command:llvm2lcov"),
        ("genhtml.exception-differential",),
        "exception coverage differential reports",
    ),
    "genhtml/filter": ctx(
        ("command:genhtml", "command:lcov"),
        ("shared.coverage-filter",),
        "source-driven coverage filters",
    ),
    "genhtml/function": ctx(
        ("command:genhtml", "command:lcov"),
        ("genhtml.function-differential",),
        "function differential reports",
    ),
    "genhtml/insensitive": ctx(
        ("command:genhtml", "command:lcov"),
        ("genhtml.path-case",),
        "case-insensitive path handling",
    ),
    "genhtml/lambda": ctx(
        ("command:genhtml", "command:lcov"),
        ("genhtml.lambda-display",),
        "lambda function report rendering",
    ),
    "genhtml/relative": ctx(
        ("command:genhtml",),
        ("genhtml.relative-paths",),
        "relative source paths",
    ),
    "genhtml/simple": ctx(
        ("command:genhtml", "command:lcov"),
        ("genhtml.report-options",),
        "general HTML report options and callbacks",
    ),
    "genhtml/synthesize": ctx(
        ("command:genhtml", "command:lcov"),
        ("genhtml.tracefile-synthesis",),
        "tracefile coverpoint synthesis",
    ),
    "lcov/add": ctx(
        ("command:lcov",),
        ("lcov.add-and-prune",),
        "tracefile addition, pruning, and function mapping",
    ),
    "lcov/branch": ctx(
        ("command:genhtml", "command:geninfo", "command:lcov"),
        ("lcov.branch-coverage",),
        "branch capture and merge behavior",
    ),
    "lcov/coverage": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.operations-and-packages",),
        "less common operation, package, capture, and CLI paths",
    ),
    "lcov/demangle": ctx(
        ("command:genhtml", "command:geninfo", "command:lcov"),
        ("lcov.demangling",),
        "demangling and simplification callbacks",
    ),
    "lcov/errs": ctx(
        ("command:lcov",),
        ("lcov.diagnostics",),
        "diagnostic and malformed tracefile behavior",
    ),
    "lcov/exception": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.exception-branches",),
        "exception branch capture and filtering",
    ),
    "lcov/extract": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.capture-and-filter",),
        "capture, extraction, callbacks, markers, and filtering",
    ),
    "lcov/follow": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.follow-symlinks",),
        "symbolic-link traversal",
    ),
    "lcov/format": ctx(
        ("command:lcov",),
        ("lcov.format",),
        "tracefile parsing and formatting",
    ),
    "lcov/gcov-tool": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.gcov-tool",),
        "gcov tool resolution",
    ),
    "lcov/initializer": ctx(
        ("command:geninfo",),
        ("lcov.initializer-filter",),
        "initializer-list filtering",
    ),
    "lcov/lambda": ctx(
        ("command:lcov",),
        ("lcov.lambda-filter",),
        "lambda function coalescing",
    ),
    "lcov/mcdc": ctx(
        ("command:genhtml", "command:geninfo", "command:llvm2lcov"),
        ("coverage.mcdc",),
        "MC/DC coverage across GCC and LLVM",
    ),
    "lcov/merge": ctx(
        ("command:lcov",),
        ("lcov.set-operations",),
        "tracefile set operations",
    ),
    "lcov/misc": ctx(
        ("command:lcov",),
        ("lcov.startup",),
        "startup help and version output",
    ),
    "lcov/multiple": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.multi-directory",),
        "multi-directory initial capture",
    ),
    "lcov/summary": ctx(
        ("command:lcov",),
        ("lcov.summary",),
        "coverage summary output",
    ),
    "llvm2lcov": ctx(
        ("command:llvm2lcov",),
        ("converter.llvm",),
        "LLVM JSON conversion",
    ),
    "perl2lcov": ctx(
        ("command:perl2lcov",),
        ("converter.perl",),
        "Devel::Cover conversion",
    ),
    "py2lcov": ctx(
        ("command:py2lcov",),
        ("converter.python",),
        "Coverage.py conversion",
    ),
    "xml2lcov": ctx(
        ("command:xml2lcov",),
        ("converter.xml",),
        "Cobertura XML conversion",
    ),
    "profiles": ctx(
        ("command:genhtml", "command:lcov"),
        ("test-harness.synthetic-tracefiles",),
        "synthetic tracefile size profiles",
    ),
}


FILE_CONTEXTS = {
    "genhtml/demangle.sh": ctx(
        ("command:genhtml",), ("genhtml.demangling",), "report-time C++ demangling"
    ),
    "genhtml/mycppfilt.sh": ctx(
        ("command:genhtml",),
        ("genhtml.demangling",),
        "report-time C++ demangler callback behavior",
        ("tests/genhtml/demangle.sh:42", "tests/genhtml/demangle.sh:129"),
    ),
    "genhtml/errs/select.sh": ctx(
        ("command:genhtml",),
        ("genhtml.diagnostics-and-config",),
        "selection-callback failure behavior",
        ("tests/genhtml/errs/msgtest.sh:530",),
    ),
    "genhtml/insensitive/annotate.sh": ctx(
        ("command:genhtml",),
        ("genhtml.path-case",),
        "case-insensitive annotation callback lookup",
        ("tests/genhtml/insensitive/insensitive.sh:133",),
    ),
    "genhtml/insensitive/version.sh": ctx(
        ("command:genhtml",),
        ("genhtml.path-case",),
        "case-insensitive version callback lookup",
        ("tests/genhtml/insensitive/insensitive.sh:30",),
    ),
    "genhtml/simple/annotate.sh": ctx(
        ("command:genhtml",),
        ("genhtml.report-options", "genhtml.tracefile-synthesis"),
        "annotation callbacks for report and synthesis behavior",
        ("tests/genhtml/simple/script.sh:439", "tests/genhtml/synthesize/synthesize.sh:32"),
    ),
    "genhtml/full.sh": ctx(
        ("command:genhtml",), ("genhtml.coverage-rates",), "full-coverage HTML output"
    ),
    "genhtml/part1.sh": ctx(
        ("command:genhtml",), ("genhtml.coverage-rates",), "partial-coverage HTML output"
    ),
    "genhtml/part2.sh": ctx(
        ("command:genhtml",), ("genhtml.coverage-rates",), "partial-coverage HTML output"
    ),
    "genhtml/target.sh": ctx(
        ("command:genhtml",), ("genhtml.coverage-rates",), "target-rate HTML output"
    ),
    "genhtml/zero.sh": ctx(
        ("command:genhtml",), ("genhtml.coverage-rates",), "zero-coverage HTML output"
    ),
    "lcovrc": ctx(
        ("command:genhtml", "command:lcov"),
        ("test-harness.configuration",),
        "the shared lcov and genhtml test configuration",
        ("tests/common.mak:69", "tests/common.mak:87", "tests/common.mak:88"),
    ),
    "lcov/coverage/coverage.sh": ctx(
        ("command:lcov",),
        ("lcov.operations-and-packages",),
        "less common operation, package, capture, and CLI paths",
    ),
    "lcov/coverage/geninfo.sh": ctx(
        ("command:geninfo",),
        ("geninfo.capture-cli",),
        "capture CLI and compatibility-mode paths",
    ),
    "lcov/extract/fakeResolve.sh": ctx(
        ("command:geninfo",),
        ("lcov.capture-and-filter",),
        "geninfo source-resolution callback behavior",
        ("tests/lcov/extract/extract.sh:984",),
    ),
    "lcov/extract/history.sh": ctx(
        ("command:geninfo",),
        ("lcov.capture-and-filter",),
        "geninfo history callback behavior",
        ("tests/lcov/extract/extract.sh:143",),
    ),
    "lcov/extract/testContext.sh": ctx(
        ("command:geninfo",),
        ("lcov.capture-and-filter",),
        "geninfo context callback success and failure behavior",
        ("tests/lcov/extract/extract.sh:374", "tests/lcov/extract/extract.sh:384"),
    ),
    "lcov/gcov-tool/mygcov.sh": ctx(
        ("command:geninfo", "command:lcov"),
        ("lcov.gcov-tool",),
        "absolute and relative gcov command-wrapper resolution",
        ("tests/lcov/gcov-tool/path.sh:80", "tests/lcov/gcov-tool/path.sh:92"),
    ),
    "scripts/batchgitversion_test.sh": ctx(
        ("support-script:batchGitVersion.pm",),
        ("support-script.batch-git-version",),
        "batch Git version callbacks",
    ),
    "scripts/gitblame_test.sh": ctx(
        ("support-script:gitblame", "support-script:gitblame.pm"),
        ("support-script.git-annotation",),
        "Git annotation callbacks",
    ),
    "scripts/gitdiff_test.sh": ctx(
        ("support-script:gitdiff",),
        ("support-script.git-diff",),
        "Git revision diffs",
    ),
    "scripts/gitversion_test.sh": ctx(
        ("support-script:gitversion", "support-script:gitversion.pm"),
        ("support-script.git-version",),
        "Git version callbacks",
    ),
    "scripts/p4annotate_test.sh": ctx(
        ("support-script:p4annotate", "support-script:p4annotate.pm"),
        ("support-script.p4-annotation",),
        "Perforce annotation callbacks",
    ),
    "scripts/p4udiff_test.sh": ctx(
        ("support-script:p4udiff",),
        ("support-script.p4-diff",),
        "Perforce revision diffs",
    ),
    "scripts/p4version_test.sh": ctx(
        ("support-script:P4version.pm", "support-script:getp4version"),
        ("support-script.p4-version",),
        "Perforce version callbacks",
    ),
}


FIXTURE_FILE_CONTEXTS = {
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.diagnostics-and-config",),
            "genhtml context-callback failure and expected-message diagnostics",
            ("tests/genhtml/errs/msgtest.sh:1001",),
        ),
        "genhtml/errs/MsgContext.pm",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.diagnostics-and-config",),
            "lcov and genhtml injected callback-failure diagnostics",
            (
                "tests/genhtml/errs/msgtest.sh:726",
                "tests/genhtml/errs/msgtest.sh:743",
                "tests/genhtml/errs/msgtest.sh:762",
                "tests/genhtml/errs/msgtest.sh:780",
            ),
        ),
        "genhtml/errs/genError.pm",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("genhtml.diagnostics-and-config",),
            "lcov diagnostics and ignore handling for inconsistent MC/DC records",
            ("tests/genhtml/errs/msgtest.sh:1161",),
        ),
        "genhtml/errs/mcdc_errs.dat",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.diagnostics-and-config",),
            "genhtml parallel callback packages missing restore lifecycle support",
            ("tests/genhtml/errs/msgtest.sh:839",),
        ),
        "genhtml/errs/missingRestore.pm",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.diagnostics-and-config",),
            "genhtml parallel callback lifecycle failure diagnostics",
            ("tests/genhtml/errs/msgtest.sh:800",),
        ),
        "genhtml/errs/parallelFail.pm",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:geninfo", "command:lcov", "command:llvm2lcov"),
            ("genhtml.exception-differential",),
            "GCC and LLVM exception coverage capture, merge, and differential reports",
            (
                "tests/genhtml/exception/exception.sh:53",
                "tests/genhtml/exception/exception.sh:69",
                "tests/genhtml/exception/exception.sh:100",
                "tests/genhtml/exception/exception.sh:169",
                "tests/genhtml/exception/exception.sh:207",
            ),
        ),
        "genhtml/exception/exception.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal filter-driver conditional detection and configuration behavior",
            ("tests/genhtml/filter/filter.pl:16", "tests/genhtml/filter/filter.pl:25"),
        ),
        "genhtml/filter/expr1.c",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal filter-driver conditional rejection behavior",
            ("tests/genhtml/filter/filter.pl:16",),
        ),
        "genhtml/filter/expr2.c",
        "genhtml/filter/expr3.c",
        "genhtml/filter/expr4.c",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal filter-driver trivial-function detection behavior",
            ("tests/genhtml/filter/filter.pl:43",),
        ),
        "genhtml/filter/multilineTrivial.c",
        "genhtml/filter/multilineTrivial2.c",
        "genhtml/filter/trivial1.c",
        "genhtml/filter/trivial2.c",
        "genhtml/filter/trivial3.c",
        "genhtml/filter/trivialMethod.c",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal filter-driver non-trivial-function rejection behavior",
            ("tests/genhtml/filter/filter.pl:43",),
        ),
        "genhtml/filter/notTrivial1.c",
        "genhtml/filter/notTrivial2.c",
        "genhtml/filter/notTrivial3.c",
        "genhtml/filter/notTrivial_init.c",
        "genhtml/filter/notTrivial_multiline.c",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal brace and directive source-filter behavior",
            ("tests/genhtml/filter/filter.pl:72", "tests/genhtml/filter/filter.pl:84"),
        ),
        "genhtml/filter/brace.c",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("shared.coverage-filter",),
            "internal brace and directive tracefile-filter totals",
            ("tests/genhtml/filter/filter.pl:74", "tests/genhtml/filter/filter.pl:90"),
        ),
        "genhtml/filter/brace.info",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.function-differential",),
            "genhtml expected function rows without function end-line records",
            (
                "tests/genhtml/function/function.sh:147",
                "tests/genhtml/function/function.sh:165",
                "tests/genhtml/function/function.sh:172",
                "tests/genhtml/function/function.sh:174",
            ),
        ),
        "genhtml/function/baseline_call_current_call.gold",
        "genhtml/function/baseline_call_current_nocall.gold",
        "genhtml/function/baseline_nocall_current_call.gold",
        "genhtml/function/baseline_nocall_current_nocall.gold",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.function-differential",),
            "genhtml expected function rows with function end-line records",
            (
                "tests/genhtml/function/function.sh:147",
                "tests/genhtml/function/function.sh:150",
                "tests/genhtml/function/function.sh:165",
                "tests/genhtml/function/function.sh:172",
                "tests/genhtml/function/function.sh:174",
            ),
        ),
        "genhtml/function/baseline_call_current_call_region.gold",
        "genhtml/function/baseline_call_current_nocall_region.gold",
        "genhtml/function/baseline_nocall_current_call_region.gold",
        "genhtml/function/baseline_nocall_current_nocall_region.gold",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.function-differential",),
            "baseline function capture, version, and differential categorization",
            (
                "tests/genhtml/function/function.sh:42",
                "tests/genhtml/function/function.sh:48",
                "tests/genhtml/function/function.sh:97",
                "tests/genhtml/function/function.sh:165",
            ),
        ),
        "genhtml/function/initial.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.function-differential",),
            "current function capture and changed-function differential categorization",
            (
                "tests/genhtml/function/function.sh:110",
                "tests/genhtml/function/function.sh:114",
                "tests/genhtml/function/function.sh:165",
            ),
        ),
        "genhtml/function/current.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.function-differential",),
            "function alias capture and genhtml alias suppression",
            (
                "tests/genhtml/function/function.sh:194",
                "tests/genhtml/function/function.sh:197",
                "tests/genhtml/function/function.sh:215",
            ),
        ),
        "genhtml/function/template.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.lambda-display",),
            "lambda function capture, extents, and HTML display",
            (
                "tests/genhtml/lambda/lambda.sh:36",
                "tests/genhtml/lambda/lambda.sh:46",
                "tests/genhtml/lambda/lambda.sh:55",
            ),
        ),
        "genhtml/lambda/lambda.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.relative-paths",),
            "genhtml relative source paths and synthesized report pages",
            ("tests/genhtml/relative/relative.sh:30", "tests/genhtml/relative/relative.sh:38"),
        ),
        "genhtml/relative/relative.info",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:geninfo", "command:lcov"),
            (
                "genhtml.diagnostics-and-config",
                "genhtml.path-case",
                "genhtml.report-options",
            ),
            "baseline source for report options, path-case, and diagnostics drivers",
            (
                "tests/genhtml/simple/script.sh:71",
                "tests/genhtml/insensitive/insensitive.sh:37",
                "tests/genhtml/errs/msgtest.sh:72",
            ),
        ),
        "genhtml/simple/simple.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.path-case", "genhtml.report-options", "genhtml.tracefile-synthesis"),
            "current source for report, path-case, and tracefile-synthesis drivers",
            (
                "tests/genhtml/simple/script.sh:317",
                "tests/genhtml/insensitive/insensitive.sh:110",
                "tests/genhtml/synthesize/synthesize.sh:30",
            ),
        ),
        "genhtml/simple/simple2.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.path-case", "genhtml.report-options", "genhtml.tracefile-synthesis"),
            "source annotation rows for report, path-case, and synthesis callbacks",
            (
                "tests/genhtml/simple/script.sh:1586",
                "tests/genhtml/insensitive/insensitive.sh:127",
                "tests/genhtml/synthesize/synthesize.sh:31",
            ),
        ),
        "genhtml/simple/simple2.cpp.annotated",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.report-options",),
            "genhtml unreachable branch and MC/DC exclusion reporting",
            (
                "tests/genhtml/simple/script.sh:1585",
                "tests/genhtml/simple/script.sh:1589",
                "tests/genhtml/simple/script.sh:1610",
            ),
        ),
        "genhtml/simple/unreach.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:lcov"),
            ("genhtml.tracefile-synthesis",),
            "out-of-range coverpoint mutation for genhtml and lcov diagnostics",
            (
                "tests/genhtml/synthesize/synthesize.sh:56",
                "tests/genhtml/synthesize/synthesize.sh:61",
                "tests/genhtml/synthesize/synthesize.sh:177",
            ),
        ),
        "genhtml/synthesize/munge.pl",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("genhtml.tracefile-synthesis",),
            "branch-without-line-coverpoint mutation for genhtml diagnostics",
            (
                "tests/genhtml/synthesize/synthesize.sh:59",
                "tests/genhtml/synthesize/synthesize.sh:143",
            ),
        ),
        "genhtml/synthesize/munge2.pl",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:geninfo", "command:lcov"),
            ("lcov.branch-coverage",),
            "normal and macro GCC branch capture, merge, and report categories",
            (
                "tests/lcov/branch/branch.sh:41",
                "tests/lcov/branch/branch.sh:53",
                "tests/lcov/branch/branch.sh:100",
                "tests/lcov/branch/branch.sh:144",
            ),
        ),
        "lcov/branch/branch.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:geninfo", "command:lcov"),
            ("lcov.demangling",),
            "capture-time demangling, function filtering, extents, and HTML simplification",
            (
                "tests/lcov/demangle/demangle.sh:35",
                "tests/lcov/demangle/demangle.sh:38",
                "tests/lcov/demangle/demangle.sh:75",
            ),
        ),
        "lcov/demangle/demangle.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml",),
            ("lcov.demangling",),
            "genhtml chained function-name simplification rules",
            ("tests/lcov/demangle/demangle.sh:73", "tests/lcov/demangle/demangle.sh:75"),
        ),
        "lcov/demangle/simplify.cmd",
        "lcov/demangle/simplify.pl",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "zero function-start and line record diagnostics",
            (
                "tests/lcov/errs/errs.sh:31",
                "tests/lcov/errs/errs.sh:33",
                "tests/lcov/errs/errs.sh:61",
            ),
        ),
        "lcov/errs/badFncLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "zero function-end and line record diagnostics",
            (
                "tests/lcov/errs/errs.sh:31",
                "tests/lcov/errs/errs.sh:33",
                "tests/lcov/errs/errs.sh:61",
            ),
        ),
        "lcov/errs/badFncEndLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "conflicting function end-line diagnostics and rewrite behavior",
            (
                "tests/lcov/errs/errs.sh:31",
                "tests/lcov/errs/errs.sh:33",
                "tests/lcov/errs/errs.sh:61",
            ),
        ),
        "lcov/errs/fncMismatch.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "zero branch and line location diagnostics",
            (
                "tests/lcov/errs/errs.sh:31",
                "tests/lcov/errs/errs.sh:33",
                "tests/lcov/errs/errs.sh:61",
            ),
        ),
        "lcov/errs/badBranchLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "zero line record diagnostics and rewrite behavior",
            (
                "tests/lcov/errs/errs.sh:31",
                "tests/lcov/errs/errs.sh:33",
                "tests/lcov/errs/errs.sh:61",
            ),
        ),
        "lcov/errs/badLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "undefined function-data record mismatch and ignore recovery",
            ("tests/lcov/errs/errs.sh:72", "tests/lcov/errs/errs.sh:74", "tests/lcov/errs/errs.sh:92"),
        ),
        "lcov/errs/noFunc.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "empty source-file record format failure and ignore recovery",
            (
                "tests/lcov/errs/errs.sh:102",
                "tests/lcov/errs/errs.sh:104",
                "tests/lcov/errs/errs.sh:122",
            ),
        ),
        "lcov/errs/emptyFileRecord.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "exception and condition branch merge identities plus input diagnostics",
            (
                "tests/lcov/errs/errs.sh:133",
                "tests/lcov/errs/errs.sh:137",
                "tests/lcov/errs/errs.sh:159",
            ),
        ),
        "lcov/errs/exceptionBranch1.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "exception-marker and condition-expression branch merge identities",
            ("tests/lcov/errs/errs.sh:133", "tests/lcov/errs/errs.sh:137"),
        ),
        "lcov/errs/exceptionBranch2.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "hit function without a hit contained line consistency diagnostics",
            (
                "tests/lcov/errs/errs.sh:214",
                "tests/lcov/errs/errs.sh:216",
                "tests/lcov/errs/errs.sh:224",
            ),
        ),
        "lcov/errs/funcNoLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "unhit function containing hit lines consistency diagnostics",
            (
                "tests/lcov/errs/errs.sh:214",
                "tests/lcov/errs/errs.sh:216",
                "tests/lcov/errs/errs.sh:224",
            ),
        ),
        "lcov/errs/lineNoFunc.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "evaluated branch on an unhit line consistency diagnostics",
            (
                "tests/lcov/errs/errs.sh:214",
                "tests/lcov/errs/errs.sh:216",
                "tests/lcov/errs/errs.sh:224",
            ),
        ),
        "lcov/errs/branchNoLine.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.diagnostics",),
            "hit line with unevaluated branches consistency diagnostics",
            (
                "tests/lcov/errs/errs.sh:214",
                "tests/lcov/errs/errs.sh:216",
                "tests/lcov/errs/errs.sh:224",
            ),
        ),
        "lcov/errs/lineNoBranch.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.exception-branches",),
            "exception-only, orphan-only, and combined branch filtering",
            (
                "tests/lcov/exception/exception.sh:232",
                "tests/lcov/exception/exception.sh:250",
                "tests/lcov/exception/exception.sh:257",
            ),
        ),
        "lcov/exception/example.data",
    ),
    **file_contexts(
        ctx(
            ("command:geninfo", "command:lcov"),
            ("lcov.exception-branches",),
            "initial exception-branch capture and exclusion-marker filtering",
            (
                "tests/lcov/exception/exception.sh:43",
                "tests/lcov/exception/exception.sh:52",
                "tests/lcov/exception/exception.sh:84",
            ),
        ),
        "lcov/exception/exception.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.capture-and-filter",),
            "lcov missing-source resolution callback error and ignore behavior",
            (
                "tests/lcov/extract/extract.sh:1057",
                "tests/lcov/extract/extract.sh:1072",
                "tests/lcov/extract/extract.sh:1087",
            ),
        ),
        "lcov/extract/brokenCallback.pm",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.capture-and-filter",),
            "lcov malformed ignore_errors configuration and format recovery",
            ("tests/lcov/extract/extract.sh:500", "tests/lcov/extract/extract.sh:509"),
        ),
        "lcov/extract/envErr.rc",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.capture-and-filter",),
            "lcov environment expansion and repeated ignore_errors configuration",
            (
                "tests/lcov/extract/extract.sh:472",
                "tests/lcov/extract/extract.sh:481",
                "tests/lcov/extract/extract.sh:491",
            ),
        ),
        "lcov/extract/envVar.rc",
    ),
    **file_contexts(
        ctx(
            ("command:geninfo", "command:lcov"),
            ("lcov.capture-and-filter",),
            "instrumented capture markers, callbacks, checksums, paths, and source filtering",
            (
                "tests/lcov/extract/extract.sh:55",
                "tests/lcov/extract/extract.sh:143",
                "tests/lcov/extract/extract.sh:405",
                "tests/lcov/extract/extract.sh:415",
                "tests/lcov/extract/extract.sh:984",
            ),
        ),
        "lcov/extract/extract.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.capture-and-filter",),
            "normalized non-MC/DC lcov list layout and totals",
            (
                "tests/lcov/extract/extract.sh:415",
                "tests/lcov/extract/extract.sh:422",
                "tests/lcov/extract/extract.sh:423",
            ),
        ),
        "lcov/extract/list.gold",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("coverage.mcdc", "lcov.capture-and-filter"),
            "exact GCC MC/DC lcov list layout and totals",
            (
                "tests/lcov/extract/extract.sh:415",
                "tests/lcov/extract/extract.sh:417",
                "tests/lcov/extract/extract.sh:418",
            ),
        ),
        "lcov/extract/list_mcdc.gold",
    ),
    **file_contexts(
        ctx(
            ("command:geninfo",),
            ("lcov.capture-and-filter",),
            "geninfo --all initial and regular capture of unlinked metadata",
            (
                "tests/lcov/extract/extract.sh:103",
                "tests/lcov/extract/extract.sh:117",
                "tests/lcov/extract/extract.sh:440",
            ),
        ),
        "lcov/extract/unused.c",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.format",),
            "malformed tracefile counts, branches, keep-going, and cleaned serialization",
            (
                "tests/lcov/format/format.sh:30",
                "tests/lcov/format/format.sh:45",
                "tests/lcov/format/format.sh:60",
                "tests/lcov/format/format.sh:119",
            ),
        ),
        "lcov/format/format.info",
    ),
    **file_contexts(
        ctx(
            ("command:geninfo", "command:lcov"),
            ("lcov.gcov-tool",),
            "default, named, absolute, relative, and missing gcov tool resolution",
            (
                "tests/lcov/gcov-tool/path.sh:37",
                "tests/lcov/gcov-tool/path.sh:51",
                "tests/lcov/gcov-tool/path.sh:80",
            ),
        ),
        "lcov/gcov-tool/test.c",
    ),
    **file_contexts(
        ctx(
            ("command:geninfo",),
            ("lcov.initializer-filter",),
            "C++ initializer-list coverage filtering and line-count changes",
            (
                "tests/lcov/initializer/initializer.sh:44",
                "tests/lcov/initializer/initializer.sh:54",
                "tests/lcov/initializer/initializer.sh:64",
            ),
        ),
        "lcov/initializer/initializer.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.lambda-filter",),
            "Java same-line lambda coalescing and enclosing function extents",
            ("tests/lcov/lambda/lambda.sh:19", "tests/lcov/lambda/lambda.sh:28"),
        ),
        "lcov/lambda/lambda.dat",
        "lcov/lambda/lambda2.dat",
    ),
    **file_contexts(
        ctx(
            ("command:genhtml", "command:geninfo", "command:llvm2lcov"),
            ("coverage.mcdc",),
            "GCC and LLVM MC/DC decision variants, conversion, filtering, and reports",
            (
                "tests/lcov/mcdc/mcdc.sh:39",
                "tests/lcov/mcdc/mcdc.sh:44",
                "tests/lcov/mcdc/mcdc.sh:55",
                "tests/lcov/mcdc/mcdc.sh:60",
                "tests/lcov/mcdc/mcdc.sh:87",
                "tests/lcov/mcdc/mcdc.sh:92",
                "tests/lcov/mcdc/mcdc.sh:94",
                "tests/lcov/mcdc/mcdc.sh:99",
            ),
        ),
        "lcov/mcdc/main.cpp",
        "lcov/mcdc/test.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "inconsistent duplicate function-location merge diagnostics",
            ("tests/lcov/merge/merge.sh:166", "tests/lcov/merge/merge.sh:175"),
        ),
        "lcov/merge/a.dat",
        "lcov/merge/b.dat",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "intersection and subtraction semantics across coverage record types",
            (
                "tests/lcov/merge/merge.sh:33",
                "tests/lcov/merge/merge.sh:41",
                "tests/lcov/merge/merge.sh:69",
                "tests/lcov/merge/merge.sh:86",
            ),
        ),
        "lcov/merge/a.info",
        "lcov/merge/b.info",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "exact a-minus-b subtraction output",
            ("tests/lcov/merge/merge.sh:77",),
        ),
        "lcov/merge/a_subtract_b.gold",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "exact b-minus-a subtraction output",
            ("tests/lcov/merge/merge.sh:94",),
        ),
        "lcov/merge/b_subtract_a.gold",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "cross-library function spelling and extent merge regression",
            ("tests/lcov/merge/merge.sh:145", "tests/lcov/merge/merge.sh:155"),
        ),
        "lcov/merge/functionBug_1.dat",
        "lcov/merge/functionBug_2.dat",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("lcov.set-operations",),
            "exact commutative intersection output",
            ("tests/lcov/merge/merge.sh:33", "tests/lcov/merge/merge.sh:59"),
        ),
        "lcov/merge/intersect.gold",
    ),
    **file_contexts(
        ctx(
            ("command:lcov",),
            ("coverage.mcdc", "lcov.set-operations"),
            "line-coverpoint synthesis for orphan MC/DC records",
            ("tests/lcov/merge/merge.sh:123", "tests/lcov/merge/merge.sh:133"),
        ),
        "lcov/merge/mcdc.dat",
    ),
    **file_contexts(
        ctx(
            ("command:llvm2lcov",),
            ("converter.llvm",),
            "LLVM JSON function, line, branch, MC/DC, macro, and exclusion conversion",
            (
                "tests/llvm2lcov/llvm2lcov.sh:43",
                "tests/llvm2lcov/llvm2lcov.sh:54",
                "tests/llvm2lcov/llvm2lcov.sh:61",
            ),
        ),
        "llvm2lcov/main.cpp",
    ),
    **file_contexts(
        ctx(
            ("command:llvm2lcov",),
            ("converter.llvm",),
            "LLVM header function and coverage-bearing macro conversion",
            (
                "tests/llvm2lcov/main.cpp:1",
                "tests/llvm2lcov/llvm2lcov.sh:43",
                "tests/llvm2lcov/llvm2lcov.sh:119",
            ),
        ),
        "llvm2lcov/test.h",
    ),
    **file_contexts(
        ctx(
            ("command:perl2lcov",),
            ("converter.perl",),
            "Devel::Cover functions, exclusions, checksums, filters, and conversion errors",
            (
                "tests/perl2lcov/perltest1.sh:22",
                "tests/perl2lcov/perltest1.sh:29",
                "tests/perl2lcov/perltest1.sh:119",
            ),
        ),
        "perl2lcov/example.pl",
    ),
    **file_contexts(
        ctx(
            ("command:py2lcov",),
            ("converter.python",),
            "Coverage.py imported function extents and branch-exclusion markers",
            ("tests/py2lcov/test.py:3", "tests/py2lcov/py2lcov.sh:67"),
        ),
        "py2lcov/localmodule.py",
    ),
    **file_contexts(
        ctx(
            ("command:py2lcov",),
            ("converter.python",),
            "Coverage.py direct and XML conversion, checksums, modes, and exclusions",
            (
                "tests/py2lcov/py2lcov.sh:67",
                "tests/py2lcov/py2lcov.sh:74",
                "tests/py2lcov/py2lcov.sh:127",
            ),
        ),
        "py2lcov/test.py",
    ),
    **file_contexts(
        ctx(
            ("command:xml2lcov",),
            ("converter.xml",),
            "Cobertura normal, verbose, version-callback, and CLI-error conversion",
            (
                "tests/xml2lcov/xml2lcov.sh:50",
                "tests/xml2lcov/xml2lcov.sh:59",
                "tests/xml2lcov/xml2lcov.sh:68",
                "tests/xml2lcov/xml2lcov.sh:93",
            ),
        ),
        "xml2lcov/coverage.xml",
    ),
}


PUBLIC_DRIVERS = {
    "genhtml/demangle.sh",
    "genhtml/errs/msgtest.sh",
    "genhtml/exception/exception.sh",
    "genhtml/filter/filter.pl",
    "genhtml/full.sh",
    "genhtml/function/function.sh",
    "genhtml/insensitive/insensitive.sh",
    "genhtml/lambda/lambda.sh",
    "genhtml/part1.sh",
    "genhtml/part2.sh",
    "genhtml/relative/relative.sh",
    "genhtml/simple/script.sh",
    "genhtml/synthesize/synthesize.sh",
    "genhtml/target.sh",
    "genhtml/zero.sh",
    "lcov/add/prune.sh",
    "lcov/add/track.sh",
    "lcov/branch/branch.sh",
    "lcov/coverage/coverage.sh",
    "lcov/coverage/geninfo.sh",
    "lcov/demangle/demangle.sh",
    "lcov/errs/errs.sh",
    "lcov/exception/exception.sh",
    "lcov/extract/extract.sh",
    "lcov/follow/follow.sh",
    "lcov/format/format.sh",
    "lcov/gcov-tool/path.sh",
    "lcov/initializer/initializer.sh",
    "lcov/lambda/lambda.sh",
    "lcov/mcdc/mcdc.sh",
    "lcov/merge/merge.sh",
    "lcov/misc/help.sh",
    "lcov/misc/version.sh",
    "lcov/multiple/multiple.sh",
    "lcov/summary/concatenated.sh",
    "lcov/summary/concatenated2.sh",
    "lcov/summary/full.sh",
    "lcov/summary/part1.sh",
    "lcov/summary/part2.sh",
    "lcov/summary/target.sh",
    "lcov/summary/zero.sh",
    "llvm2lcov/llvm2lcov.sh",
    "perl2lcov/perltest1.sh",
    "py2lcov/py2lcov.sh",
    "scripts/batchgitversion_test.sh",
    "scripts/gitblame_test.sh",
    "scripts/gitdiff_test.sh",
    "scripts/gitversion_test.sh",
    "scripts/p4annotate_test.sh",
    "scripts/p4udiff_test.sh",
    "scripts/p4version_test.sh",
    "xml2lcov/xml2lcov.sh",
}


DISABLED_DRIVERS = {
    "genhtml/part1.sh",
    "genhtml/part2.sh",
    "genhtml/target.sh",
    "lcov/summary/concatenated.sh",
    "lcov/summary/concatenated2.sh",
    "lcov/summary/part1.sh",
    "lcov/summary/part2.sh",
    "lcov/summary/target.sh",
}


FIXTURE_HELPERS = {
    "genhtml/errs/select.sh",
    "genhtml/insensitive/annotate.sh",
    "genhtml/insensitive/version.sh",
    "genhtml/mycppfilt.sh",
    "genhtml/simple/annotate.sh",
    "lcov/extract/fakeResolve.sh",
    "lcov/extract/history.sh",
    "lcov/extract/testContext.sh",
    "lcov/gcov-tool/mygcov.sh",
}


REVIEWED_FIXTURES = FIXTURE_HELPERS | {"lcovrc"} | set(FIXTURE_FILE_CONTEXTS)


FIXTURE_SUFFIXES = {
    ".annotated",
    ".c",
    ".cmd",
    ".cpp",
    ".dat",
    ".data",
    ".gold",
    ".h",
    ".info",
    ".pl",
    ".pm",
    ".py",
    ".rc",
    ".xml",
}


def run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def source_context(relative: str) -> Context:
    if relative in FIXTURE_FILE_CONTEXTS:
        return FIXTURE_FILE_CONTEXTS[relative]
    if relative in FILE_CONTEXTS:
        return FILE_CONTEXTS[relative]
    parent = Path(relative).parent.as_posix()
    while parent != ".":
        if parent in DIRECTORY_CONTEXTS:
            return DIRECTORY_CONTEXTS[parent]
        parent = Path(parent).parent.as_posix()
    raise ValueError(f"no reviewed behavior context for tests/{relative}")


def infrastructure_entry(relative: str, digest: str) -> dict[str, object] | None:
    source = f"tests/{relative}"
    if relative == "README.md":
        group = "test-harness.documentation"
        rationale = (
            "Upstream test-suite documentation; it describes the harness rather than "
            "an installed LCOV behavior."
        )
    elif relative == "Makefile" or Path(relative).name == "Makefile":
        group = "test-harness.orchestration"
        rationale = (
            "Upstream Makefile that selects or launches tests; it is harness "
            "orchestration, not an installed LCOV behavior."
        )
    elif relative == "common.mak":
        group = "test-harness.configuration"
        rationale = "Shared Make variables and test command setup; this is harness configuration."
    elif relative == "common.tst":
        group = "test-harness.configuration"
        rationale = (
            "Shared shell argument and environment setup sourced by test drivers; "
            "this is harness configuration."
        )
    elif relative in {"profiles/large", "profiles/medium", "profiles/small"}:
        group = "test-harness.synthetic-tracefiles"
        rationale = (
            "Synthetic size profile consumed only by the internal mkinfo harness at "
            "tests/common.mak:137; public commands consume the generated tracefiles, "
            "not this profile file, so no command owner applies."
        )
        return {
            "source": source,
            "sha256": digest,
            "classification": "internal_test_infrastructure",
            "review_status": "reviewed",
            "evidence_scope": "internal_only",
            "upstream_execution": "not_applicable",
            "owners": [],
            "behavior_groups": [group],
            "consumer_evidence": ["tests/common.mak:137"],
            "rationale": rationale,
        }
    elif relative.startswith("bin/"):
        roles = {
            "check_counts": ("test-harness.synthetic-tracefiles", "validates generated synthetic tracefile counts"),
            "checkdeps": ("test-harness.dependencies", "checks test executable prerequisites"),
            "cleantests.py": ("test-harness.cleanup", "discovers and cleans test targets"),
            "common": ("test-harness.results", "provides shared shell logging and result functions"),
            "common.py": ("test-harness.results", "provides shared Python logging and result functions"),
            "mkinfo": ("test-harness.synthetic-tracefiles", "generates synthetic tracefile inputs"),
            "runtests.py": ("test-harness.execution", "discovers and schedules test drivers"),
            "test_run": ("test-harness.execution", "executes and measures a test driver"),
            "test_skip": ("test-harness.results", "records an explicit test skip"),
            "test_worker.py": ("test-harness.execution", "runs an isolated test worker"),
            "testsuite_exit": ("test-harness.results", "aggregates final test results"),
            "testsuite_init": ("test-harness.results", "initializes logs and environment evidence"),
        }
        name = Path(relative).name
        if name not in roles:
            raise ValueError(f"unreviewed test harness executable: {source}")
        group, role = roles[name]
        rationale = f"Upstream harness utility that {role}; it does not exercise an installed LCOV surface by itself."
    else:
        return None
    return {
        "source": source,
        "sha256": digest,
        "classification": "internal_test_infrastructure",
        "review_status": "reviewed",
        "evidence_scope": "internal_only",
        "upstream_execution": "not_applicable",
        "owners": [],
        "behavior_groups": [group],
        "rationale": rationale,
    }


def fixture_rationale(relative: str, context: Context) -> str:
    if relative in FIXTURE_HELPERS:
        return (
            "Executable test double or callback fixture used to exercise "
            f"{context.subject}; it is not itself the asserted public surface."
        )
    name = Path(relative).name
    suffix = Path(relative).suffix
    if relative == "lcovrc":
        role = "configuration fixture"
    elif relative.startswith("profiles/"):
        role = "synthetic tracefile generation profile"
    elif suffix in {".c", ".cpp", ".h", ".pl", ".py"}:
        role = "source-program fixture"
    elif suffix in {".info", ".dat", ".data", ".xml"}:
        role = "coverage-input fixture"
    elif suffix == ".gold":
        role = "expected-output fixture"
    elif suffix in {".rc", ".cmd"}:
        role = "configuration or callback-input fixture"
    elif suffix == ".pm":
        role = "callback or injected-failure module fixture"
    elif suffix == ".annotated":
        role = "annotation-data fixture"
    else:
        raise ValueError(f"unreviewed fixture kind: tests/{relative}")
    return (
        f"Upstream {role} used in {context.subject}; it supports evidence but "
        "does not execute a public surface by itself."
    )


def classify(path: Path, tests_root: Path) -> dict[str, object]:
    relative = path.relative_to(tests_root).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    infrastructure = infrastructure_entry(relative, digest)
    if infrastructure is not None:
        return infrastructure

    context = source_context(relative)
    if relative in PUBLIC_DRIVERS:
        indirect = relative == "genhtml/filter/filter.pl"
        execution = "disabled" if relative in DISABLED_DRIVERS else "active"
        qualifier = (
            "It calls the internal lcovutil API, so it is indirect evidence for "
            "public filtering semantics and not standalone CLI proof."
            if indirect
            else "It invokes the assigned installed command or support script and asserts observable results."
        )
        return {
            "source": f"tests/{relative}",
            "sha256": digest,
            "classification": "public_behavior",
            "review_status": "reviewed",
            "evidence_scope": "indirect_public_behavior" if indirect else "direct_public_behavior",
            "upstream_execution": execution,
            "owners": list(context.owners),
            "behavior_groups": list(context.groups),
            "rationale": f"Upstream behavior driver for {context.subject}. {qualifier}",
        }

    is_known_fixture = (
        relative in FIXTURE_HELPERS
        or relative == "lcovrc"
        or relative.startswith("profiles/")
        or path.suffix in FIXTURE_SUFFIXES
    )
    if not is_known_fixture:
        raise ValueError(
            f"tests/{relative} has no explicit classification; add an unreviewed entry instead of guessing"
        )
    reviewed = relative in REVIEWED_FIXTURES
    if reviewed:
        if not context.evidence:
            raise ValueError(f"reviewed fixture lacks consumer evidence: tests/{relative}")
        owners = list(context.owners)
        rationale = fixture_rationale(relative, context)
        consumer_evidence = list(context.evidence)
    else:
        owners = []
        consumer_evidence = []
        rationale = (
            "Unreviewed fixture mapping: the file type and test directory identify it "
            f"as supporting {context.subject}, but its per-file consumers and owner "
            "assignment have not been manually verified."
        )
    return {
        "source": f"tests/{relative}",
        "sha256": digest,
        "classification": "fixture",
        "review_status": "reviewed" if reviewed else "unreviewed",
        "evidence_scope": "fixture_support",
        "upstream_execution": "supporting",
        "owners": owners,
        "behavior_groups": list(context.groups),
        "consumer_evidence": consumer_evidence,
        "rationale": rationale,
    }


def counter(
    entries: list[dict[str, object]], key: str, allowed_values: tuple[str, ...]
) -> dict[str, int]:
    counts = Counter(str(entry[key]) for entry in entries)
    return {value: counts[value] for value in sorted(allowed_values)}


def generate(upstream_root: Path) -> dict[str, object]:
    upstream_root = upstream_root.resolve()
    tests_root = upstream_root / "tests"
    if not tests_root.is_dir():
        raise ValueError(f"missing upstream tests directory: {tests_root}")

    head = run_git(upstream_root, "rev-parse", "HEAD")
    if head != UPSTREAM_COMMIT:
        raise ValueError(f"upstream HEAD is {head}, expected immutable commit {UPSTREAM_COMMIT}")
    dirty = run_git(upstream_root, "status", "--porcelain", "--untracked-files=all", "--", "tests")
    if dirty:
        raise ValueError("upstream tests tree is dirty; inventory must be generated from the pinned commit")

    paths = sorted(path for path in tests_root.rglob("*") if path.is_file())
    if len(paths) != EXPECTED_SOURCE_FILES:
        raise ValueError(f"found {len(paths)} upstream test files, expected {EXPECTED_SOURCE_FILES}")
    entries = [classify(path, tests_root) for path in paths]
    if [entry["source"] for entry in entries] != sorted(entry["source"] for entry in entries):
        raise AssertionError("entry generation is not source-sorted")

    owner_assigned = sum(bool(entry["owners"]) for entry in entries)
    unreviewed = sum(entry["review_status"] == "unreviewed" for entry in entries)
    return {
        "schema_version": 1,
        "upstream": {
            "release": UPSTREAM_RELEASE,
            "commit": UPSTREAM_COMMIT,
            "tests_tree": run_git(upstream_root, "rev-parse", "HEAD:tests"),
            "test_root": "tests",
        },
        "review_policy": (
            "Reviewed mappings come only from explicit driver, infrastructure, helper, "
            "and file rules. Other recognized fixtures retain a provisional directory-level "
            "behavior group with review_status unreviewed and no owner; generation must not "
            "infer a command or support-script owner from a similar filename."
        ),
        "owners": [
            {"id": owner_id, "kind": values[0], "name": values[1], "description": values[2]}
            for owner_id, values in sorted(OWNERS.items())
        ],
        "behavior_groups": [
            {"id": group_id, "description": description}
            for group_id, description in sorted(GROUPS.items())
        ],
        "totals": {
            "expected_source_files": EXPECTED_SOURCE_FILES,
            "mapped_source_files": len(entries),
            "unmapped_source_files": EXPECTED_SOURCE_FILES - len(entries),
            "classification": counter(
                entries,
                "classification",
                ("fixture", "internal_test_infrastructure", "public_behavior"),
            ),
            "review_status": counter(entries, "review_status", ("reviewed", "unreviewed")),
            "evidence_scope": counter(
                entries,
                "evidence_scope",
                (
                    "direct_public_behavior",
                    "fixture_support",
                    "indirect_public_behavior",
                    "internal_only",
                ),
            ),
            "upstream_execution": counter(
                entries,
                "upstream_execution",
                ("active", "disabled", "not_applicable", "supporting"),
            ),
            "owner_coverage": {
                "assigned": owner_assigned,
                "not_applicable_internal": sum(
                    entry["classification"] == "internal_test_infrastructure" and not entry["owners"]
                    for entry in entries
                ),
                "unresolved": unreviewed,
            },
        },
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        document = generate(args.upstream_root)
        rendered = json.dumps(document, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"upstream-test-map generation failed: {error}", file=sys.stderr)
        return 1
    print(
        f"wrote {args.output} with {document['totals']['mapped_source_files']} mapped files "
        f"at {document['upstream']['commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
