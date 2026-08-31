import importlib.util, pathlib, tempfile, unittest

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
    def test_outcome_distinguishes_exit_and_signal(self):
        import subprocess
        self.assertEqual(MOD.outcome(subprocess.CompletedProcess([],7)),("exit",7))
        self.assertEqual(MOD.outcome(subprocess.CompletedProcess([],-9)),("signal",9))

if __name__ == "__main__": unittest.main()
