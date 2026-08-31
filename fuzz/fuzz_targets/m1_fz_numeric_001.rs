#![no_main]
use ferricov_tracefile::fuzzing::{FuzzTarget, HarnessBudget, run};
use libfuzzer_sys::fuzz_target;
fuzz_target!(|data: &[u8]| run(FuzzTarget::Numeric, data, HarnessBudget::CI_SMOKE));
