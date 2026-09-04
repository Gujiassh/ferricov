//! Process-isolated CORE-009 test worker. The parent owns deadline/RSS policy.
use std::io::{self, Read};
use std::time::Duration;

use ferricov_tracefile::fuzzing::{FuzzTarget, HarnessBudget, run};

fn main() {
    let mode = std::env::args().nth(1).unwrap_or_else(|| "normal".into());
    match mode.as_str() {
        "sleep" => std::thread::sleep(Duration::from_secs(30)),
        "allocate" => {
            let bytes = std::env::args()
                .nth(2)
                .and_then(|v| v.parse().ok())
                .unwrap_or(768usize << 20);
            let mut allocation = vec![0u8; bytes];
            for page in allocation.chunks_mut(4096) {
                page[0] = 1;
            }
            std::hint::black_box(allocation);
        }
        "normal" => {
            let mut input = Vec::new();
            io::stdin()
                .read_to_end(&mut input)
                .expect("read case bytes");
            let target = match std::env::args().nth(2).as_deref() {
                Some("M1-FZ-LEX-001") => FuzzTarget::Lex,
                Some("M1-FZ-WRITER-001") => FuzzTarget::Writer,
                Some("M1-FZ-ROUNDTRIP-001") => FuzzTarget::Roundtrip,
                Some("M1-FZ-NUMERIC-001") => FuzzTarget::Numeric,
                Some("M1-FZ-LINE-ALGEBRA-001") => FuzzTarget::LineAlgebra,
                Some("M1-FZ-FUNCTION-ALGEBRA-001") => FuzzTarget::FunctionAlgebra,
                Some("M1-FZ-BRANCH-ALGEBRA-001") => FuzzTarget::BranchAlgebra,
                Some("M1-FZ-MCDC-ALGEBRA-001") => FuzzTarget::McdcAlgebra,
                Some("M1-FZ-STATEFUL-001") => FuzzTarget::Stateful,
                Some(other) => {
                    eprintln!("CORE009_WORKER_REJECT kind=unknown_target target={other}");
                    std::process::exit(64);
                }
                None => {
                    eprintln!("CORE009_WORKER_REJECT kind=missing_target");
                    std::process::exit(64);
                }
            };
            if let Err(failure) = run(target, &input, HarnessBudget::CI_SMOKE) {
                eprintln!("CORE009_WORKER_FAILURE kind={failure:?}");
                std::process::exit(2);
            }
            println!("CORE009_WORKER_OK bytes={}", input.len());
        }
        _ => {
            eprintln!("unknown worker mode");
            std::process::exit(64);
        }
    }
}
