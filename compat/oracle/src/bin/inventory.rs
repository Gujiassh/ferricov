use ferricov_oracle::generate_inventory;
use std::env;
use std::error::Error;
use std::fs;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args_os().skip(1);
    let upstream_root = PathBuf::from(
        args.next()
            .ok_or("usage: inventory <upstream-root> <help-snapshot-dir> <output-json>")?,
    );
    let help_dir = PathBuf::from(
        args.next()
            .ok_or("usage: inventory <upstream-root> <help-snapshot-dir> <output-json>")?,
    );
    let output_path = PathBuf::from(
        args.next()
            .ok_or("usage: inventory <upstream-root> <help-snapshot-dir> <output-json>")?,
    );
    if args.next().is_some() {
        return Err("inventory accepts exactly three arguments".into());
    }

    let inventory = generate_inventory(&upstream_root, &help_dir)?;
    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut encoded = serde_json::to_string_pretty(&inventory)?;
    encoded.push('\n');
    fs::write(output_path, encoded)?;
    Ok(())
}
