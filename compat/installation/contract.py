#!/usr/bin/env python3
"""Generate and validate the fail-closed LCOV 2.5 installation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path(__file__).with_name("v2.5.json")
SCHEMA_PATH = ROOT / "compat/schema/installation-contract.schema.json"
UPSTREAM_COMMIT = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5"
DEFAULT_UPSTREAM_ROOT = Path(
    os.environ.get("LCOV_SOURCE_ROOT", ROOT.parent / "lcov-upstream-reference")
)
TREE_LOCK = ROOT / "compat/upstream/installed-tree.lock"
ORACLE_MANIFEST = ROOT / "compat/manifests/oracle-lcov-v2.5-smoke.json"
BENCHMARK_RESULT = ROOT / "compat/benchmarks/results/oracle-x86_64-linux-20260728/result.json"

EXPECTED_ARTIFACT_HASHES = {
    "compat/upstream/installed-tree.lock":
        "75edeea2799a5f13715df5dd119bc10614ee347aa5fc33e37fbeb21cafd8fd24",
    "compat/manifests/oracle-lcov-v2.5-smoke.json":
        "a15e953f5dfa176ac0d2f2b0c8668f190951f64e58a69bd9e63365e8eb3ea981",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/result.json":
        "851fe9ca0b81e5af95139d1daad84afad413e0da083cdee21266f3644e348131",
}

ASSET_SAMPLE_PATHS = (
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-000/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-001/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-measured-002/output-tree.json",
    "compat/benchmarks/results/oracle-x86_64-linux-20260728/samples/report-genhtml-default-warmup-000/output-tree.json",
)
EXPECTED_ASSET_SAMPLE_HASHES = {
    ASSET_SAMPLE_PATHS[0]: "6b45e6e2c1f7a9f55df111c47045d6a68e69c7f5f8a1b9f23ce49cad96af83a7",
    ASSET_SAMPLE_PATHS[1]: "c0c12cc0504942e99e2c5fa50dea8b053c16c0e2809987506626e6135b8fb01f",
    ASSET_SAMPLE_PATHS[2]: "f8e42c0433d562edc74210e69d64e959348851627b038f954ac78bb741a4c368",
    ASSET_SAMPLE_PATHS[3]: "6a457161384a125f32227957760a74109857fd28e1f29e59ee37159296641bab",
}
EXPECTED_SAMPLE_METADATA_HASHES = {
    str(Path(ASSET_SAMPLE_PATHS[0]).with_name("sample.json")):
        "2ff8dcf8efc631462f8a9a97cead439449bcc8367fc1433942d0d37d25558aa5",
    str(Path(ASSET_SAMPLE_PATHS[1]).with_name("sample.json")):
        "0feefe681ad1f21aeb8c352adee36746e2d97f6b911b6477b920a876a8724b5c",
    str(Path(ASSET_SAMPLE_PATHS[2]).with_name("sample.json")):
        "c65aed31ba534877c10ec17a60ca8a92f926e501e19ece9626b55a4f8d008cc4",
    str(Path(ASSET_SAMPLE_PATHS[3]).with_name("sample.json")):
        "f86f9774eba770f04da0c94f19caa24ef3730091040950bb811d20cee0d1b847",
}

CASE_RECORDS_PATH = Path(__file__).with_name("oracle-case-records.json")
CASE_RECORDS_SCHEMA_PATH = Path(__file__).with_name("oracle-case-records.schema.json")
EXPECTED_CASE_RECORDS_SHA256 = "18f57021031d5564e7d189866941a159127037b50bb5e94d1761812d6dfdf172"

WAVE2_DIR = Path(__file__).with_name("wave2")
WAVE2_CAPTURE_PATH = WAVE2_DIR / "oracle-capture.json"
WAVE2_EXPECTED_TABLE_PATH = WAVE2_DIR / "expected-case-table.json"
WAVE2_CASE_CAPTURE_SCHEMA_PATH = WAVE2_DIR / "oracle-case-capture.schema.json"
WAVE2_DIRECTORY_LOCK = WAVE2_DIR / "installed-directories.lock"
EXPECTED_WAVE2_DIRECTORY_COUNT = 57
EXPECTED_WAVE2_DIRECTORY_MODE = "755"
EXPECTED_WAVE2_DIRECTORY_LOCK_SHA256 = (
    "da6eb48da728b53821c6aa3fca632006b29c5bf3fad6b32fc2296ccc22f3c32e"
)
EXPECTED_WAVE2_CAPTURE_SHA256 = (
    "7673559a7b96794d11156de5f62d3398ef79e25511bc0297cd109d6c0f8c895e"
)
EXPECTED_WAVE2_EXPECTED_TABLE_SHA256 = (
    "a9ee30f2a79a12f56e82ee0c22fa36316c48e28bbbeb6bc1c53fbc8bd04c86b0"
)
EXPECTED_WAVE2_ORACLE_IMAGE_ID = (
    "sha256:b02cc645313ff5b0a09adc6d6ddeb5e670e48d64ac376b6b29b34b9d56eb80b7"
)
EXPECTED_WAVE2_UPSTREAM_COMMIT = UPSTREAM_COMMIT
EXPECTED_WAVE2_ARTIFACT_HASHES = {
    "compat/installation/wave2/.gitignore":
        "fcca98f8e6bef10bf1e43db285299794f99184cae864a09b03b0676a1b050e48",
    "compat/installation/wave2/capture-driver.sh":
        "cb9986e3a22508822b3d1f4e2d8c86cdaaa11f8ef8aa9626eff27a3ae8c1858e",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/capture.json":
        "a02241140ff594323750e606eb6fd19041ca890abf582d322254e904035a93e6",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/cleanup.log":
        "62e382b5fd53aac121e6271b7f9a3ea2d478b92f7d14bd99ee35ee5762c609fc",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/meta.env":
        "68415192eb23fcfb23365e1987bb9b45510a72f0f42bca1397e3baec1be5637e",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/observed-argv.json":
        "343e16d808c1bf21b38b59e5f56193039b1fe3bb8b2db503ecea4a93603fa701",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/observed-children.json":
        "c1c12e3379eb62a161d6956ec55b07ab195c977567b1ec6f8f325e3de314c4a3",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/run-meta.env":
        "3a1b62538dbf08b7f0e9ab9792f20ce59fc757e5d30d5c548d83e368e42f9bfa",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/status.env":
        "3a68ea3b64d17d579df06c6648e0fc6138c848b489aed765e6e6647655c0384d",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/stdout.bin":
        "370b73f4fa66265c73a96aa256ff91c82c552b688860de4b1b94190582ca7438",
    "compat/installation/wave2/cases/INST-CONFIG-DISCOVERY-001/tree-effects.json":
        "2d1284c7c5b9893a807c74266b83c7ce9c10e390901048fe2ab13a17f68408a2",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/capture.json":
        "2f8822ca11f6ca241824df2c3b11b2998e72b06725d7275892af3bdef986bdd7",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/cleanup.log":
        "99478234a5c6ec2e39f719d3b07dc98fce2a49cf2db13faf484edf02a23d192c",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/meta.env":
        "8bcb0c09099fa8a205c72a9f7c1eff101a9bf601f5b6a42bc82a15546f8fabac",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/observed-argv.json":
        "a2be4e32a13288eaa130078c88897a762f5f40f01198cf78531872b12d32e769",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/observed-children.json":
        "ab40db80bca5a3744148585b83510eabe81d02971068ac454c352f6d88f61d21",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/status.env":
        "41dd5638a146420fedca8df1c05fb974868b0333236f4db674ceabf4922bae37",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/stderr.bin":
        "1c671c7e99ff530451311814bbfdab043a8e7bae8a97accf02ab194aa595a53c",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/stdout.bin":
        "fd43b7b1eb74da0952f026b075c706cb0bea78b396d3cde437efb5080a07362d",
    "compat/installation/wave2/cases/INST-DIRTY-ASSET-001/tree-effects.json":
        "5867610e4434b68faf72e679fba975deba287f1e8316e8af25fe63823215dd22",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/capture.json":
        "ec9904320b14d9a783eb0cd1bb72e9da6254dda51233d8a6418c4bfa1da9db18",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/cleanup.log":
        "e39db0da629d9bc7d918ae901d2df227be1398380f3de9e5a20e7014368bfd09",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/meta.env":
        "1613a68f09c2aa49365ef8633a15b56b876bf02c9150dac4a38adb6c5f857e67",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/observed-argv.json":
        "c47f9d9a85008f3f7c4040318023c2562275d5d04bf42fbcef154f7af5097a64",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/observed-children.json":
        "c8d57936db9fe1abc199ce63ef65df62bf0457a735e6cd211c79ee701c8ff7ad",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/run-meta.env":
        "a5383b60663c8dd28d5af7c433e37840340de968d4f0c9456946820b44b53868",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/status.env":
        "36aa00299879cb87eb86330c82c3a905ccd1c5e510b6d76f30858a998618ff3b",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/stderr.bin":
        "0d9f796b4835c9e01cff30ed23335a6cb682b2a897b00b2d08f0f0eeec9be0de",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/stdout.bin":
        "23f07f060f3cb14c91561f1bbb69f4daac6830bd3b7afafa3cc61530d1ae5fa5",
    "compat/installation/wave2/cases/INST-DOC-FAIL-001/tree-effects.json":
        "52459946c102e3859cb822891f5e5c1fad41f680e2a000f1695daef2e50e4da9",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/capture.json":
        "98f0f2a5c09a7b5abf03c5a372bd89abd79003fa308d6acb627e916d8e6eac0f",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/cleanup.log":
        "ada6c6ae190c28ffd0213963ae4587505a602b6563e10520026c21e877ebf329",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/meta.env":
        "d1e82a25682ff8f65bd810c6671f9b9132cdd626a85a608a645763461087c6b8",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/observed-argv.json":
        "0cf1ce4ee559ba8a603e8f1b601f85743a74a552acc4303ed77ec78523e02b97",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/observed-children.json":
        "0cda629554661d186e6167efacfe87ff923caa6b2677e2d8cb72550bce5109c1",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/run-meta.env":
        "62a8ea19e931c8b7cf601cc056d9660ab6b7fa3e88f31d683a0636cbb7e54a53",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/status.env":
        "2459252f005e6907e1e2cb2d1dce9f57108f6cae0996e9e80ea16e5dd0f88a03",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/stdout.bin":
        "5ff7679291315f27f6ef621f97225fafc9829b52daedb10d4a8e87f20dc25ffa",
    "compat/installation/wave2/cases/INST-DOC-PATH-001/tree-effects.json":
        "581b0f8fe9c600a74d3c2d615acf7bf6de45bd1d313d706d14d9e407cd87ab11",
    "compat/installation/wave2/cases/INST-INTERP-001/capture.json":
        "d80f7ac10e68d298afdee113815e3b94605b9124f80abe86ae21b78ee8b33417",
    "compat/installation/wave2/cases/INST-INTERP-001/clean-env.env":
        "10d4cc4b0ccc7b30a5cf1283b889680d12519077a244be94bb943e9d7b79ec75",
    "compat/installation/wave2/cases/INST-INTERP-001/cleanup.log":
        "03c6e85a210205aa1bfbc16658a57a856a390054fa4d28e181f175dcda7a3b1d",
    "compat/installation/wave2/cases/INST-INTERP-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-INTERP-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-INTERP-001/meta.env":
        "f033c0f3832d38beea68a07e763f0954578000485d768df556a7987f8d8cd802",
    "compat/installation/wave2/cases/INST-INTERP-001/observation.txt":
        "e2712c806feef0de54ff0c6e8d4ba3389817bf18d8a26677e158981bc79c0eae",
    "compat/installation/wave2/cases/INST-INTERP-001/observed-argv.json":
        "966f95079f2e18460755f7b91e9355bfae36a513a06e43731fab9d9f5c73e606",
    "compat/installation/wave2/cases/INST-INTERP-001/observed-children.json":
        "a4ae4d01ec4607da701c5485c744d47afe6880025ad7d85411a5d09cb1b3cc17",
    "compat/installation/wave2/cases/INST-INTERP-001/observed-env.env":
        "10d4cc4b0ccc7b30a5cf1283b889680d12519077a244be94bb943e9d7b79ec75",
    "compat/installation/wave2/cases/INST-INTERP-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-INTERP-001/status.env":
        "41dd5638a146420fedca8df1c05fb974868b0333236f4db674ceabf4922bae37",
    "compat/installation/wave2/cases/INST-INTERP-001/stderr.bin":
        "1c671c7e99ff530451311814bbfdab043a8e7bae8a97accf02ab194aa595a53c",
    "compat/installation/wave2/cases/INST-INTERP-001/stdout.bin":
        "8ec59dcdae9493a815f7a3c6a10ac29ef94ab765845dba30c05849a4589c826a",
    "compat/installation/wave2/cases/INST-INTERP-001/tree-effects.json":
        "5b7c77c785a607ac78817102c536ff2b3387d76c7be015453532f0e0d9e8ec0f",
    "compat/installation/wave2/cases/INST-LAYOUT-001/capture.json":
        "926005131feb926b7d10a4d696afa00d4e280c7a5110f655f02a49d6134d8013",
    "compat/installation/wave2/cases/INST-LAYOUT-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-LAYOUT-001/cleanup.log":
        "6338824994cb575f7d0af9d95201e110bf1fbaa0bf3966ce8b2fa739a5cc5d4a",
    "compat/installation/wave2/cases/INST-LAYOUT-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-LAYOUT-001/installed-directories.lock":
        "da6eb48da728b53821c6aa3fca632006b29c5bf3fad6b32fc2296ccc22f3c32e",
    "compat/installation/wave2/cases/INST-LAYOUT-001/meta.env":
        "54aed9206464e09e87a9261e48a74c5a360473ed8a2eef86a8651f4858e75b51",
    "compat/installation/wave2/cases/INST-LAYOUT-001/observed-argv.json":
        "01ee064044bf24cd51f5522809af88433d99fcd8b304ceb1739751d71e263de1",
    "compat/installation/wave2/cases/INST-LAYOUT-001/observed-children.json":
        "d15874e7c6028735132c765285bb0a0eab2af361b1d1b9430616216bc761476b",
    "compat/installation/wave2/cases/INST-LAYOUT-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-LAYOUT-001/run-meta.env":
        "3d6018c4e1f966ca0a4827b1659e715e9e073d7edad9a7b92c8ad1cfcb247ddd",
    "compat/installation/wave2/cases/INST-LAYOUT-001/status.env":
        "576bcffdf88146ce65b9dd12d9a4515fa449151711de5c4c4f690c5db65a02ec",
    "compat/installation/wave2/cases/INST-LAYOUT-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/INST-LAYOUT-001/stdout.bin":
        "da6eb48da728b53821c6aa3fca632006b29c5bf3fad6b32fc2296ccc22f3c32e",
    "compat/installation/wave2/cases/INST-LAYOUT-001/tree-effects.json":
        "378e66e5e239309f8f9da9b52a99c85cc34ba2d943eda3bf022e45963b317044",
    "compat/installation/wave2/cases/INST-LICENSE-001/capture.json":
        "2d9a45e0825c707816554c7b58bcd27f9ac05f8bbafd8c24a1fd75ebb9a122b8",
    "compat/installation/wave2/cases/INST-LICENSE-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-LICENSE-001/cleanup.log":
        "96a6d3d834f8340048bec3375d71bcca339649d62c755ce9217a29807feabd79",
    "compat/installation/wave2/cases/INST-LICENSE-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-LICENSE-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-LICENSE-001/meta.env":
        "dc34d7ffe8c34649afb616519e44516fb21408513c50a338f0bea09e8e0535b4",
    "compat/installation/wave2/cases/INST-LICENSE-001/observation.txt":
        "b514c0103dc918f11ef5409e532d481f384f7cf6d0fe60e3eef21cece8f95b5e",
    "compat/installation/wave2/cases/INST-LICENSE-001/observed-argv.json":
        "38097403919598ebdfb5cfe960071265cb14b0d64130c610cd5782b0fb455d90",
    "compat/installation/wave2/cases/INST-LICENSE-001/observed-children.json":
        "ceaacebc1d2b636cbd8de6ce242c569c8198b670619c68517d6a8a39d0d78916",
    "compat/installation/wave2/cases/INST-LICENSE-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-LICENSE-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-LICENSE-001/status.env":
        "41dd5638a146420fedca8df1c05fb974868b0333236f4db674ceabf4922bae37",
    "compat/installation/wave2/cases/INST-LICENSE-001/stderr.bin":
        "1c671c7e99ff530451311814bbfdab043a8e7bae8a97accf02ab194aa595a53c",
    "compat/installation/wave2/cases/INST-LICENSE-001/stdout.bin":
        "72b6c461f512ef6e7a0c8d2839f4e00c352c1ddd983fc11a5dd599d6269ff4b6",
    "compat/installation/wave2/cases/INST-LICENSE-001/tree-effects.json":
        "afecb058af9a1a49fe33534e6aa56b13a57e75de06534bc4cc6678767b6b3015",
    "compat/installation/wave2/cases/INST-PARTIAL-001/capture.json":
        "708a05c719aa8414f5908e1e1d69c52ae3f17bcebcd4e231610aa2604741862b",
    "compat/installation/wave2/cases/INST-PARTIAL-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PARTIAL-001/cleanup.log":
        "4f50cb4eea17217ad7038d685850cf9b161a648196b139cb6ccc6612b5d90df4",
    "compat/installation/wave2/cases/INST-PARTIAL-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-PARTIAL-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-PARTIAL-001/meta.env":
        "04b971378be931ed41692ea563d578fb7a17b55cb696ca8d1c8323728050e42e",
    "compat/installation/wave2/cases/INST-PARTIAL-001/observed-argv.json":
        "99e01ffaabc29b9dab4e2784d90ce569a0107b59304590e4626b6cbcc1acc87e",
    "compat/installation/wave2/cases/INST-PARTIAL-001/observed-children.json":
        "94351781c5d31e69f4f1b2a22c8cea4b7704f20bfff635ea034815eb7ba7a410",
    "compat/installation/wave2/cases/INST-PARTIAL-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PARTIAL-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-PARTIAL-001/status.env":
        "654c6aed9436fe01b73d12d1791c62d2d32d4f6a22f513c25d279eb7727dbe87",
    "compat/installation/wave2/cases/INST-PARTIAL-001/stderr.bin":
        "e24a0f470fb8d5f9556632143a7b2700280b573979afad5c3da14689ef73773b",
    "compat/installation/wave2/cases/INST-PARTIAL-001/stdout.bin":
        "dc8e9504d8e2a4a3681c867b4c49f4280ab4111a879259c566fb83aa7164977e",
    "compat/installation/wave2/cases/INST-PARTIAL-001/tree-effects.json":
        "6d45f6ffcd44c0ea83efbfa8adbd65ca680c4dc571d14f0e60d45cf09070ba0a",
    "compat/installation/wave2/cases/INST-PATH-001/capture.json":
        "379ba30535620a8f9053fa298316eed6d469b9364180fa8a8dd44ac65c54a1dd",
    "compat/installation/wave2/cases/INST-PATH-001/relative/capture.json":
        "c2f8281633aadba4f8934043977aabe2d5db0e23e687daea74912f2762026f9b",
    "compat/installation/wave2/cases/INST-PATH-001/relative/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PATH-001/relative/cleanup.log":
        "2e744442a3bc798fc378fc80b1a3d30e570cbb156283b45b33f1a058a1179925",
    "compat/installation/wave2/cases/INST-PATH-001/relative/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-PATH-001/relative/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-PATH-001/relative/meta.env":
        "b8b1c84bb96bb3811232af85b5f2e5f7b609e2d58885704e107bf0b0961fa980",
    "compat/installation/wave2/cases/INST-PATH-001/relative/observed-argv.json":
        "12e40b7f8e84ba53e02ec53bfa25097e5b2c76cf9278eb654313020622dff5e5",
    "compat/installation/wave2/cases/INST-PATH-001/relative/observed-children.json":
        "2696e07342516a58a2901965a66a6e6f20b42114a5e6fcd06a9978c487ec2206",
    "compat/installation/wave2/cases/INST-PATH-001/relative/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PATH-001/relative/run-meta.env":
        "d7488fe2ee27d391fd42f62dfc1d502b839c6e1772ebabf4725d353feaca4235",
    "compat/installation/wave2/cases/INST-PATH-001/relative/status.env":
        "f23b7f19a2cd05739a72e7ec1f245a0201ba16910319616a94b14d46fa47d0b3",
    "compat/installation/wave2/cases/INST-PATH-001/relative/stderr.bin":
        "b9e2ade6cc441be7cdafcbe666305f621445d0bf7a835f7f887b5ce1d3093732",
    "compat/installation/wave2/cases/INST-PATH-001/relative/stdout.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/INST-PATH-001/relative/tree-effects.json":
        "fb67a85d82f30c0af3347dee2f2b87f5bde0a2689b94ef8288eb5049dd2836fc",
    "compat/installation/wave2/cases/INST-PATH-001/space/capture.json":
        "233a5dfd0d0f9608b7ae6e32d90e5a14fa87e60dfadbd4c07f88a454faad8de0",
    "compat/installation/wave2/cases/INST-PATH-001/space/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PATH-001/space/cleanup.log":
        "59c30a5f125020a83098ab0a0cb3f3a0134b89b0b3a0ab860c2e26c125afd1f8",
    "compat/installation/wave2/cases/INST-PATH-001/space/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-PATH-001/space/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-PATH-001/space/meta.env":
        "6c676d146d9a8006d19e69a5ff6529ecb6e2c070052ba12cdb22b9e9d3120cbb",
    "compat/installation/wave2/cases/INST-PATH-001/space/observed-argv.json":
        "022c1b693129c4c52730e0f188e2789d315750785f5db89ef5ae477145731d96",
    "compat/installation/wave2/cases/INST-PATH-001/space/observed-children.json":
        "7a0d967a43a129e07110cedc8a18a7d9585c0ffe9f319772a62eff31a3e157ef",
    "compat/installation/wave2/cases/INST-PATH-001/space/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-PATH-001/space/run-meta.env":
        "a5383b60663c8dd28d5af7c433e37840340de968d4f0c9456946820b44b53868",
    "compat/installation/wave2/cases/INST-PATH-001/space/status.env":
        "36aa00299879cb87eb86330c82c3a905ccd1c5e510b6d76f30858a998618ff3b",
    "compat/installation/wave2/cases/INST-PATH-001/space/stderr.bin":
        "2e696725fb8a1dcccdec20855f94b38ee86c65d80ec754c277559f40b02840de",
    "compat/installation/wave2/cases/INST-PATH-001/space/stdout.bin":
        "9c1c2bc44beb089ff7103020c5b19be6da066add6f6edf8687779e3fc0cb9aa5",
    "compat/installation/wave2/cases/INST-PATH-001/space/tree-effects.json":
        "1463d804b0012be616bc7f1c310e3390c4b83d3d9762f79950ed0a367cca93f7",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/capture.json":
        "9b29ecd5ad641767912d5fec9e70b97577bb5e643f6ec94218d8c707ebdbfdfc",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/cleanup.log":
        "d181bae991149dbfd99212ae0e1e43fa28ca483d16b93c0a33be617985955826",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/meta.env":
        "6e9cd95f7b2bb91032d1bea8e6ea55d87e8638a232d40689190d5fab8c24c1cb",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/observed-argv.json":
        "eb26c367b6f9930c211dd75f179dba72138c16f72ee83c8c9f7e6df945a2772b",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/observed-children.json":
        "606445e53ece487a0b3a723d790e627642d2b632027725f41386d2bb6603229e",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/run-meta.env":
        "62a8ea19e931c8b7cf601cc056d9660ab6b7fa3e88f31d683a0636cbb7e54a53",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/status.env":
        "2459252f005e6907e1e2cb2d1dce9f57108f6cae0996e9e80ea16e5dd0f88a03",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/stdout.bin":
        "22592f7ccb2935c3dca33c61970a2cfb3f7ecdd74c7975875d35a4b58e226ba4",
    "compat/installation/wave2/cases/INST-REPORT-ASSET-001/tree-effects.json":
        "7df7fd8f3a53dff56583d8fb73b02bf7e1aabb549902e9ae73f12424206df4b6",
    "compat/installation/wave2/cases/INST-STAGE-001/capture.json":
        "1482bca6d05137ceba7833bc65a0fa8e8046d8fc9cc0c597a943de0d3bf7e9b3",
    "compat/installation/wave2/cases/INST-STAGE-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-STAGE-001/cleanup.log":
        "8aaa09c2b1eeafe62f40673ece048a36b661b06cbb503fd8af674279f5e22c50",
    "compat/installation/wave2/cases/INST-STAGE-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-STAGE-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-STAGE-001/meta.env":
        "71bac395d84a2042426d89eb571cb714b20f0d85cbd87007ad0278717b146465",
    "compat/installation/wave2/cases/INST-STAGE-001/observed-argv.json":
        "e8e0fc52571cfbabdd40674d119b4c72e01dbd70d38bced12b50c9e6738c62b6",
    "compat/installation/wave2/cases/INST-STAGE-001/observed-children.json":
        "e54fdcac506224d3d7680338dba343da6324dcb14827c07e444a672d5ee1c23b",
    "compat/installation/wave2/cases/INST-STAGE-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-STAGE-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-STAGE-001/status.env":
        "41dd5638a146420fedca8df1c05fb974868b0333236f4db674ceabf4922bae37",
    "compat/installation/wave2/cases/INST-STAGE-001/stderr.bin":
        "1c671c7e99ff530451311814bbfdab043a8e7bae8a97accf02ab194aa595a53c",
    "compat/installation/wave2/cases/INST-STAGE-001/stdout.bin":
        "34c78bff707e0e956b39f2845519e78979b1c68bef4ad78c93884b91322b9e4e",
    "compat/installation/wave2/cases/INST-STAGE-001/tree-effects.json":
        "f91656248548da17a7a894a4c0db3a40c0948c1199d843c1716828ef5788c4e9",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/capture.json":
        "4e0dc998b0e0176c45b685b0106ebcdf501f2fd5743af598c599fdf8c7fa0413",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/cleanup.log":
        "6338824994cb575f7d0af9d95201e110bf1fbaa0bf3966ce8b2fa739a5cc5d4a",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/meta.env":
        "903bb74ec5e5e89e1acafe1d53c3ea3b7b05eeb19844ff01ecfacdd7dabce33f",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/observed-argv.json":
        "5b0e4a5619fde08d8b64ec8b35b7169b29d4e029de0d14cf9c7be148630438d9",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/observed-children.json":
        "d4663ece64df07d065779ab6332fefa2e6511bb3d6113110ba0c825f4fdfc57b",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/run-meta.env":
        "c328c565585ceb63e92c2faf2958d814a9ed97e1ec9a1c8ca20374d4403e2ade",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/status.env":
        "a949b9afa74f72a689d2e607d69d76f9a4e41b1e9349f323ca99d3f2bee4d32b",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/stderr.bin":
        "fea70f3bac590f8e420ca2fb65d8395bb46b1beadbf93169c67214acf8898c8f",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/stdout.bin":
        "279a529f3cfbb1149c1baa9e77baa4d47ffdddc6632b611e1912c0a18350fb25",
    "compat/installation/wave2/cases/INST-TEST-RUN-001/tree-effects.json":
        "996385e15d3d180ef69dd2757712a2fb251bc8c86144ac008ac2842da0d460e3",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/capture.json":
        "59fdee753fae44726c64f58c4bbe9cfe573b2213db9659b841c7babafc259eb7",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/cleanup.log":
        "409c7b2802faf81bbced07db77c50bf81daae1fc0564012f4cd993e7bef32ed0",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/doc.log":
        "6cdf2032487927db0e185a61ff11909412c8f37ed97cb01062b4f111e84b97ad",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/install.log":
        "f59b021f62f0f49ba8afcc8c70e38ba6a97d938ef2b2934f3cf1900d35084c96",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/meta.env":
        "b9baddff1ca714deabce1a62b7816865798bbc6b32248b6fbeb58fb84b378b07",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/observed-argv.json":
        "0fd741d1f5015373814d2dacdd7a2783e483120335db3c4298500977c25cef03",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/observed-children.json":
        "0e8e01a4e29e44d07d16f3ab6cbce02aa3131d979dbb740abf13a7d7ad4e8d08",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/run-meta.env":
        "8e78366ead726dd176744db1dbd4790d7ed07bce522a3a140555b335731cd089",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/status.env":
        "41dd5638a146420fedca8df1c05fb974868b0333236f4db674ceabf4922bae37",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/stderr.bin":
        "c95bafeca4c411a290e362c035a77dc4c3d6d6ebe7dbd87b6b41a6cb702605a8",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/stdout.bin":
        "060277f3e5be19c2b0ddb4ecdb087a1a117d1ee6ff13e9e10737deee69e3c2f3",
    "compat/installation/wave2/cases/INST-UNINSTALL-001/tree-effects.json":
        "7ba4a9e7c5d8f0d8c59ee3304c3fcce437c3e33c322d6b2dee6923e1da0b430c",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/capture.json":
        "ec676e86909734086a06aaf0cceef2fc71372642157fd77144c4844a1331a879",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/cleanup.log":
        "6338824994cb575f7d0af9d95201e110bf1fbaa0bf3966ce8b2fa739a5cc5d4a",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/meta.env":
        "fef8527ac244b751c496383dd888b45c5796c01c7570390b25839afbc23d455d",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/observed-argv.json":
        "676c6c95feb69f09c7bef9dd69096af132bcd9350c1ff7f4ec429e9cbc3ff666",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/observed-children.json":
        "308e80b7c0831c96565058d5f001185de9baf232c5a6e2ef74f783ae432befbd",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/run-meta.env":
        "a7e7a24e203eea8719cb99dc958b207b3c6c5148abd0e0910e3f0aa34f1e1dc3",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/status.env":
        "2b9512f84b629f141dfda93edfea4b08a6b787bd9e3b96ab73d136b4d0e456a4",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/stdout.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-SIGNAL-001/tree-effects.json":
        "0c157a8fadc9b4c2a03194c6ef51bf0cb3eb2eac106f9df8d9633584f3c04e03",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/capture.json":
        "20bf2d64533f91c1889c31a356899de2cb682729441e01329ea2a64d4c388317",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/clean-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/cleanup.log":
        "6338824994cb575f7d0af9d95201e110bf1fbaa0bf3966ce8b2fa739a5cc5d4a",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/host-observer.txt":
        "5a09a06817f7773e8f2f272c32999e91ee576b28b3b5f507706ad2a63b922ef1",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/meta.env":
        "3423a96d9e08fe418f68be6ee1ef6cce2b644647bafd99e173b590fb2add4fcb",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/observed-argv.json":
        "676c6c95feb69f09c7bef9dd69096af132bcd9350c1ff7f4ec429e9cbc3ff666",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/observed-children.json":
        "263f300ea2b98446112de42924a77c9f6174d88605df8e7beba7bc52586d7b44",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/observed-env.env":
        "8a4893a5f071b396d547d5b3d10357dbfbb61178ada1f0972fabfe8c9688fb4c",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/run-meta.env":
        "0db86c7ce11b13f2af71fbd6521903d6af8c112de6037c7eb8c512925fa66762",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/status.env":
        "344b2eb7b00c158e693f62b74454eec6aab3c94b675bd4c1ca4c78a06b50d338",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/stderr.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/stdout.bin":
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compat/installation/wave2/cases/_runner/INST-RUNNER-TIMEOUT-001/tree-effects.json":
        "0c157a8fadc9b4c2a03194c6ef51bf0cb3eb2eac106f9df8d9633584f3c04e03",
    "compat/installation/wave2/expected-case-table.json":
        "a9ee30f2a79a12f56e82ee0c22fa36316c48e28bbbeb6bc1c53fbc8bd04c86b0",
    "compat/installation/wave2/installed-directories.lock":
        "da6eb48da728b53821c6aa3fca632006b29c5bf3fad6b32fc2296ccc22f3c32e",
    "compat/installation/wave2/installed-tree-directories.sh":
        "e16713b25dcd71651cf9d2f5ea63b0df87aa0ae201979c70be500f7e1d0da557",
    "compat/installation/wave2/oracle-capture.json":
        "7673559a7b96794d11156de5f62d3398ef79e25511bc0297cd109d6c0f8c895e",
    "compat/installation/wave2/oracle-case-capture.schema.json":
        "457523cb98604b38e761017c2c2fd133ae42732070cfc5d308f39afb55142771",
    "compat/installation/wave2/oracle-image.pin":
        "f22fdba249a35092246f20148f7a49b8e3ffb74d5512268e63f12d17c31c51a1",
    "compat/installation/wave2/process-observer.py":
        "fc8ce4ba2c98b1708405dab9ef7d37669a4ff866c6899939b0477721343875d5",
    "compat/installation/wave2/recapture.py":
        "2a4023ac1738e5a2a0e66ecd530a56fdd90cd1432f9f153bf694aedca9093ce4",
}

LAYOUT_IDS = (
    "INST-PATHS-001",
    "INST-BIN-001",
    "INST-SCRIPT-001",
    "INST-LIB-001",
    "INST-MAN-001",
    "INST-HTML-001",
    "INST-EXAMPLE-001",
    "INST-CONFIG-001",
    "INST-REPORT-ASSET-001",
)
FAILURE_IDS = (
    "INST-INTERP-001",
    "INST-CONFIG-DISCOVERY-001",
    "INST-UNINSTALL-001",
    "INST-PARTIAL-001",
    "INST-PATH-001",
    "INST-DIRTY-ASSET-001",
    "INST-DOC-FAIL-001",
    "INST-TEST-RUN-001",
    "INST-DOC-PATH-001",
    "INST-LICENSE-001",
)
PLANNED_CASE_IDS = (
    "INST-LAYOUT-001",
    "INST-STAGE-001",
    "INST-INTERP-001",
    "INST-CONFIG-DISCOVERY-001",
    "INST-UNINSTALL-001",
    "INST-PARTIAL-001",
    "INST-DOC-FAIL-001",
    "INST-PATH-001",
    "INST-DIRTY-ASSET-001",
    "INST-TEST-RUN-001",
    "INST-DOC-PATH-001",
    "INST-REPORT-ASSET-001",
    "INST-LICENSE-001",
)
CASE_RECORD_ORDER = PLANNED_CASE_IDS
CASE_FAMILY_BY_ID = {
    "INST-LAYOUT-001": "layout",
    "INST-STAGE-001": "lifecycle",
    "INST-INTERP-001": "failure",
    "INST-CONFIG-DISCOVERY-001": "failure",
    "INST-UNINSTALL-001": "failure",
    "INST-PARTIAL-001": "failure",
    "INST-DOC-FAIL-001": "failure",
    "INST-PATH-001": "failure",
    "INST-DIRTY-ASSET-001": "failure",
    "INST-TEST-RUN-001": "failure",
    "INST-DOC-PATH-001": "failure",
    "INST-REPORT-ASSET-001": "asset",
    "INST-LICENSE-001": "license",
}
CASE_ROLE_BY_ID = {
    "INST-LAYOUT-001": "installed_tree_partition",
    "INST-STAGE-001": "staged_root_versus_prefix",
    "INST-INTERP-001": "interpreter_fixup_ineffective",
    "INST-CONFIG-DISCOVERY-001": "config_discovery_precedence",
    "INST-UNINSTALL-001": "uninstall_residue_and_recursive_removal",
    "INST-PARTIAL-001": "non_transactional_install_loops",
    "INST-DOC-FAIL-001": "documentation_prerequisite_before_payload",
    "INST-PATH-001": "install_root_path_variants",
    "INST-DIRTY-ASSET-001": "dynamic_working_tree_enumeration",
    "INST-TEST-RUN-001": "installed_test_runtime_paths",
    "INST-DOC-PATH-001": "documented_path_mismatch",
    "INST-REPORT-ASSET-001": "runtime_report_assets",
    "INST-LICENSE-001": "distribution_license_manifest",
}
CASE_SOURCE_CLOSURE_IDS = {
    "INST-LAYOUT-001": ("installation.make-variables", "installation.make-doc-install"),
    "INST-STAGE-001": ("installation.make-variables", "installation.make-doc-install"),
    "INST-INTERP-001": ("installation.fixup", "installation.make-doc-install"),
    "INST-CONFIG-DISCOVERY-001": ("installation.config-discovery",),
    "INST-UNINSTALL-001": ("installation.make-uninstall", "installation.make-doc-install"),
    "INST-PARTIAL-001": ("installation.make-doc-install",),
    "INST-DOC-FAIL-001": (
        "installation.make-doc-install",
        "installation.docs-build",
        "installation.docs-config",
    ),
    "INST-PATH-001": ("installation.make-variables", "installation.make-doc-install"),
    "INST-DIRTY-ASSET-001": ("installation.make-variables", "installation.make-doc-install"),
    "INST-TEST-RUN-001": (
        "installation.test-runtime",
        "installation.test-paths",
        "installation.test-readme",
    ),
    "INST-DOC-PATH-001": ("installation.readme-paths", "installation.make-variables"),
    "INST-REPORT-ASSET-001": (
        "installation.asset-names",
        "installation.asset-generation",
        "installation.asset-writers",
    ),
    "INST-LICENSE-001": ("installation.make-variables", "installation.make-doc-install"),
}
CASE_LAYOUT_IDS = {
    "INST-LAYOUT-001": (
        "INST-PATHS-001",
        "INST-BIN-001",
        "INST-SCRIPT-001",
        "INST-LIB-001",
        "INST-MAN-001",
        "INST-HTML-001",
        "INST-EXAMPLE-001",
        "INST-CONFIG-001",
    ),
    "INST-STAGE-001": ("INST-PATHS-001",),
    "INST-INTERP-001": (),
    "INST-CONFIG-DISCOVERY-001": ("INST-CONFIG-001",),
    "INST-UNINSTALL-001": ("INST-MAN-001",),
    "INST-PARTIAL-001": (),
    "INST-DOC-FAIL-001": (),
    "INST-PATH-001": ("INST-PATHS-001",),
    "INST-DIRTY-ASSET-001": ("INST-SCRIPT-001", "INST-EXAMPLE-001"),
    "INST-TEST-RUN-001": (),
    "INST-DOC-PATH-001": ("INST-PATHS-001", "INST-MAN-001"),
    "INST-REPORT-ASSET-001": ("INST-REPORT-ASSET-001",),
    "INST-LICENSE-001": (),
}
CASE_FAILURE_IDS = {
    "INST-LAYOUT-001": (),
    "INST-STAGE-001": (),
    "INST-INTERP-001": ("INST-INTERP-001",),
    "INST-CONFIG-DISCOVERY-001": ("INST-CONFIG-DISCOVERY-001",),
    "INST-UNINSTALL-001": ("INST-UNINSTALL-001",),
    "INST-PARTIAL-001": ("INST-PARTIAL-001",),
    "INST-DOC-FAIL-001": ("INST-DOC-FAIL-001",),
    "INST-PATH-001": ("INST-PATH-001",),
    "INST-DIRTY-ASSET-001": ("INST-DIRTY-ASSET-001",),
    "INST-TEST-RUN-001": ("INST-TEST-RUN-001",),
    "INST-DOC-PATH-001": ("INST-DOC-PATH-001",),
    "INST-REPORT-ASSET-001": (),
    "INST-LICENSE-001": ("INST-LICENSE-001",),
}

SOURCE_CLOSURES = (
    ("installation.make-variables", "Makefile", 38, 84, "install_variables"),
    ("installation.make-doc-install", "Makefile", 125, 190, "install_recipe"),
    ("installation.make-uninstall", "Makefile", 194, 223, "uninstall_recipe"),
    ("installation.fixup", "bin/fix.pl", 89, 139, "interpreter_fixup"),
    ("installation.docs-build", "docs/Makefile", 4, 22, "documentation_build"),
    ("installation.docs-config", "docs/conf.py", 34, 63, "documentation_config"),
    ("installation.man-pages", "docs/conf.py", 83, 153, "man_page_generation"),
    ("installation.config-discovery", "lib/lcovutil.pm", 1448, 1460, "config_discovery"),
    ("installation.test-runtime", "tests/common.mak", 2, 18, "installed_test_runtime"),
    ("installation.test-paths", "tests/common.mak", 76, 83, "installed_test_paths"),
    ("installation.test-readme", "tests/README.md", 13, 18, "installed_test_docs"),
    ("installation.readme-paths", "README.rst", 125, 139, "documented_paths"),
    ("installation.asset-names", "bin/genhtml", 7128, 7128, "report_asset_names"),
    ("installation.asset-generation", "bin/genhtml", 7952, 7952, "report_asset_generation"),
    ("installation.asset-writers", "bin/genhtml", 8822, 9046, "report_asset_writers"),
)

EXPECTED_GROUPS = (
    ("bin", "/usr/local/bin/", 10, ("file",), ("755",)),
    ("config", "/usr/local/etc/lcovrc", 1, ("file",), ("644",)),
    ("lib", "/usr/local/lib/lcov/lcovutil.pm", 1, ("file",), ("644",)),
    ("man", "/usr/local/share/man/", 10, ("file",), ("644",)),
    ("support_scripts", "/usr/local/share/lcov/support-scripts/", 23, ("file",), ("755",)),
    ("html", "/usr/local/share/lcov/html/", 60, ("file",), ("644",)),
    ("example", "/usr/local/share/lcov/example/", 10, ("file",), ("644",)),
    ("tests", "/usr/local/share/lcov/tests/", 205, ("file",), ("644", "755")),
    ("legacy_man_symlink", "/usr/local/man", 1, ("symlink",), ("777",)),
)

EXPECTED_ASSETS = (
    ("gcov-css", "gcov.css", "css", 24155, "a302edd3a3f0ec66ffb0c1c41946ea9f6d6c14856906ebdcf5d8f8d81f03fa5d"),
    ("ruby-png", "ruby.png", "png", 141, "a2332ef8c44727042b0ab36628aaf562b0d5b0df43c6fa73c5191dfac50ec7be"),
    ("amber-png", "amber.png", "png", 141, "dff576889b1ebdb619eeb69f12d503f7c431d5ff321838624b804ea5bda86fcb"),
    ("emerald-png", "emerald.png", "png", 141, "8479273af3556e10f0feb96d8ac24fbd9615b0d887437c0f85f8ef6638e56b83"),
    ("snow-png", "snow.png", "png", 141, "53c50fc490fcf2ad290819b05f8033b1cbdad698e230bdcbac63564942c34723"),
    ("glass-png", "glass.png", "png", 167, "936a969e16ba5de4db2c9bcacd197b22a276e3d636335ba7f347da4009fc9cc5"),
    ("updown-png", "updown.png", "png", 117, "a851165a175f4ca2649a4e30291192dd71131ea02a93cf46464953e74c1c5f0c"),
)

EVIDENCE_GAPS = (
    "baseline installed-tree.lock still excludes directory rows; wave2 companion lock retains 57 directory modes",
    "staged DESTDIR installs omit the image-only legacy /usr/local/man symlink",
    "optional genhtml updown variants and HTML-reference qualification remain open",
    "space-containing DESTDIR failure is observed on this GNU/Linux install path only",
    "induced partial-install uses a fake install wrapper rather than native Makefile fault injection points",
    "no multi-platform install root matrix beyond the pinned x86_64 Linux Oracle image",
    "packaging/RPM distribution license policy remains uncaptured",
    "no Ferricov product installer, uninstall, or report-renderer compatibility evidence",
    "M1 parser/model installation surfaces remain blocked",
    "wave2 captures are Oracle-reference only and keep execution_status=planned",
    "directory companion is not verified inside the Docker image build diff against installed-tree.lock",
    "config discovery probe mirrors lcovutil search order without executing every consumer binary path",
    "report-asset capture scans genhtml symbols and does not execute HTML rendering",
)


class InstallationContractError(RuntimeError):
    pass


def canonical_json(document: object) -> str:
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallationContractError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise InstallationContractError(f"expected JSON object: {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_closure(upstream_root: Path, closure: tuple[str, str, int, int, str]) -> dict[str, Any]:
    identifier, path, start, end, role = closure
    try:
        lines = (upstream_root / path).read_text(encoding="utf-8").splitlines()
        selected = lines[start - 1:end]
    except (OSError, IndexError) as error:
        raise InstallationContractError(f"cannot read source closure {path}:{start}-{end}") from error
    if len(selected) != end - start + 1:
        raise InstallationContractError(f"short source closure {path}:{start}-{end}")
    content = ("\n".join(selected) + "\n").encode("utf-8")
    return {
        "id": identifier,
        "path": path,
        "line_start": start,
        "line_end": end,
        "line_count": len(selected),
        "role": role,
        "sha256": sha256_bytes(content),
    }


def artifact_bindings() -> list[dict[str, str]]:
    result = []
    for relative, expected in EXPECTED_ARTIFACT_HASHES.items():
        path = ROOT / relative
        actual = sha256_file(path)
        if actual != expected:
            raise InstallationContractError(
                f"retained installation artifact drift: {relative} expected={expected} actual={actual}"
            )
        result.append({"path": relative, "sha256": actual})
    for bindings, label in (
        (EXPECTED_ASSET_SAMPLE_HASHES, "asset sample"),
        (EXPECTED_SAMPLE_METADATA_HASHES, "sample metadata"),
    ):
        for relative, expected in bindings.items():
            actual = sha256_file(ROOT / relative)
            if actual != expected:
                raise InstallationContractError(
                    f"retained {label} drift: {relative} expected={expected} actual={actual}"
                )
            result.append({"path": relative, "sha256": actual})
    result.extend(wave2_artifact_bindings())
    return result


def parse_tree() -> list[dict[str, str]]:
    entries = []
    for raw in TREE_LOCK.read_text(encoding="ascii").splitlines():
        fields = raw.split("\t")
        if len(fields) != 4:
            raise InstallationContractError("installed-tree.lock has a malformed row")
        kind, mode, identity, path = fields
        if kind not in {"file", "symlink"} or not re.fullmatch(r"[0-7]{3}", mode):
            raise InstallationContractError(f"installed-tree.lock has an invalid row: {raw}")
        parsed_path = PurePosixPath(path)
        if (
            not parsed_path.is_absolute()
            or parsed_path.parts[:3] != ("/", "usr", "local")
            or ".." in parsed_path.parts
            or parsed_path.as_posix() != path
        ):
            raise InstallationContractError(f"installed tree has an invalid path: {path}")
        if kind == "file" and not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise InstallationContractError(f"installed tree file identity is not SHA-256: {path}")
        if kind == "symlink" and (path, mode, identity) != ("/usr/local/man", "777", "share/man"):
            raise InstallationContractError(f"installed tree legacy symlink drift: {path}")
        entries.append({"kind": kind, "mode": mode, "identity": identity, "path": path})
    if len(entries) != 321:
        raise InstallationContractError(f"installed tree must contain 321 entries, found {len(entries)}")
    paths = [entry["path"] for entry in entries]
    if len(set(paths)) != len(entries):
        raise InstallationContractError("installed tree contains duplicate paths")
    if paths != sorted(paths):
        raise InstallationContractError("installed tree paths are not in lexicographic order")
    return entries


def group_for_path(path: str) -> tuple[str, str]:
    prefixes = (
        ("bin", "/usr/local/bin/"),
        ("config", "/usr/local/etc/lcovrc"),
        ("lib", "/usr/local/lib/lcov/lcovutil.pm"),
        ("man", "/usr/local/share/man/"),
        ("support_scripts", "/usr/local/share/lcov/support-scripts/"),
        ("html", "/usr/local/share/lcov/html/"),
        ("example", "/usr/local/share/lcov/example/"),
        ("tests", "/usr/local/share/lcov/tests/"),
        ("legacy_man_symlink", "/usr/local/man"),
    )
    matches = [
        (name, prefix)
        for name, prefix in prefixes
        if (path.startswith(prefix) if prefix.endswith("/") else path == prefix)
    ]
    if len(matches) != 1:
        raise InstallationContractError(f"installed path does not belong to exactly one group: {path}")
    return matches[0]


def installed_tree() -> dict[str, Any]:
    entries = parse_tree()
    groups = []
    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        name, prefix = group_for_path(entry["path"])
        grouped.setdefault(name, []).append(entry)
    for name, prefix, count, kinds, modes in EXPECTED_GROUPS:
        current = grouped.get(name, [])
        if len(current) != count:
            raise InstallationContractError(f"installed tree group {name} count drift")
        if {entry["kind"] for entry in current} != set(kinds):
            raise InstallationContractError(f"installed tree group {name} kind drift")
        if {entry["mode"] for entry in current} != set(modes):
            raise InstallationContractError(f"installed tree group {name} mode drift")
        raw = "\n".join(
            "\t".join((entry["kind"], entry["mode"], entry["identity"], entry["path"]))
            for entry in current
        ) + "\n"
        groups.append({
            "id": f"installation.tree.{name}",
            "name": name,
            "path_prefix": prefix,
            "entry_count": len(current),
            "kinds": sorted({entry["kind"] for entry in current}),
            "modes": sorted({entry["mode"] for entry in current}),
            "entries_sha256": sha256_bytes(raw.encode("ascii")),
        })
    if sum(group["entry_count"] for group in groups) != len(entries):
        raise InstallationContractError("installed tree groups are not exhaustive")
    mode_counts: dict[str, int] = {}
    for entry in entries:
        mode_counts[entry["mode"]] = mode_counts.get(entry["mode"], 0) + 1
    kind_counts: dict[str, int] = {}
    for entry in entries:
        kind_counts[entry["kind"]] = kind_counts.get(entry["kind"], 0) + 1
    return {
        "manifest_path": "compat/upstream/installed-tree.lock",
        "manifest_sha256": sha256_file(TREE_LOCK),
        "path_root": "/usr/local",
        "path_order": "lexicographic",
        "file_identity_algorithm": "sha256",
        "legacy_symlink": {
            "path": "/usr/local/man",
            "target": "share/man",
            "mode": "777",
        },
        "entry_count": len(entries),
        "file_count": kind_counts["file"],
        "symlink_count": kind_counts["symlink"],
        "mode_counts": mode_counts,
        "directory_entries_retained": False,
        "groups": groups,
    }


def planned_case_ids(upstream_root: Path) -> list[str]:
    path = ROOT / "specs/001-full-lcov-compatibility/callback-installation-contract.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("### Support And Installation Cases")
    end = text.index("### `perl2lcov` Cases", start)
    found = []
    for identifier in re.findall(r"`(INST-[A-Z0-9-]+)`", text[start:end]):
        if identifier not in found:
            found.append(identifier)
    if tuple(found) != PLANNED_CASE_IDS:
        raise InstallationContractError(f"installation planned-case catalog drift: {found}")
    return found


def observed_runtime_assets(
    document: object,
    relative: str,
    expected_by_name: dict[str, dict[str, Any]],
) -> dict[str, dict[str, object]]:
    if not isinstance(document, list):
        raise InstallationContractError(f"asset sample is not a tree list: {relative}")
    observed: dict[str, dict[str, object]] = {}
    observed_paths = set()
    for entry in document:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if not isinstance(path, str) or not path.startswith("html/"):
            continue
        name = path.removeprefix("html/")
        if name not in expected_by_name:
            continue
        if path in observed_paths:
            raise InstallationContractError(f"duplicate runtime asset path: {relative}:{path}")
        observed_paths.add(path)
        observed[name] = {
            "bytes": entry.get("bytes"),
            "sha256": str(entry.get("sha256", "")).removeprefix("sha256:"),
            "status": entry.get("status"),
        }
    expected_observed = {
        name: {"bytes": asset["bytes"], "sha256": asset["sha256"], "status": "created"}
        for name, asset in expected_by_name.items()
    }
    if observed != expected_observed:
        raise InstallationContractError(f"runtime asset observation drift: {relative}")
    return observed


def validate_sample_metadata(relative: str, artifact_path: Path) -> tuple[str, str]:
    sample_relative = str(Path(relative).with_name("sample.json"))
    sample = load_json(ROOT / sample_relative)
    sample_id = Path(relative).parent.name
    expected_phase = "warmup" if "-warmup-" in sample_id else "measured"
    if (
        sample.get("case_id") != "report-genhtml-default"
        or sample.get("sample_id") != sample_id
        or sample.get("phase") != expected_phase
    ):
        raise InstallationContractError(f"runtime asset sample identity drift: {sample_relative}")
    artifacts = sample.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("output_tree"), dict):
        raise InstallationContractError(f"runtime asset sample artifacts drift: {sample_relative}")
    output_tree = artifacts["output_tree"]
    expected_artifact_path = artifact_path.relative_to(BENCHMARK_RESULT.parent).as_posix()
    if (
        output_tree.get("path") != expected_artifact_path
        or output_tree.get("bytes") != artifact_path.stat().st_size
        or str(output_tree.get("sha256", "")).removeprefix("sha256:") != sha256_file(artifact_path)
    ):
        raise InstallationContractError(f"runtime asset sample binding drift: {sample_relative}")
    return sample_relative, sha256_file(ROOT / sample_relative)


def runtime_assets() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    assets = [
        {"id": identifier, "name": name, "kind": kind, "bytes": size, "sha256": digest}
        for identifier, name, kind, size, digest in EXPECTED_ASSETS
    ]
    expected_by_name = {asset["name"]: asset for asset in assets}
    observations = []
    asset_set = canonical_json(assets).encode("ascii")
    for relative in ASSET_SAMPLE_PATHS:
        artifact_path = ROOT / relative
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
        observed = observed_runtime_assets(document, relative, expected_by_name)
        sample_path, sample_sha256 = validate_sample_metadata(relative, artifact_path)
        observations.append({
            "id": f"installation.asset-observation.{Path(relative).parent.name}",
            "artifact_path": relative,
            "artifact_sha256": sha256_file(artifact_path),
            "sample_metadata_path": sample_path,
            "sample_metadata_sha256": sample_sha256,
            "asset_set_sha256": sha256_bytes(asset_set),
            "asset_count": len(observed),
        })
    return assets, observations


def validate_oracle_manifest(tree: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(ORACLE_MANIFEST)
    if manifest.get("status") != "observed" or manifest.get("manifest_id") != "oracle-lcov-v2.5-image-smoke":
        raise InstallationContractError("installation Oracle manifest identity drift")
    if manifest.get("evidence", {}).get("scope") != "environment_smoke":
        raise InstallationContractError("installation Oracle manifest scope drift")
    if manifest.get("evidence", {}).get("inventory_entries") != []:
        raise InstallationContractError("installation Oracle manifest claims inventory evidence")
    installed = manifest.get("installed_tree", {})
    if installed.get("entries") != tree["entry_count"] or installed.get("manifest_sha256") != f"sha256:{tree['manifest_sha256']}":
        raise InstallationContractError("installation Oracle manifest tree binding drift")
    return {
        "manifest_id": manifest["manifest_id"],
        "status": manifest["status"],
        "evidence_scope": manifest["evidence"]["scope"],
        "product_compatibility_evidence": False,
    }


def validate_benchmark_result() -> dict[str, Any]:
    result = load_json(BENCHMARK_RESULT)
    if result.get("result_id") != "m0-oracle-baseline-oracle" or result.get("status") != "baseline_only":
        raise InstallationContractError("installation asset benchmark identity drift")
    correctness = result.get("correctness_gate", {})
    performance = result.get("performance_gate", {})
    if correctness.get("status") != "not_evaluated" or correctness.get("reason") != "candidate_not_available":
        raise InstallationContractError("installation asset correctness gate drift")
    if performance.get("status") != "not_evaluated" or performance.get("reason") != "candidate_not_available":
        raise InstallationContractError("installation asset performance gate drift")
    manifest = result.get("execution_manifest", {})
    if manifest.get("path") != "compat/manifests/oracle-lcov-v2.5-smoke.json":
        raise InstallationContractError("installation asset execution-manifest binding drift")
    if str(manifest.get("sha256", "")).removeprefix("sha256:") != sha256_file(ORACLE_MANIFEST):
        raise InstallationContractError("installation asset execution-manifest hash drift")
    return {
        "result_id": result["result_id"],
        "status": result["status"],
        "correctness_gate_status": correctness["status"],
        "performance_gate_status": performance["status"],
        "product_compatibility_evidence": False,
    }




def source_binding(upstream_root: Path, path: str, start: int, end: int) -> dict[str, Any]:
    try:
        lines = (upstream_root / path).read_text(encoding="utf-8").splitlines()
        selected = lines[start - 1:end]
    except (OSError, IndexError) as error:
        raise InstallationContractError(f"cannot read source binding {path}:{start}-{end}") from error
    if len(selected) != end - start + 1:
        raise InstallationContractError(f"short source binding {path}:{start}-{end}")
    content = ("\n".join(selected) + "\n").encode("utf-8")
    digest = sha256_bytes(content)
    return {
        "path": path,
        "line_start": start,
        "line_end": end,
        "line_count": len(selected),
        "sha256": digest,
        "text_sha256": digest,
    }


def tree_entries() -> list[dict[str, str]]:
    return parse_tree()


def group_entries(entries: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {
        "bin": [],
        "config": [],
        "lib": [],
        "man": [],
        "support_scripts": [],
        "html": [],
        "example": [],
        "tests": [],
        "legacy_man_symlink": [],
    }
    for entry in entries:
        name, _prefix = group_for_path(entry["path"])
        grouped[name].append(entry)
    return grouped


def expected_report_observation_facts() -> list[dict[str, Any]]:
    expected_names = {name for _, name, _, _, _ in EXPECTED_ASSETS}
    observations: list[dict[str, Any]] = []
    for relative in ASSET_SAMPLE_PATHS:
        artifact_path = ROOT / relative
        sample_relative = str(Path(relative).with_name("sample.json"))
        sample = load_json(ROOT / sample_relative)
        tree_document = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(tree_document, list):
            raise InstallationContractError(f"asset sample is not a tree list: {relative}")
        assets: dict[str, dict[str, object]] = {}
        for entry in tree_document:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if not isinstance(path, str) or not path.startswith("html/"):
                continue
            name = path.removeprefix("html/")
            if name not in expected_names:
                continue
            assets[name] = {
                "bytes": entry.get("bytes"),
                "sha256": str(entry.get("sha256", "")).removeprefix("sha256:"),
                "status": entry.get("status"),
            }
        if set(assets) != expected_names:
            raise InstallationContractError(f"report observation asset set drift: {relative}")
        for _, name, _, size, digest in EXPECTED_ASSETS:
            asset = assets[name]
            if asset.get("bytes") != size or asset.get("sha256") != digest or asset.get("status") != "created":
                raise InstallationContractError(f"report observation asset identity drift: {relative}:{name}")
        sample_id = Path(relative).parent.name
        expected_phase = "warmup" if "-warmup-" in sample_id else "measured"
        if (
            sample.get("case_id") != "report-genhtml-default"
            or sample.get("sample_id") != sample_id
            or sample.get("phase") != expected_phase
        ):
            raise InstallationContractError(f"report observation sample identity drift: {sample_relative}")
        observations.append({
            "id": f"installation.asset-observation.{sample_id}",
            "artifact_path": relative,
            "artifact_sha256": sha256_file(artifact_path),
            "sample_metadata_path": sample_relative,
            "sample_metadata_sha256": sha256_file(ROOT / sample_relative),
            "sample_case_id": sample["case_id"],
            "sample_id": sample_id,
            "phase": expected_phase,
            "assets": assets,
            "asset_count": len(assets),
        })
    return observations




def wave2_capture_document() -> dict[str, Any]:
    if not WAVE2_CAPTURE_PATH.is_file():
        raise InstallationContractError("installation wave2 capture document is missing")
    actual = sha256_file(WAVE2_CAPTURE_PATH)
    if actual != EXPECTED_WAVE2_CAPTURE_SHA256:
        raise InstallationContractError(
            f"installation wave2 capture drift: expected={EXPECTED_WAVE2_CAPTURE_SHA256} actual={actual}"
        )
    document = load_json(WAVE2_CAPTURE_PATH)
    if document.get("product_compatibility_evidence") is not False:
        raise InstallationContractError("installation wave2 capture claims product compatibility")
    if document.get("evidence_status") != "oracle_reference" or document.get("execution_status") != "planned":
        raise InstallationContractError("installation wave2 capture evidence status drift")
    if document.get("case_count") != 13 or len(document.get("cases", [])) != 13:
        raise InstallationContractError("installation wave2 capture must cover 13 cases")
    if document.get("capture_format") != "replayable_case_records_v1":
        raise InstallationContractError("installation wave2 capture format drift")
    if document.get("oracle_image_id") != EXPECTED_WAVE2_ORACLE_IMAGE_ID:
        raise InstallationContractError("installation wave2 capture image id drift")
    if document.get("upstream_commit") != EXPECTED_WAVE2_UPSTREAM_COMMIT:
        raise InstallationContractError("installation wave2 capture upstream commit drift")
    return document


def wave2_expected_table() -> dict[str, Any]:
    if not WAVE2_EXPECTED_TABLE_PATH.is_file():
        raise InstallationContractError("installation wave2 expected case table is missing")
    actual = sha256_file(WAVE2_EXPECTED_TABLE_PATH)
    if actual != EXPECTED_WAVE2_EXPECTED_TABLE_SHA256:
        raise InstallationContractError(
            "installation wave2 expected table drift: "
            f"expected={EXPECTED_WAVE2_EXPECTED_TABLE_SHA256} actual={actual}"
        )
    table = load_json(WAVE2_EXPECTED_TABLE_PATH)
    if table.get("product_compatibility_evidence") is not False:
        raise InstallationContractError("wave2 expected table claims product compatibility")
    if table.get("evidence_status") != "oracle_reference" or table.get("execution_status") != "planned":
        raise InstallationContractError("wave2 expected table status drift")
    if table.get("oracle_image_id") != EXPECTED_WAVE2_ORACLE_IMAGE_ID:
        raise InstallationContractError("wave2 expected table image id drift")
    if table.get("upstream_commit") != EXPECTED_WAVE2_UPSTREAM_COMMIT:
        raise InstallationContractError("wave2 expected table upstream commit drift")
    cases = table.get("cases")
    if not isinstance(cases, list) or len(cases) != 13:
        raise InstallationContractError("wave2 expected table must contain 13 cases")
    ids = [case.get("id") for case in cases]
    if ids != list(PLANNED_CASE_IDS):
        raise InstallationContractError("wave2 expected table case order drift")
    return table


def wave2_case_capture_schema() -> dict[str, Any]:
    if not WAVE2_CASE_CAPTURE_SCHEMA_PATH.is_file():
        raise InstallationContractError("wave2 case capture schema missing")
    return load_json(WAVE2_CASE_CAPTURE_SCHEMA_PATH)


def observation_material(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifacts": record["artifacts"],
        "case_id": record["case_id"],
        "environment": record["environment"],
        "file_tree_effects": record["file_tree_effects"],
        "identity": record["identity"],
        "invocation": record["invocation"],
        "process": record["process"],
    }


def recompute_observation_sha256(record: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(observation_material(record)).encode("ascii"))


def _bind_capture_artifact_file(art: dict[str, Any], *, label: str) -> None:
    rel = art.get("path")
    if not isinstance(rel, str) or not rel.startswith("compat/installation/wave2/cases/"):
        raise InstallationContractError(f"wave2 artifact path prefix invalid ({label}): {rel}")
    if ".." in PurePosixPath(rel).parts:
        raise InstallationContractError(f"wave2 artifact path traversal ({label}): {rel}")
    art_path = ROOT / rel
    if not art_path.is_file():
        raise InstallationContractError(f"wave2 artifact missing ({label}): {rel}")
    actual = sha256_file(art_path)
    if actual != art.get("sha256"):
        raise InstallationContractError(
            f"wave2 artifact drift ({label}): {rel} expected={art.get('sha256')} actual={actual}"
        )
    if art_path.stat().st_size != art.get("bytes"):
        raise InstallationContractError(f"wave2 artifact size drift ({label}): {rel}")


def load_case_capture_record(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    if not path.is_file():
        raise InstallationContractError(f"wave2 case capture missing: {relative_path}")
    record = load_json(path)
    validate_against_schema(record, wave2_case_capture_schema(), label="wave2 case capture")
    if record.get("product_compatibility_evidence") is not False:
        raise InstallationContractError(f"wave2 case capture product claim: {relative_path}")
    if record.get("evidence_status") != "oracle_reference" or record.get("execution_status") != "planned":
        raise InstallationContractError(f"wave2 case capture status drift: {relative_path}")
    recomputed = recompute_observation_sha256(record)
    if recomputed != record.get("observation_sha256"):
        raise InstallationContractError(f"wave2 observation hash drift: {relative_path}")
    # Bind raw stdout/stderr bytes and every extra artifact reference.
    for key in ("stdout_bin", "stderr_bin"):
        _bind_capture_artifact_file(record["artifacts"][key], label=f"{relative_path}:{key}")
    for extra in record["artifacts"].get("extra") or []:
        _bind_capture_artifact_file(extra, label=f"{relative_path}:extra:{extra.get('name')}")
    # Artifact paths must stay under the case tree rooted at the capture directory
    # (or a direct child for dual-part parents such as INST-PATH-001).
    capture_dir = PurePosixPath(relative_path).parent.as_posix()
    case_root = capture_dir
    for art in [record["artifacts"]["stdout_bin"], record["artifacts"]["stderr_bin"], *(record["artifacts"].get("extra") or [])]:
        art_path = PurePosixPath(art["path"]).as_posix()
        if not (art_path.startswith(case_root + "/") or PurePosixPath(art_path).parent.as_posix() == case_root):
            raise InstallationContractError(
                f"wave2 capture artifact outside case tree: capture={relative_path} artifact={art_path}"
            )
    return record


def validate_against_schema(document: dict[str, Any], schema: dict[str, Any], *, label: str) -> None:
    try:
        Draft202012Validator(schema).validate(document)
    except Exception as exc:  # noqa: BLE001 - surface validator detail
        raise InstallationContractError(f"{label} schema failure: {exc}") from exc


def wave2_directory_companion() -> dict[str, Any]:
    if not WAVE2_DIRECTORY_LOCK.is_file():
        raise InstallationContractError("installation wave2 directory lock is missing")
    actual = sha256_file(WAVE2_DIRECTORY_LOCK)
    if actual != EXPECTED_WAVE2_DIRECTORY_LOCK_SHA256:
        raise InstallationContractError(
            "installation wave2 directory lock drift: "
            f"expected={EXPECTED_WAVE2_DIRECTORY_LOCK_SHA256} actual={actual}"
        )
    rows = []
    for raw in WAVE2_DIRECTORY_LOCK.read_text(encoding="ascii").splitlines():
        fields = raw.split("	")
        if len(fields) != 4:
            raise InstallationContractError("wave2 directory lock has a malformed row")
        kind, mode, identity, path = fields
        if kind != "directory" or mode != EXPECTED_WAVE2_DIRECTORY_MODE or identity != ".":
            raise InstallationContractError(f"wave2 directory lock invalid row: {raw}")
        parsed_path = PurePosixPath(path)
        if (
            not parsed_path.is_absolute()
            or parsed_path.parts[:3] != ("/", "usr", "local")
            or ".." in parsed_path.parts
            or parsed_path.as_posix() != path
        ):
            raise InstallationContractError(f"wave2 directory path invalid: {path}")
        rows.append({"kind": kind, "mode": mode, "identity": identity, "path": path})
    if len(rows) != EXPECTED_WAVE2_DIRECTORY_COUNT:
        raise InstallationContractError(
            f"wave2 directory lock must contain {EXPECTED_WAVE2_DIRECTORY_COUNT} entries"
        )
    paths = [row["path"] for row in rows]
    if paths != sorted(paths):
        raise InstallationContractError("wave2 directory paths are not lexicographic")
    if len(set(paths)) != len(paths):
        raise InstallationContractError("wave2 directory lock has duplicate paths")
    return {
        "path": "compat/installation/wave2/installed-directories.lock",
        "sha256": actual,
        "entry_count": len(rows),
        "mode": EXPECTED_WAVE2_DIRECTORY_MODE,
        "paths": paths,
    }


def wave2_artifact_bindings() -> list[dict[str, str]]:
    result = []
    for relative, expected in EXPECTED_WAVE2_ARTIFACT_HASHES.items():
        path = ROOT / relative
        actual = sha256_file(path)
        if actual != expected:
            raise InstallationContractError(
                f"wave2 artifact drift: {relative} expected={expected} actual={actual}"
            )
        result.append({"path": relative, "sha256": actual})
    return result


def expected_row_for_case(case_id: str) -> dict[str, Any]:
    for case in wave2_expected_table()["cases"]:
        if case["id"] == case_id:
            return case
    raise InstallationContractError(f"wave2 expected table missing case: {case_id}")



def capture_binding_for_case(case_id: str) -> dict[str, Any]:
    """Independent expected-table binding; does not trust capture JSON alone.

    Compares observed capture fields against the independently authored expected
    table for exit, argv, cwd, timeout, cleanup, environment mode, executable
    identity, signal, timed_out, child shape, full tree paths_sha256/counts, and
    stream hashes. Capture observation hashes must match the table only when the
    table pins them; co-mutating capture + observation without table update fails.
    """
    row = expected_row_for_case(case_id)
    if row.get("oracle_image_id") != EXPECTED_WAVE2_ORACLE_IMAGE_ID:
        raise InstallationContractError(f"wave2 expected image drift: {case_id}")
    if row.get("upstream_commit") != EXPECTED_WAVE2_UPSTREAM_COMMIT:
        raise InstallationContractError(f"wave2 expected upstream drift: {case_id}")

    def check_common(record: dict[str, Any], expect: dict[str, Any], label: str) -> None:
        if record.get("oracle_execution_status") != expect.get(
            "oracle_execution_status", row.get("oracle_execution_status")
        ):
            # parent row status for parts uses captured
            if expect.get("oracle_execution_status") is not None:
                raise InstallationContractError(f"wave2 status drift: {label}")
        if expect.get("expected_exit_status") is not None:
            if record["process"]["exit_status"] != expect["expected_exit_status"]:
                raise InstallationContractError(f"wave2 exit status drift: {label}")
        if "argv" in expect and record["invocation"]["argv"] != expect["argv"]:
            raise InstallationContractError(f"wave2 argv drift: {label}")
        if "working_directory" in expect:
            if record["invocation"]["working_directory"] != expect["working_directory"]:
                raise InstallationContractError(f"wave2 cwd drift: {label}")
        if "timeout_seconds" in expect:
            if record["invocation"]["timeout_seconds"] != expect["timeout_seconds"]:
                raise InstallationContractError(f"wave2 timeout drift: {label}")
        if "environment_mode" in expect:
            if record["environment"]["mode"] != expect["environment_mode"]:
                raise InstallationContractError(f"wave2 env mode drift: {label}")
        if "executable_path" in expect:
            if record["identity"]["executable_path"] != expect["executable_path"]:
                raise InstallationContractError(f"wave2 exe path drift: {label}")
        if expect.get("executable_sha256"):
            if record["identity"]["executable_sha256"] != expect["executable_sha256"]:
                raise InstallationContractError(f"wave2 exe hash drift: {label}")
        if "signal" in expect and record["process"]["signal"] != expect["signal"]:
            raise InstallationContractError(f"wave2 signal drift: {label}")
        if "timed_out" in expect and record["process"]["timed_out"] != expect["timed_out"]:
            raise InstallationContractError(f"wave2 timed_out drift: {label}")
        if "cleanup" in expect:
            if record["invocation"]["cleanup"] != expect["cleanup"]:
                raise InstallationContractError(f"wave2 cleanup drift: {label}")
        if expect.get("paths_sha256"):
            if record["file_tree_effects"]["paths_sha256"] != expect["paths_sha256"]:
                raise InstallationContractError(f"wave2 tree paths_sha256 drift: {label}")
        if "file_count" in expect:
            if record["file_tree_effects"]["file_count"] != expect["file_count"]:
                raise InstallationContractError(f"wave2 tree file_count drift: {label}")
        if "directory_count" in expect:
            if record["file_tree_effects"]["directory_count"] != expect["directory_count"]:
                raise InstallationContractError(f"wave2 tree directory_count drift: {label}")
        if "symlink_count" in expect:
            if record["file_tree_effects"]["symlink_count"] != expect["symlink_count"]:
                raise InstallationContractError(f"wave2 tree symlink_count drift: {label}")
        if "rows" not in record["file_tree_effects"]:
            raise InstallationContractError(f"wave2 tree rows missing: {label}")
        rows = record["file_tree_effects"]["rows"]
        if not isinstance(rows, list):
            raise InstallationContractError(f"wave2 tree rows type drift: {label}")
        # Full rows retained: count must match directory+file+symlink totals
        expected_row_count = (
            record["file_tree_effects"]["file_count"]
            + record["file_tree_effects"]["directory_count"]
            + record["file_tree_effects"]["symlink_count"]
        )
        if len(rows) != expected_row_count:
            raise InstallationContractError(f"wave2 tree rows incomplete: {label}")
        if "child_count" in expect:
            if len(record["process"]["child_processes_observed"]) != expect["child_count"]:
                raise InstallationContractError(f"wave2 child count drift: {label}")
        for child in record["process"]["child_processes_observed"]:
            if not isinstance(child.get("argv"), list) or not child.get("command"):
                raise InstallationContractError(f"wave2 child shape drift: {label}")
            if "exit_status" not in child or "signal" not in child or "timed_out" not in child:
                raise InstallationContractError(f"wave2 child fields drift: {label}")
        if "observed_env_keys" in expect:
            keys = sorted(record["environment"]["observed_variables"].keys())
            if keys != expect["observed_env_keys"]:
                raise InstallationContractError(f"wave2 observed env keys drift: {label}")
        # Fail closed: captured requires integer exit XOR signal/timeout
        if record.get("oracle_execution_status") == "captured":
            proc = record["process"]
            if proc["timed_out"]:
                if proc["exit_status"] is not None or proc["signal"] is None:
                    raise InstallationContractError(f"wave2 timeout shape invalid: {label}")
            elif proc["signal"] is not None:
                if proc["exit_status"] is not None:
                    raise InstallationContractError(f"wave2 signal shape invalid: {label}")
            elif not isinstance(proc["exit_status"], int):
                raise InstallationContractError(f"wave2 exit missing for captured: {label}")
            if not record["identity"]["executable_path"].startswith("/"):
                raise InstallationContractError(f"wave2 relative executable: {label}")
            if record["identity"]["executable_sha256"] == "0" * 64:
                raise InstallationContractError(f"wave2 zero executable hash: {label}")
            if not record["invocation"]["working_directory"].startswith("/"):
                raise InstallationContractError(f"wave2 relative cwd: {label}")
            if not record["invocation"]["fixture_setup"]:
                raise InstallationContractError(f"wave2 empty fixture_setup: {label}")
            if not record["invocation"]["cleanup"]:
                raise InstallationContractError(f"wave2 empty cleanup: {label}")
            if not record["environment"].get("observed_variables"):
                raise InstallationContractError(f"wave2 missing observed env: {label}")
        if expect.get("observation_sha256"):
            if record.get("observation_sha256") != expect["observation_sha256"]:
                raise InstallationContractError(f"wave2 observation table drift: {label}")
        if expect.get("stdout_sha256"):
            if record["artifacts"]["stdout_bin"]["sha256"] != expect["stdout_sha256"]:
                raise InstallationContractError(f"wave2 stdout table drift: {label}")
        if expect.get("stderr_sha256"):
            if record["artifacts"]["stderr_bin"]["sha256"] != expect["stderr_sha256"]:
                raise InstallationContractError(f"wave2 stderr table drift: {label}")
        if record["identity"]["oracle_image_id"] != EXPECTED_WAVE2_ORACLE_IMAGE_ID:
            raise InstallationContractError(f"wave2 record image drift: {label}")
        if record["identity"]["upstream_commit"] != EXPECTED_WAVE2_UPSTREAM_COMMIT:
            raise InstallationContractError(f"wave2 record upstream drift: {label}")

    if case_id == "INST-PATH-001":
        rel = load_case_capture_record(
            "compat/installation/wave2/cases/INST-PATH-001/relative/capture.json"
        )
        space = load_case_capture_record(
            "compat/installation/wave2/cases/INST-PATH-001/space/capture.json"
        )
        parent = load_case_capture_record(row["capture_path"])
        parts = row.get("parts") or {}
        rel_expect = {**row, **(parts.get("relative") or {})}
        space_expect = {**row, **(parts.get("space") or {})}
        # parts override parent argv etc.
        for key in (
            "argv",
            "working_directory",
            "timeout_seconds",
            "expected_exit_status",
            "signal",
            "timed_out",
            "environment_mode",
            "executable_path",
            "executable_sha256",
            "cleanup",
            "paths_sha256",
            "file_count",
            "directory_count",
            "symlink_count",
            "child_count",
            "observed_env_keys",
            "observation_sha256",
            "stdout_sha256",
            "stderr_sha256",
        ):
            if key in (parts.get("relative") or {}):
                rel_expect[key] = parts["relative"][key]
            if key in (parts.get("space") or {}):
                space_expect[key] = parts["space"][key]
        check_common(rel, rel_expect, f"{case_id}:relative")
        check_common(space, space_expect, f"{case_id}:space")
        if parent.get("oracle_execution_status") != row["oracle_execution_status"]:
            raise InstallationContractError(f"wave2 path parent status drift: {case_id}")
        if row.get("observation_sha256") and parent.get("observation_sha256") != row["observation_sha256"]:
            raise InstallationContractError(f"wave2 path parent observation drift: {case_id}")
        if rel["artifacts"]["stdout_bin"]["sha256"] != row.get("stdout_sha256", rel["artifacts"]["stdout_bin"]["sha256"]):
            if row.get("stdout_sha256"):
                raise InstallationContractError("wave2 path relative stdout drift")
        if space["artifacts"]["stdout_bin"]["sha256"] != row.get(
            "space_stdout_sha256", space["artifacts"]["stdout_bin"]["sha256"]
        ):
            if row.get("space_stdout_sha256"):
                raise InstallationContractError("wave2 path space stdout drift")
        if row.get("space_stderr_sha256"):
            if space["artifacts"]["stderr_bin"]["sha256"] != row["space_stderr_sha256"]:
                raise InstallationContractError("wave2 path space stderr drift")
        # parent child processes must reference both parts
        if len(parent["process"]["child_processes_observed"]) != 2:
            raise InstallationContractError("wave2 path parent child count drift")
        return {
            "relative": {
                "path": "compat/installation/wave2/cases/INST-PATH-001/relative/capture.json",
                "sha256": sha256_file(
                    ROOT / "compat/installation/wave2/cases/INST-PATH-001/relative/capture.json"
                ),
                "observation_sha256": rel["observation_sha256"],
                "stdout_sha256": rel["artifacts"]["stdout_bin"]["sha256"],
                "stderr_sha256": rel["artifacts"]["stderr_bin"]["sha256"],
            },
            "space": {
                "path": "compat/installation/wave2/cases/INST-PATH-001/space/capture.json",
                "sha256": sha256_file(
                    ROOT / "compat/installation/wave2/cases/INST-PATH-001/space/capture.json"
                ),
                "observation_sha256": space["observation_sha256"],
                "stdout_sha256": space["artifacts"]["stdout_bin"]["sha256"],
                "stderr_sha256": space["artifacts"]["stderr_bin"]["sha256"],
            },
        }

    record = load_case_capture_record(row["capture_path"])
    check_common(record, row, case_id)
    return {
        "path": row["capture_path"],
        "sha256": sha256_file(ROOT / row["capture_path"]),
        "observation_sha256": row.get("observation_sha256") or record["observation_sha256"],
        "stdout_sha256": row.get("stdout_sha256") or record["artifacts"]["stdout_bin"]["sha256"],
        "stderr_sha256": row.get("stderr_sha256") or record["artifacts"]["stderr_bin"]["sha256"],
    }



def capture_artifact_for_case(case_id: str, capture_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    del capture_doc  # independent expected table is authoritative
    binding = capture_binding_for_case(case_id)
    if case_id == "INST-PATH-001":
        # Parent-facing single artifact remains the dual relative envelope for compatibility
        # with non-path call sites; path facts use capture_artifacts instead.
        return binding["relative"]
    return binding


def validate_wave2_runner_qualification(index: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Production-load and recompute both runner qualification captures."""
    document = index if index is not None else wave2_capture_document()
    rows = document.get("runner_qualification")
    if not isinstance(rows, list) or len(rows) != 2:
        raise InstallationContractError("wave2 runner_qualification must contain exactly 2 rows")
    expected_ids = ["INST-RUNNER-SIGNAL-001", "INST-RUNNER-TIMEOUT-001"]
    by_id = {row.get("id"): row for row in rows}
    if list(by_id) != expected_ids and set(by_id) != set(expected_ids):
        # order flexible but membership exact
        if set(by_id) != set(expected_ids):
            raise InstallationContractError(f"wave2 runner ids drift: {sorted(by_id)}")
    bindings: list[dict[str, Any]] = []
    for case_id in expected_ids:
        row = by_id[case_id]
        expected_path = f"compat/installation/wave2/cases/_runner/{case_id}/capture.json"
        if row.get("capture_path") != expected_path:
            raise InstallationContractError(
                f"wave2 runner capture_path drift: {case_id} expected={expected_path} actual={row.get('capture_path')}"
            )
        record = load_case_capture_record(expected_path)
        if record.get("oracle_execution_status") != "captured":
            raise InstallationContractError(f"wave2 runner not captured: {case_id}")
        if record.get("case_id") != case_id:
            raise InstallationContractError(f"wave2 runner case_id drift: {case_id}")
        # Lifecycle semantics
        if case_id == "INST-RUNNER-SIGNAL-001":
            if record["process"]["signal"] is None or record["process"]["timed_out"]:
                raise InstallationContractError(f"wave2 runner signal semantics drift: {case_id}")
            if record["process"]["exit_status"] is not None:
                raise InstallationContractError(f"wave2 runner signal exit must be null: {case_id}")
            if int(record["invocation"]["timeout_seconds"]) != 30:
                raise InstallationContractError(f"wave2 runner signal timeout_seconds drift: {case_id}")
        if case_id == "INST-RUNNER-TIMEOUT-001":
            if not record["process"]["timed_out"] or record["process"]["signal"] is None:
                raise InstallationContractError(f"wave2 runner timeout semantics drift: {case_id}")
            if record["process"]["exit_status"] is not None:
                raise InstallationContractError(f"wave2 runner timeout exit must be null: {case_id}")
            if int(record["invocation"]["timeout_seconds"]) != 1:
                raise InstallationContractError(
                    f"wave2 runner timeout_seconds must match 1s deadline: got {record['invocation']['timeout_seconds']}"
                )
        if row.get("observation_sha256") != record["observation_sha256"]:
            raise InstallationContractError(f"wave2 runner index observation drift: {case_id}")
        if row.get("signal") != record["process"]["signal"]:
            raise InstallationContractError(f"wave2 runner index signal drift: {case_id}")
        if bool(row.get("timed_out")) != bool(record["process"]["timed_out"]):
            raise InstallationContractError(f"wave2 runner index timed_out drift: {case_id}")
        if row.get("host_observer_code") != record["process"]["host_observer_code"]:
            raise InstallationContractError(f"wave2 runner index host_observer_code drift: {case_id}")
        # Recompute observation already done inside load; also require non-sentinel exe hash
        exe = record["identity"]["executable_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", exe or "") or exe in {"0" * 64, "f" * 64}:
            raise InstallationContractError(f"wave2 runner executable hash invalid: {case_id}")
        bindings.append(
            {
                "id": case_id,
                "path": expected_path,
                "sha256": sha256_file(ROOT / expected_path),
                "observation_sha256": record["observation_sha256"],
                "stdout_sha256": record["artifacts"]["stdout_bin"]["sha256"],
                "stderr_sha256": record["artifacts"]["stderr_bin"]["sha256"],
                "timeout_seconds": record["invocation"]["timeout_seconds"],
                "signal": record["process"]["signal"],
                "timed_out": record["process"]["timed_out"],
                "executable_sha256": exe,
            }
        )
    return bindings


