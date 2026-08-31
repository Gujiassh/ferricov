import hashlib, importlib.util, json, pathlib, shutil, tempfile, unittest

MODULE_PATH = pathlib.Path(__file__).with_name("validate_artifacts.py")
SPEC = importlib.util.spec_from_file_location("validate_artifacts", MODULE_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(VALIDATOR)
REPO_FUZZ = pathlib.Path(__file__).resolve().parents[1]

class ValidatorMutationTests(unittest.TestCase):
    def test_repository_manifest_passes(self): VALIDATOR.validate_manifest(REPO_FUZZ)
    def test_mutated_corpus_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory); shutil.copytree(REPO_FUZZ/"corpus", root/"corpus")
            (root/"corpus/m1_fz_lex_001/all-record-prefixes.trace").write_bytes(b"mutated")
            with self.assertRaisesRegex(ValueError, "hash mismatch"): VALIDATOR.validate_manifest(root)
    def test_sidecar_artifact_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact=pathlib.Path(directory)/"crash.minimized"; artifact.write_bytes(b"changed")
            raw=pathlib.Path(directory)/"crash.raw"; raw.write_bytes(b"original")
            sidecar=pathlib.Path(str(artifact)+".json"); value={"schema_version":1,"target_id":"M1-FZ-LEX-001","case_id":"case","seed":1,"raw_sha256":hashlib.sha256(b"original").hexdigest(),"minimized_sha256":hashlib.sha256(b"original-minimized").hexdigest(),"raw_artifact":"crash.raw","first_failing_operation":"parse","semantic_snapshots":{},"process":{"exit_code":1,"signal":None,"timed_out":False,"stdout":"","stderr":"failure"},"runtime_manifest":{},"origin_ids":["M1-FZ-LEX-001"]}; sidecar.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "artifact hash mismatch"): VALIDATOR.validate_sidecar(sidecar)
if __name__ == "__main__": unittest.main()
