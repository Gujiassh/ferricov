//! Coverage domain entities and invariants.
//!
//! M1-CORE-001 provides the byte, identity, numeric, and branch-taken
//! primitives required by `coverage-model.md`.
//!
//! M1-CORE-002 adds independent aggregate and testcase-family coverage stores,
//! including explicit empty family values and a distinct observable totals
//! holder.
//!
//! M1-CORE-003 adds function dual indexes, ordered branch blocks, and MC/DC
//! dual-sense group structure with structural invariants.

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
pub use branch_store::{
    BranchBlock, BranchCoverage, BranchEdge, BranchError, BranchKind, BranchLine,
};
pub use bytes::ByteString;
pub use function::{
    effective_alias_length, is_lambda_alias, FunctionError, FunctionGroup, FunctionTable,
};
pub use identity::{SourceIdentity, SourceLookupKey, TestName};
pub use keys::LineKey;
pub use line::LineCoverage;
pub use mcdc::{
    GroupSizeKey, McdcCoverage, McdcError, McdcExpression, McdcLine, SenseCoverage,
};
pub use numeric::{
    AddError, CountValidation, CoverageCount, NumericAtom, NumericClass, NumericKind,
};
pub use stores::{
    CoverageDatabase, CoverageStore, SourceCoverage, TestcaseStores, TotalState,
};
