import hashlib, importlib.util, json, os, pathlib, shutil, tempfile, time, unittest

PATH=pathlib.Path(__file__).with_name("retain_finding.py")
SPEC=importlib.util.spec_from_file_location("retain_finding",PATH); MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)

class RetentionTransactionTests(unittest.TestCase):
    def test_lock_is_exclusive_and_released(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=pathlib.Path(directory)/"lock"
            with MOD.exclusive_lock(lock):
                self.assertTrue(lock.exists())
                with self.assertRaisesRegex(RuntimeError,"lock held"):
                    with MOD.exclusive_lock(lock): pass
            self.assertFalse(lock.exists())
    def test_stale_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            lock=pathlib.Path(directory)/"lock"
            lock.write_text(json.dumps({"pid":99999999,"created":time.time()-1000}))
            with MOD.exclusive_lock(lock, stale_after=1): self.assertTrue(lock.exists())
            self.assertFalse(lock.exists())
    def test_outcome_distinguishes_exit_and_signal(self):
        import subprocess
        self.assertEqual(MOD.outcome(subprocess.CompletedProcess([],7)),("exit",7))
        self.assertEqual(MOD.outcome(subprocess.CompletedProcess([],-9)),("signal",9))

    @unittest.skipUnless(os.name == "nt", "Windows fake executable fixture")
    def test_full_transaction_installs_and_updates_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory); fuzz=root/"fuzz"; (fuzz/"corpus").mkdir(parents=True); (fuzz/"scripts").mkdir()
            shutil.copy(PATH.with_name("validate_artifacts.py"),fuzz/"scripts/validate_artifacts.py")
            shutil.copy(PATH.parents[1]/"failure-sidecar.schema.json",fuzz/"failure-sidecar.schema.json")
            raw=root/"finding"; raw.write_bytes(b"failing-input")
            target="M1-FZ-LEX-001"; case="CORE009-FAIL-001"; digest=hashlib.sha256(b"seed").hexdigest()
            seed=int.from_bytes(hashlib.sha256(target.encode()+b"\0"+case.encode()+b"\0"+digest.encode()).digest()[:8],"big")
            manifest={"schema_version":1,"known_failures":[],"entries":[{"case_id":case,"sha256":digest,"targets":[target],"derived_seeds":{target:seed}}]}
            (fuzz/"corpus/manifest.json").write_text(json.dumps(manifest))
            runtime=root/"runtime.json"; runtime.write_text('{"tool":"fake"}')
            fake=root/"fake-cargo.cmd"; fake.write_text("@echo off\r\nsetlocal enabledelayedexpansion\r\nset prev=\r\nfor %%A in (%*) do ( if !prev!==--output copy /Y %~dp0finding %%~A >nul & set prev=%%~A )\r\necho deterministic crash 1>&2\r\nexit /b 1\r\n")
            old=os.environ.get("FERRICOV_CARGO_FUZZ"); os.environ["FERRICOV_CARGO_FUZZ"]=str(fake)
            try: sidecar=MOD.retain(root,target,case,raw,runtime,["M1-PROP-ROUNDTRIP-001"])
            finally:
                if old is None: os.environ.pop("FERRICOV_CARGO_FUZZ",None)
                else: os.environ["FERRICOV_CARGO_FUZZ"]=old
            self.assertTrue(sidecar.is_file()); value=json.loads(sidecar.read_text()); self.assertEqual(value["seed"],seed)
            updated=json.loads((fuzz/"corpus/manifest.json").read_text()); self.assertEqual(len(updated["known_failures"]),1)

if __name__ == "__main__": unittest.main()
