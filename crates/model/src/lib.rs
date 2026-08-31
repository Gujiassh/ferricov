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
//!
//! M1-CORE-004 adds ordered union / intersect / difference algebra for coverage
//! families and thin store wrappers.

#![forbid(unsafe_code)]

mod algebra;
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

pub use algebra::{AlgebraError, AlgebraOp};
pub use branch::BranchTaken;
pub use branch_store::{
    BranchBlock, BranchCoverage, BranchEdge, BranchError, BranchKind, BranchLine,
};
pub use bytes::ByteString;
pub use function::{
    FunctionError, FunctionGroup, FunctionTable, effective_alias_length, is_lambda_alias,
};
pub use identity::{SourceIdentity, SourceLookupKey, TestName};
pub use keys::LineKey;
pub use line::LineCoverage;
pub use mcdc::{GroupSizeKey, McdcCoverage, McdcError, McdcExpression, McdcLine, SenseCoverage};
pub use numeric::{
    AddError, CountValidation, CoverageCount, NumericAtom, NumericClass, NumericKind,
};
pub use stores::{CoverageDatabase, CoverageStore, SourceCoverage, TestcaseStores, TotalState};