def validate_wave2_captures_against_expected() -> None:
    index = wave2_capture_document()
    table = wave2_expected_table()
    index_by_id = {case["id"]: case for case in index["cases"]}
    for row in table["cases"]:
        case_id = row["id"]
        if case_id not in index_by_id:
            raise InstallationContractError(f"wave2 index missing case: {case_id}")
        indexed = index_by_id[case_id]
        if indexed.get("oracle_execution_status") != row["oracle_execution_status"]:
            raise InstallationContractError(f"wave2 index status drift: {case_id}")
        if indexed.get("observation_sha256") != row["observation_sha256"]:
            raise InstallationContractError(f"wave2 index observation drift: {case_id}")
        if indexed.get("capture_path") != row["capture_path"]:
            raise InstallationContractError(f"wave2 index path drift: {case_id}")
        capture_binding_for_case(case_id)
    # Runner qualification is outside the 13-case table but must still production-load.
    validate_wave2_runner_qualification(index)


def expected_case_independent_facts(
    case_id: str,
    upstream_root: Path,
    tree: dict[str, Any],
    assets: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    entries = tree_entries()
    grouped = group_entries(entries)
    bin_names = sorted(Path(entry["path"]).name for entry in grouped["bin"])
    support_script_names = sorted(Path(entry["path"]).name for entry in grouped["support_scripts"])
    man_page_names = sorted(Path(entry["path"]).name for entry in grouped["man"])
    mk_vars = source_binding(upstream_root, "Makefile", 38, 84)
    install_payload = source_binding(upstream_root, "Makefile", 134, 190)
    install_doc = source_binding(upstream_root, "Makefile", 125, 190)
    fixup = source_binding(upstream_root, "bin/fix.pl", 89, 139)
    config_discovery = source_binding(upstream_root, "lib/lcovutil.pm", 1448, 1460)
    uninstall = source_binding(upstream_root, "Makefile", 194, 223)
    man_install = source_binding(upstream_root, "Makefile", 163, 174)
    docs_build = source_binding(upstream_root, "docs/Makefile", 4, 22)
    docs_config = source_binding(upstream_root, "docs/conf.py", 34, 63)
    test_runtime = source_binding(upstream_root, "tests/common.mak", 2, 18)
    test_paths = source_binding(upstream_root, "tests/common.mak", 76, 83)
    test_readme = source_binding(upstream_root, "tests/README.md", 13, 18)
    readme_paths = source_binding(upstream_root, "README.rst", 125, 139)
    asset_names = source_binding(upstream_root, "bin/genhtml", 7128, 7128)
    asset_generation = source_binding(upstream_root, "bin/genhtml", 7952, 7952)
    asset_writers = source_binding(upstream_root, "bin/genhtml", 8822, 9046)
    dist_manifest = source_binding(upstream_root, "Makefile", 71, 72)
    report_observation_facts = expected_report_observation_facts()

    if case_id == "INST-LAYOUT-001":
        directory = wave2_directory_companion()
        return {
            "bin_names": bin_names,
            "directory_companion_entry_count": directory["entry_count"],
            "directory_companion_mode": directory["mode"],
            "directory_companion_path": directory["path"],
            "directory_companion_retained": True,
            "capture_artifact": capture_binding_for_case(case_id),
            "directory_companion_sha256": directory["sha256"],
            "directory_entries_retained": False,
            "oracle_execution_status": "captured",
            "file_count": tree["file_count"],
            "group_counts": {name: len(values) for name, values in grouped.items()},
            "legacy_symlink": {
                "mode": "777",
                "path": "/usr/local/man",
                "target": "share/man",
            },
            "man_page_names": man_page_names,
            "manifest_sha256": tree["manifest_sha256"],
            "mode_counts": {
                "644": tree["mode_counts"]["644"],
                "755": tree["mode_counts"]["755"],
                "777": tree["mode_counts"]["777"],
            },
            "path_order": "lexicographic",
            "path_root": "/usr/local",
            "support_script_count": 23,
            "support_script_names": support_script_names,
            "symlink_count": tree["symlink_count"],
            "tree_entry_count": tree["entry_count"],
        }
    if case_id == "INST-STAGE-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "compiled_paths_retain_prefix_without_destdir": True,
            "oracle_execution_status": "captured",
            "payload_under_destdir": True,
            "requires_absolute_destdir_prefix": True,
            "source_bindings": [mk_vars, install_payload],
        }
    if case_id == "INST-INTERP-001":
        capture_doc = wave2_capture_document()
        return {
            "advertised_override_effective": False,
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "env_shebang_excluded_from_rewrite": True,
            "install_passes_fixinterp": False,
            "oracle_execution_status": "captured",
            "source_bindings": [fixup, install_payload],
        }
    if case_id == "INST-CONFIG-DISCOVERY-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "compiled_prefix_alone_selects_system_file": False,
            "oracle_execution_status": "captured",
            "search_order": ["$HOME/.lcovrc", "$LCOV_HOME/etc/lcovrc"],
            "source_bindings": [config_discovery],
            "stops_after_first_readable": True,
        }
    if case_id == "INST-UNINSTALL-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "foreign_sentinels_removed": True,
            "isolated_root_required": True,
            "man_uninstall_enumerates_source_glob": True,
            "oracle_execution_status": "captured",
            "recursive_removal_targets": ["lib/lcov", "share/lcov"],
            "source_bindings": [man_install, uninstall],
        }
    if case_id == "INST-PARTIAL-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "oracle_execution_status": "captured",
            "partial_payload_possible": True,
            "rollback": False,
            "source_bindings": [install_payload],
            "transactional": False,
        }
    if case_id == "INST-DOC-FAIL-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "doc_finished_is_hard_prerequisite": True,
            "install_cleans_source_example_and_tests": True,
            "missing_sphinx_or_theme_fails_before_payload": True,
            "oracle_execution_status": "captured",
            "source_bindings": [install_doc, docs_build, docs_config],
        }
    if case_id == "INST-PATH-001":
        return {
            "capture_artifacts": capture_binding_for_case(case_id),
            "oracle_execution_status": "captured",
            "relative_roots_rejected": True,
            "requires_absolute_destdir_prefix": True,
            "source_bindings": [mk_vars, install_payload],
            "space_containing_paths_platform_sensitive": True,
        }
    if case_id == "INST-DIRTY-ASSET-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "examples_and_tests_from_working_tree": True,
            "oracle_execution_status": "captured",
            "retained_support_script_count": 23,
            "retained_support_script_names": support_script_names,
            "scripts_from_dynamic_ls": True,
            "source_bindings": [mk_vars, install_payload],
            "untracked_ordinary_files_can_enter_install": True,
        }
    if case_id == "INST-TEST-RUN-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "explicit_lcov_home_required_for_installed_tests": True,
            "oracle_execution_status": "captured",
            "retained_test_entry_count": 205,
            "source_bindings": [test_runtime, test_paths, test_readme],
            "unset_lcov_home_can_resolve_nonexistent_share_lcov_bin": True,
        }
    if case_id == "INST-DOC-PATH-001":
        capture_doc = wave2_capture_document()
        return {
            "actual_retained_roots": {
                "bin": "/usr/local/bin",
                "config": "/usr/local/etc/lcovrc",
                "html": "/usr/local/share/lcov/html",
                "lib": "/usr/local/lib/lcov",
                "man": "/usr/local/share/man",
                "scripts": "/usr/local/share/lcov/support-scripts",
                "tests": "/usr/local/share/lcov/tests",
            },
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "documentation_mismatch_must_be_recorded": True,
            "oracle_execution_status": "captured",
            "source_bindings": [readme_paths, mk_vars],
            "truth_source": "installed_tree_filesystem_evidence",
        }
    if case_id == "INST-REPORT-ASSET-001":
        expected_observation_ids = [item["id"] for item in report_observation_facts]
        retained_observation_ids = [item["id"] for item in observations]
        if expected_observation_ids != retained_observation_ids:
            raise InstallationContractError("report observation id order drift")
        for expected_obs, retained_obs in zip(report_observation_facts, observations):
            if expected_obs["artifact_path"] != retained_obs["artifact_path"]:
                raise InstallationContractError("report observation artifact_path drift")
            if expected_obs["artifact_sha256"] != retained_obs["artifact_sha256"]:
                raise InstallationContractError("report observation artifact_sha256 drift")
            if expected_obs["sample_metadata_path"] != retained_obs["sample_metadata_path"]:
                raise InstallationContractError("report observation sample_metadata_path drift")
            if expected_obs["sample_metadata_sha256"] != retained_obs["sample_metadata_sha256"]:
                raise InstallationContractError("report observation sample_metadata_sha256 drift")
            if expected_obs["id"] != retained_obs["id"]:
                raise InstallationContractError("report observation id drift")
            if expected_obs["asset_count"] != retained_obs["asset_count"]:
                raise InstallationContractError("report observation asset_count drift")
        capture_doc = wave2_capture_document()
        return {
            "asset_count": 7,
            "assets_are_runtime_not_install_payload": True,
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "observation_count": 4,
            "observations": report_observation_facts,
            "optional_updown_and_html_reference_qualification_open": True,
            "oracle_execution_status": "captured",
            "runtime_assets": assets,
            "source_bindings": [asset_names, asset_generation, asset_writers],
        }
    if case_id == "INST-LICENSE-001":
        capture_doc = wave2_capture_document()
        return {
            "capture_artifact": capture_artifact_for_case(case_id, capture_doc),
            "copying_in_install_payload": False,
            "copying_in_source_archive_manifest": True,
            "oracle_execution_status": "captured",
            "retained_tree_contains_copying": any("COPYING" in entry["path"] for entry in entries),
            "source_bindings": [dist_manifest, install_payload],
            "upstream_omission_is_not_permission_to_omit": True,
        }
    raise InstallationContractError(f"unknown installation case id: {case_id}")


