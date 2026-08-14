#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[2]
SUITE_PATH=ROOT/"compat/cases/m0-residual-b-lang-ext-contract.json"
SUITE_SCHEMA_PATH=ROOT/"compat/schema/suite.schema.json"
SUITE_ID="m0-residual-b-lang-ext-contract"
FIXTURE="compat/fixtures/m0-residual-b-lang-ext-contract"
CANONICAL_CASES={
  "m0-residual-b-lang-ext-contract-control": {"arguments": ["--config-file", "control.lcovrc", "-a", "input.info", "-o", "out.info", "--filter", "region,brace,directive", "--ignore-errors", "source,unsupported,inconsistent,unused,empty"], "command": "lcov", "comparisons": [{"dimension": "exit", "normalizer": "exact-v1"}, {"dimension": "filesystem", "normalizer": "exact-v1"}]},
  "m0-residual-b-lang-ext-contract-c-file-extensions": {"arguments": ["--config-file", "c-file-extensions.lcovrc", "-a", "input.info", "-o", "out.info", "--filter", "region,brace,directive", "--ignore-errors", "source,unsupported,inconsistent,unused,empty"], "command": "lcov", "comparisons": [{"dimension": "exit", "normalizer": "exact-v1"}, {"dimension": "filesystem", "normalizer": "exact-v1"}]},
  "m0-residual-b-lang-ext-contract-java-file-extensions": {"arguments": ["--config-file", "java-file-extensions.lcovrc", "-a", "input.info", "-o", "out.info", "--filter", "region,brace,directive", "--ignore-errors", "source,unsupported,inconsistent,unused,empty"], "command": "lcov", "comparisons": [{"dimension": "exit", "normalizer": "exact-v1"}, {"dimension": "filesystem", "normalizer": "exact-v1"}]},
  "m0-residual-b-lang-ext-contract-python-file-extensions": {"arguments": ["--config-file", "python-file-extensions.lcovrc", "-a", "input.info", "-o", "out.info", "--filter", "region,brace,directive", "--ignore-errors", "source,unsupported,inconsistent,unused,empty"], "command": "lcov", "comparisons": [{"dimension": "exit", "normalizer": "exact-v1"}, {"dimension": "filesystem", "normalizer": "exact-v1"}]},
  "m0-residual-b-lang-ext-contract-perl-file-extensions": {"arguments": ["--config-file", "perl-file-extensions.lcovrc", "-a", "input.info", "-o", "out.info", "--filter", "region,brace,directive", "--ignore-errors", "source,unsupported,inconsistent,unused,empty"], "command": "lcov", "comparisons": [{"dimension": "exit", "normalizer": "exact-v1"}, {"dimension": "filesystem", "normalizer": "exact-v1"}]},
}
class Err(RuntimeError): pass
def validate_suite_document(document):
  schema=json.loads(SUITE_SCHEMA_PATH.read_text()); Draft202012Validator.check_schema(schema)
  errs=sorted(Draft202012Validator(schema).iter_errors(document), key=lambda e:list(e.path))
  if errs: raise Err(errs[0].message)
  if document.get("suite_id")!=SUITE_ID or document.get("evidence_scope")!="compatibility" or document.get("schema_version")!=1: raise Err("header")
  cases=document.get("cases")
  if not isinstance(cases,list) or [c.get("id") for c in cases]!=list(CANONICAL_CASES): raise Err("ids")
  for case in cases:
    exp=CANONICAL_CASES[case["id"]]
    if case.get("surface")!="config" or case.get("command")!=exp["command"] or case.get("fixture")!=FIXTURE: raise Err(case["id"])
    if case.get("arguments")!=exp["arguments"] or case.get("comparisons")!=exp["comparisons"]: raise Err(case["id"]+" argv")
    if {i["dimension"] for i in case["comparisons"]}!={"exit","filesystem"}: raise Err("dims")
def validate_committed_suite():
  validate_suite_document(json.loads(SUITE_PATH.read_text()))
if __name__=="__main__":
  validate_committed_suite(); print("OK", SUITE_ID)
