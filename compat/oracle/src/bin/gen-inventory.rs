// Standalone inventory generator that avoids the broken differential module.
// Remove once the controller reconciles process.rs.

use std::env;
use std::error::Error;
use std::fs;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args_os().skip(1);
    let upstream_root = PathBuf::from(
        args.next()
            .ok_or("usage: gen-inventory <upstream-root> <help-dir> <review-dir> <output-json>")?,
    );
    let help_dir = PathBuf::from(
        args.next()
            .ok_or("usage: gen-inventory <upstream-root> <help-dir> <review-dir> <output-json>")?,
    );
    let review_dir = PathBuf::from(
        args.next()
            .ok_or("usage: gen-inventory <upstream-root> <help-dir> <review-dir> <output-json>")?,
    );
    let output_path = PathBuf::from(
        args.next()
            .ok_or("usage: gen-inventory <upstream-root> <help-dir> <review-dir> <output-json>")?,
    );

    // Inline the inventory generation to avoid linking broken differential code.
    let inventory = ferricov_oracle::generate_inventory(&upstream_root, &help_dir, &review_dir)?;

    if let Some(parent) = output_path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut encoded = serde_json::to_string_pretty(&inventory)?;
    encoded.push('\n');
    fs::write(output_path, encoded)?;
    Ok(())
}