def expected_case_record(
    case_id: str,
    upstream_root: Path,
    tree: dict[str, Any],
    assets: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    facts = expected_case_independent_facts(case_id, upstream_root, tree, assets, observations)
    observation_ids = (
        [item["id"] for item in facts["observations"]]
        if case_id == "INST-REPORT-ASSET-001"
        else []
    )
    return {
        "id": case_id,
        "family": CASE_FAMILY_BY_ID[case_id],
        "role": CASE_ROLE_BY_ID[case_id],
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_evidence": [],
        "source_closure_ids": list(CASE_SOURCE_CLOSURE_IDS[case_id]),
        "layout_contract_ids": list(CASE_LAYOUT_IDS[case_id]),
        "failure_contract_ids": list(CASE_FAILURE_IDS[case_id]),
        "observation_ids": observation_ids,
        "independent_facts": facts,
        "facts_sha256": sha256_bytes(canonical_json(facts).encode("ascii")),
    }


def expected_case_records_document(
    upstream_root: Path,
    tree: dict[str, Any],
    assets: list[dict[str, Any]],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    cases = [
        expected_case_record(case_id, upstream_root, tree, assets, observations)
        for case_id in CASE_RECORD_ORDER
    ]
    return {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "case_count": 13,
        "cases": cases,
    }


def json_values_equal(left: object, right: object) -> bool:
    """Type-sensitive JSON equality: bool is not int, 1 is not 1.0."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if set(left) != set(right):
            return False
        return all(json_values_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        if len(left) != len(right):
            return False
        return all(json_values_equal(left_item, right_item) for left_item, right_item in zip(left, right))
    return left == right


def validate_case_records_schema(document: dict[str, Any]) -> None:
    schema = load_json(CASE_RECORDS_SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise InstallationContractError(f"installation case-records schema is invalid: {error.message}") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise InstallationContractError(
            f"installation case-records schema failure at {location}: {errors[0].message}"
        )


def load_case_records() -> dict[str, Any]:
    if not CASE_RECORDS_PATH.is_file():
        raise InstallationContractError("installation case records are missing")
    raw = CASE_RECORDS_PATH.read_bytes()
    actual = sha256_bytes(raw)
    if actual != EXPECTED_CASE_RECORDS_SHA256:
        raise InstallationContractError(
            "installation case-records artifact drift: "
            f"expected={EXPECTED_CASE_RECORDS_SHA256} actual={actual}"
        )
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InstallationContractError("installation case records are not canonical ASCII JSON") from error
    if not isinstance(document, dict):
        raise InstallationContractError("installation case records root must be an object")
    validate_case_records_schema(document)
    if document.get("product_compatibility_evidence") is not False:
        raise InstallationContractError("installation case records claim product compatibility")
    if document.get("evidence_status") != "oracle_reference" or document.get("execution_status") != "planned":
        raise InstallationContractError("installation case records evidence status drift")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 13:
        raise InstallationContractError("installation case records must contain exactly 13 cases")
    ids = [case.get("id") for case in cases]
    if ids != list(CASE_RECORD_ORDER):
        raise InstallationContractError(f"installation case-record order drift: {ids}")
    for case in cases:
        if not isinstance(case, dict):
            raise InstallationContractError("installation case record is not an object")
        case_id = case.get("id")
        if case_id not in CASE_FAMILY_BY_ID:
            raise InstallationContractError(f"installation case id unknown: {case_id}")
        if case.get("family") != CASE_FAMILY_BY_ID[case_id]:
            raise InstallationContractError(f"installation case family drift: {case_id}")
        if case.get("role") != CASE_ROLE_BY_ID[case_id]:
            raise InstallationContractError(f"installation case role drift: {case_id}")
        if case.get("product_evidence"):
            raise InstallationContractError(f"installation case product evidence: {case_id}")
        if tuple(case.get("source_closure_ids", ())) != CASE_SOURCE_CLOSURE_IDS[case_id]:
            raise InstallationContractError(f"installation case source_closure_ids drift: {case_id}")
        if tuple(case.get("layout_contract_ids", ())) != CASE_LAYOUT_IDS[case_id]:
            raise InstallationContractError(f"installation case layout_contract_ids drift: {case_id}")
        if tuple(case.get("failure_contract_ids", ())) != CASE_FAILURE_IDS[case_id]:
            raise InstallationContractError(f"installation case failure_contract_ids drift: {case_id}")
        facts = case.get("independent_facts")
        if not isinstance(facts, dict):
            raise InstallationContractError(f"installation case facts missing: {case_id}")
        facts_bytes = canonical_json(facts).encode("ascii")
        if case.get("facts_sha256") != sha256_bytes(facts_bytes):
            raise InstallationContractError(f"installation case facts hash drift: {case_id}")
        # closed independent-facts must not self-certify only through nested hashes without identity
        if "product_compatibility_evidence" in facts and facts["product_compatibility_evidence"] is not False:
            raise InstallationContractError(f"installation case facts claim product compatibility: {case_id}")
    return document


def case_records_binding() -> dict[str, Any]:
    document = load_case_records()
    return {
        "path": "compat/installation/oracle-case-records.json",
        "schema_path": "compat/installation/oracle-case-records.schema.json",
        "sha256": EXPECTED_CASE_RECORDS_SHA256,
        "case_count": 13,
        "evidence_status": "oracle_reference",
        "execution_status": "planned",
        "product_compatibility_evidence": False,
        "case_ids": [case["id"] for case in document["cases"]],
        "case_fact_sha256s": [
            {"id": case["id"], "facts_sha256": case["facts_sha256"]}
            for case in document["cases"]
        ],
    }


def validate_case_records_against_contract(
    document: dict[str, Any],
    upstream_root: Path,
    tree: dict[str, Any],
    assets: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    closures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = load_case_records()
    expected_records = expected_case_records_document(upstream_root, tree, assets, observations)
    if not json_values_equal(records, expected_records):
        raise InstallationContractError("installation case records drift from independently generated facts")

    closure_ids = {closure["id"] for closure in closures}
    layout_ids = set(document["layout_contract_ids"])
    failure_ids = set(document["failure_contract_ids"])
    observation_by_id = {observation["id"]: observation for observation in observations}
    retained_observation_ids = [observation["id"] for observation in observations]
    asset_by_name = {asset["name"]: asset for asset in assets}
    summaries = []

    for case, expected_case in zip(records["cases"], expected_records["cases"]):
        if case["id"] != expected_case["id"]:
            raise InstallationContractError(f"installation case order drift: {case['id']}")
        if case["family"] != CASE_FAMILY_BY_ID[case["id"]] or case["role"] != CASE_ROLE_BY_ID[case["id"]]:
            raise InstallationContractError(f"installation case identity drift: {case['id']}")
        if tuple(case["source_closure_ids"]) != CASE_SOURCE_CLOSURE_IDS[case["id"]]:
            raise InstallationContractError(f"installation case source_closure_ids drift: {case['id']}")
        if tuple(case["layout_contract_ids"]) != CASE_LAYOUT_IDS[case["id"]]:
            raise InstallationContractError(f"installation case layout_contract_ids drift: {case['id']}")
        if tuple(case["failure_contract_ids"]) != CASE_FAILURE_IDS[case["id"]]:
            raise InstallationContractError(f"installation case failure_contract_ids drift: {case['id']}")
        if not json_values_equal(case["source_closure_ids"], expected_case["source_closure_ids"]):
            raise InstallationContractError(f"installation case source_closure_ids mismatch: {case['id']}")
        if not json_values_equal(case["layout_contract_ids"], expected_case["layout_contract_ids"]):
            raise InstallationContractError(f"installation case layout_contract_ids mismatch: {case['id']}")
        if not json_values_equal(case["failure_contract_ids"], expected_case["failure_contract_ids"]):
            raise InstallationContractError(f"installation case failure_contract_ids mismatch: {case['id']}")
        if not json_values_equal(case["observation_ids"], expected_case["observation_ids"]):
            raise InstallationContractError(f"installation case observation_ids mismatch: {case['id']}")
        if not json_values_equal(case["independent_facts"], expected_case["independent_facts"]):
            raise InstallationContractError(f"installation case independent_facts mismatch: {case['id']}")
        if case["facts_sha256"] != expected_case["facts_sha256"]:
            raise InstallationContractError(f"installation case facts_sha256 mismatch: {case['id']}")

        for source_id in case["source_closure_ids"]:
            if source_id not in closure_ids:
                raise InstallationContractError(f"case source closure unbound: {case['id']}:{source_id}")
        for layout_id in case["layout_contract_ids"]:
            if layout_id not in layout_ids:
                raise InstallationContractError(f"case layout id unbound: {case['id']}:{layout_id}")
        for failure_id in case["failure_contract_ids"]:
            if failure_id not in failure_ids:
                raise InstallationContractError(f"case failure id unbound: {case['id']}:{failure_id}")
        for observation_id in case["observation_ids"]:
            if observation_id not in observation_by_id:
                raise InstallationContractError(f"case observation unbound: {case['id']}:{observation_id}")

        facts = case["independent_facts"]
        # INST-LAYOUT-001 exception: nested source_bindings are intentionally
        # absent. Source identity is bound only via top-level source_closure_ids
        # plus tree partition facts regenerated from the pinned installed-tree
        # lock. All other cases require nested source_bindings digests.
        source_bindings = facts.get("source_bindings", [])
        if case["id"] != "INST-LAYOUT-001":
            if not isinstance(source_bindings, list) or not source_bindings:
                raise InstallationContractError(f"installation case source_bindings missing: {case['id']}")
            if case["id"] == "INST-PATH-001":
                capture_artifacts = facts.get("capture_artifacts")
                expected_capture = capture_binding_for_case(case["id"])
                if not json_values_equal(capture_artifacts, expected_capture):
                    raise InstallationContractError(
                        f"installation case capture_artifacts drift: {case['id']}"
                    )
            else:
                capture_artifact = facts.get("capture_artifact")
                if not isinstance(capture_artifact, dict):
                    raise InstallationContractError(
                        f"installation case capture_artifact missing: {case['id']}"
                    )
                expected_capture = capture_binding_for_case(case["id"])
                if not json_values_equal(capture_artifact, expected_capture):
                    raise InstallationContractError(
                        f"installation case capture_artifact drift: {case['id']}"
                    )
            if facts.get("oracle_execution_status") != "captured":
                raise InstallationContractError(f"installation case capture status drift: {case['id']}")
            for binding in source_bindings:
                if not isinstance(binding, dict):
                    raise InstallationContractError(f"installation case source binding shape drift: {case['id']}")
                expected_binding = source_binding(
                    upstream_root,
                    binding["path"],
                    binding["line_start"],
                    binding["line_end"],
                )
                if not json_values_equal(binding, expected_binding):
                    raise InstallationContractError(
                        f"installation case source binding digest drift: {case['id']}:{binding['path']}"
                    )

        if case["id"] == "INST-LAYOUT-001":
            if not json_values_equal(facts["support_script_names"], sorted(
                Path(entry["path"]).name for entry in group_entries(tree_entries())["support_scripts"]
            )):
                raise InstallationContractError("INST-LAYOUT-001 support_script_names drift")
            if facts["support_script_count"] != 23:
                raise InstallationContractError("INST-LAYOUT-001 support_script_count drift")
            if facts["tree_entry_count"] != tree["entry_count"]:
                raise InstallationContractError("INST-LAYOUT-001 tree_entry_count drift")
            if facts["manifest_sha256"] != tree["manifest_sha256"]:
                raise InstallationContractError("INST-LAYOUT-001 manifest_sha256 drift")
            directory = wave2_directory_companion()
            if facts.get("directory_companion_retained") is not True:
                raise InstallationContractError("INST-LAYOUT-001 directory companion not retained")
            if facts.get("directory_entries_retained") is not False:
                raise InstallationContractError("INST-LAYOUT-001 baseline directory claim drift")
            if facts.get("directory_companion_entry_count") != directory["entry_count"]:
                raise InstallationContractError("INST-LAYOUT-001 directory companion count drift")
            if facts.get("directory_companion_sha256") != directory["sha256"]:
                raise InstallationContractError("INST-LAYOUT-001 directory companion hash drift")
            if facts.get("directory_companion_path") != directory["path"]:
                raise InstallationContractError("INST-LAYOUT-001 directory companion path drift")
            expected_layout_capture = capture_binding_for_case("INST-LAYOUT-001")
            if not json_values_equal(facts.get("capture_artifact"), expected_layout_capture):
                raise InstallationContractError("INST-LAYOUT-001 capture_artifact drift")

        if case["id"] == "INST-REPORT-ASSET-001":
            if case["observation_ids"] != retained_observation_ids:
                raise InstallationContractError("INST-REPORT-ASSET-001 observation_ids mapping drift")
            if not json_values_equal(facts["runtime_assets"], assets):
                raise InstallationContractError("INST-REPORT-ASSET-001 runtime_assets drift")
            if len(facts["observations"]) != 4:
                raise InstallationContractError("INST-REPORT-ASSET-001 observation count drift")
            for observed_fact, retained in zip(facts["observations"], observations):
                if observed_fact["id"] != retained["id"]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 observation id mapping drift")
                if observed_fact["artifact_path"] != retained["artifact_path"]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 observation artifact_path drift")
                if observed_fact["artifact_sha256"] != retained["artifact_sha256"]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 observation artifact_sha256 drift")
                if observed_fact["sample_metadata_path"] != retained["sample_metadata_path"]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 sample_metadata_path drift")
                if observed_fact["sample_metadata_sha256"] != retained["sample_metadata_sha256"]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 sample_metadata_sha256 drift")
                if observed_fact["artifact_sha256"] != EXPECTED_ASSET_SAMPLE_HASHES[observed_fact["artifact_path"]]:
                    raise InstallationContractError("INST-REPORT-ASSET-001 retained artifact hash drift")
                if (
                    observed_fact["sample_metadata_sha256"]
                    != EXPECTED_SAMPLE_METADATA_HASHES[observed_fact["sample_metadata_path"]]
                ):
                    raise InstallationContractError("INST-REPORT-ASSET-001 retained sample metadata hash drift")
                assets_map = observed_fact["assets"]
                if set(assets_map) != set(asset_by_name):
                    raise InstallationContractError("INST-REPORT-ASSET-001 observation asset set drift")
                for name, asset in assets_map.items():
                    expected_asset = asset_by_name[name]
                    if (
                        asset.get("bytes") != expected_asset["bytes"]
                        or asset.get("sha256") != expected_asset["sha256"]
                        or asset.get("status") != "created"
                    ):
                        raise InstallationContractError(
                            f"INST-REPORT-ASSET-001 observation asset identity drift: {name}"
                        )

        summaries.append({
            "id": case["id"],
            "family": case["family"],
            "role": case["role"],
            "evidence_status": case["evidence_status"],
            "execution_status": case["execution_status"],
            "facts_sha256": case["facts_sha256"],
            "source_closure_count": len(case["source_closure_ids"]),
            "layout_contract_count": len(case["layout_contract_ids"]),
            "failure_contract_count": len(case["failure_contract_ids"]),
            "observation_count": len(case["observation_ids"]),
            "product_evidence": [],
        })
    return summaries


def build_document(upstream_root: Path) -> dict[str, Any]:
    tree = installed_tree()
    assets, observations = runtime_assets()
    closures = [source_closure(upstream_root, value) for value in SOURCE_CLOSURES]
    planned = planned_case_ids(upstream_root)
    bindings = artifact_bindings()
    case_binding = case_records_binding()
    bindings.append({"path": case_binding["path"], "sha256": case_binding["sha256"]})
    document = {
        "schema_version": 1,
        "upstream_release": "v2.5",
        "upstream_commit": UPSTREAM_COMMIT,
        "scope": (
            "LCOV 2.5 installation layout, build/failure boundaries, retained "
            "installed-tree evidence, report asset references, and exact Oracle "
            "reference-only case records for the 13 INST identities"
        ),
        "artifact_bindings": bindings,
        "oracle_manifest": validate_oracle_manifest(tree),
        "benchmark_result": validate_benchmark_result(),
        "source_closures": closures,
        "installed_tree": tree,
        "layout_contract_ids": list(LAYOUT_IDS),
        "failure_contract_ids": list(FAILURE_IDS),
        "planned_case_ids": planned,
        "planned_case_evidence_status": "planned",
        "planned_case_product_evidence": [],
        "oracle_case_records": case_binding,
        "oracle_case_summaries": [],
        "runtime_assets": assets,
        "runtime_asset_observations": observations,
        "oracle_observation_evidence_status": "oracle_reference",
        "oracle_observation_product_evidence": [],
        "known_evidence_gaps": list(EVIDENCE_GAPS),
        "totals": {
            "artifact_bindings": (
                len(EXPECTED_ARTIFACT_HASHES)
                + len(EXPECTED_ASSET_SAMPLE_HASHES)
                + len(EXPECTED_SAMPLE_METADATA_HASHES)
                + len(EXPECTED_WAVE2_ARTIFACT_HASHES)
                + 1
            ),
            "source_closures": len(closures),
            "source_lines": sum(closure["line_count"] for closure in closures),
            "installed_tree_entries": tree["entry_count"],
            "installed_tree_groups": len(tree["groups"]),
            "layout_contract_ids": len(LAYOUT_IDS),
            "failure_contract_ids": len(FAILURE_IDS),
            "planned_cases": len(PLANNED_CASE_IDS),
            "oracle_case_records": 13,
            "runtime_assets": len(assets),
            "runtime_asset_observations": len(observations),
        },
        "product_compatibility_evidence": False,
    }
    document["oracle_case_summaries"] = validate_case_records_against_contract(
        document, upstream_root, tree, assets, observations, closures
    )
    return document


def validate_schema(document: dict[str, Any]) -> None:
    schema = load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise InstallationContractError(f"installation schema is invalid: {error.message}") from error
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise InstallationContractError(f"installation schema failure at {location}: {errors[0].message}")


def validate_upstream_identity(upstream_root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stdout.strip() != UPSTREAM_COMMIT:
        raise InstallationContractError("installation contract upstream commit mismatch")


def validate_document(document: dict[str, Any], upstream_root: Path) -> None:
    validate_schema(document)
    expected = build_document(upstream_root)
    for key in (
        "upstream_commit", "artifact_bindings", "oracle_manifest", "benchmark_result", "source_closures",
        "installed_tree", "layout_contract_ids", "failure_contract_ids", "planned_case_ids",
        "oracle_case_records", "oracle_case_summaries",
        "runtime_assets", "runtime_asset_observations", "known_evidence_gaps", "totals",
    ):
        if not json_values_equal(document.get(key), expected[key]):
            raise InstallationContractError(f"installation contract drift: {key}")
    if document["planned_case_evidence_status"] != "planned" or document["planned_case_product_evidence"]:
        raise InstallationContractError("installation planned cases claim evidence")
    if document["oracle_observation_evidence_status"] != "oracle_reference" or document["oracle_observation_product_evidence"]:
        raise InstallationContractError("installation Oracle references claim product evidence")
    if document.get("oracle_case_records", {}).get("evidence_status") != "oracle_reference":
        raise InstallationContractError("installation case records claim non-reference evidence")
    if document.get("oracle_case_records", {}).get("execution_status") != "planned":
        raise InstallationContractError("installation case records claim execution evidence")
    if document.get("oracle_case_records", {}).get("product_compatibility_evidence"):
        raise InstallationContractError("installation case records claim product compatibility")
    if document["product_compatibility_evidence"]:
        raise InstallationContractError("installation contract claims product compatibility")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", type=Path, default=DEFAULT_UPSTREAM_ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    upstream_root = args.upstream_root.resolve()
    validate_upstream_identity(upstream_root)
    document = build_document(upstream_root)
    validate_document(document, upstream_root)
    content = canonical_json(document).encode("ascii")
    if args.write:
        OUTPUT_PATH.write_bytes(content)
        print(f"INSTALLATION_CONTRACT_WRITTEN path={OUTPUT_PATH.relative_to(ROOT)}")
    if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_bytes() != content:
        raise InstallationContractError("committed installation contract differs from generation")
    print(
        "INSTALLATION_CONTRACT_OK "
        f"tree_entries={document['totals']['installed_tree_entries']} "
        f"groups={document['totals']['installed_tree_groups']} "
        f"source_closures={document['totals']['source_closures']} "
        f"planned_cases={document['totals']['planned_cases']} "
        f"oracle_case_records={document['totals']['oracle_case_records']} "
        f"runtime_assets={document['totals']['runtime_assets']} "
        f"asset_observations={document['totals']['runtime_asset_observations']} "
        "product_compatibility=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
