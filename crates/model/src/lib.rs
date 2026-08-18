//! Coverage domain entities and invariants.
//!
//! M1-CORE-001 provides the byte, identity, numeric, and branch-taken
//! primitives required by `coverage-model.md`.
//!
//! M1-CORE-002 adds independent aggregate and testcase-family coverage stores,
//! including explicit empty family values and a distinct observable totals
//! holder. Function/branch/MC/DC structural invariants arrive in CORE-003.

#![forbid(unsafe_code)]

mod branch;
mod branch_store;
mod bytes;
mod function;
mod identity;
mod keys;
mod line;
mod mcdc;
mod numeric;
mod stores;

pub use branch::BranchTaken;
pub use branch_store::BranchCoverage;
pub use bytes::ByteString;
pub use function::FunctionTable;
pub use identity::{SourceIdentity, SourceLookupKey, TestName};
pub use keys::LineKey;
pub use line::LineCoverage;
pub use mcdc::McdcCoverage;
pub use numeric::{
    AddError, CountValidation, CoverageCount, NumericAtom, NumericClass, NumericKind,
};
pub use stores::{
    CoverageDatabase, CoverageStore, SourceCoverage, TestcaseStores, TotalState,
};
