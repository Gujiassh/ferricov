//! Coverage domain entities and invariants.
//!
//! M1-CORE-001 provides the byte, identity, numeric, and branch-taken
//! primitives required by `coverage-model.md`. Higher-level stores, algebra,
//! and parser/writer integration arrive in later CORE tasks.

#![forbid(unsafe_code)]

mod branch;
mod bytes;
mod identity;
mod numeric;

pub use branch::BranchTaken;
pub use bytes::ByteString;
pub use identity::{SourceIdentity, SourceLookupKey, TestName};
pub use numeric::{
    AddError, CountValidation, CoverageCount, NumericAtom, NumericClass, NumericKind,
};
