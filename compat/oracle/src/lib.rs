//! Differential execution and compatibility comparison support.

pub mod benchmark;
pub mod correctness;
mod differential;
pub mod inventory;
mod normalizer;

pub use differential::{DifferentialRunner, Launcher, Suite, SuiteOutcome};
pub use inventory::generate_inventory;
pub use normalizer::{NormalizerId, normalize};

/// LCOV release used as the first compatibility target.
pub const UPSTREAM_RELEASE: &str = "v2.5";

/// Immutable upstream commit used by the Oracle.
pub const UPSTREAM_COMMIT: &str = "74c8eabbb36d7cf2454d3f0ea37bf1337641cbc5";
