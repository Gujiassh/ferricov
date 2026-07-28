use ferricov_oracle::correctness::run_baseline;
use std::env;
use std::error::Error;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn Error>> {
    let mut arguments = env::args_os().skip(1);
    let case_contract = required_path(&mut arguments)?;
    let manifest = required_path(&mut arguments)?;
    let launcher = required_path(&mut arguments)?;
    let output = required_path(&mut arguments)?;
    if arguments.next().is_some() {
        return Err(usage().into());
    }

    let repository_root = env::current_dir()?;
    let result = run_baseline(
        &repository_root,
        &case_contract,
        &manifest,
        &launcher,
        &output,
    )?;
    println!(
        "ORACLE_CORRECTNESS_BASELINE_RECORDED path={} status=complete product_compatibility=false",
        result.display()
    );
    Ok(())
}

fn required_path(
    arguments: &mut impl Iterator<Item = std::ffi::OsString>,
) -> Result<PathBuf, Box<dyn Error>> {
    arguments
        .next()
        .map(PathBuf::from)
        .ok_or_else(|| usage().into())
}

fn usage() -> &'static str {
    "usage: oracle-correctness-baseline <case-contract> <execution-manifest> <launcher> <output-dir>"
}
