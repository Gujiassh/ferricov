use ferricov_oracle::{DifferentialRunner, Launcher, Suite};
use serde::de::DeserializeOwned;
use std::env;
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args_os().skip(1);
    let first = required_path(&mut args)?;
    if first == Path::new("--verify-result") {
        let case_root = required_path(&mut args)?;
        if args.next().is_some() {
            return Err("usage: differential --verify-result <case-result-dir>".into());
        }
        return DifferentialRunner::verify_result_artifacts(&case_root);
    }
    let suite_path = first;
    let reference_path = required_path(&mut args)?;
    let candidate_path = required_path(&mut args)?;
    let output_path = required_path(&mut args)?;
    if args.next().is_some() {
        return Err(usage().into());
    }

    let repository_root = env::current_dir()?;
    let suite: Suite = read_json(&suite_path)?;
    let reference: Launcher = read_json(&reference_path)?;
    let candidate: Launcher = read_json(&candidate_path)?;
    let mut runner = DifferentialRunner::new(repository_root, reference, candidate)?;
    let outcome = runner.run(&suite, &output_path)?;
    if outcome.failed > 0 {
        return Err(format!(
            "differential suite failed: {} passed, {} failed",
            outcome.passed, outcome.failed
        )
        .into());
    }
    Ok(())
}

fn required_path(
    args: &mut impl Iterator<Item = std::ffi::OsString>,
) -> Result<PathBuf, Box<dyn Error>> {
    args.next().map(PathBuf::from).ok_or_else(|| usage().into())
}

fn usage() -> &'static str {
    "usage: differential <suite> <reference-launcher> <candidate-launcher> <output-dir>\n       differential --verify-result <case-result-dir>"
}

fn read_json<T: DeserializeOwned>(path: &Path) -> Result<T, Box<dyn Error>> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
