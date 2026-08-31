//! Branch taken-state primitives.
//!
//! `NeverEvaluated` corresponds to the BRDA `-` token and is distinct from an
//! evaluated zero count.

use crate::numeric::CoverageCount;

/// Branch taken state: never evaluated (`-`) or an evaluated coverage count.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum BranchTaken {
    /// BRDA taken field was `-`. Contributes no hit.
    NeverEvaluated,
    /// Evaluated taken count retained as a coverage count.
    Evaluated(CoverageCount),
}

impl BranchTaken {
    /// Construct the never-evaluated state for `-`.
    #[must_use]
    pub const fn never_evaluated() -> Self {
        Self::NeverEvaluated
    }

    /// Construct an evaluated taken state from a coverage count.
    #[must_use]
    pub fn evaluated(count: CoverageCount) -> Self {
        Self::Evaluated(count)
    }

    /// Parse a BRDA taken token.
    ///
    /// Exact `-` becomes [`BranchTaken::NeverEvaluated`]. Any other token is
    /// retained as an evaluated [`CoverageCount`] lexeme (including `0`).
    #[must_use]
    pub fn from_token(token: impl AsRef<[u8]>) -> Self {
        let token = token.as_ref();
        if token == b"-" {
            Self::NeverEvaluated
        } else {
            Self::Evaluated(CoverageCount::from_lexeme(token.to_vec()))
        }
    }

    /// Return `true` for `-`.
    #[must_use]
    pub const fn is_never_evaluated(&self) -> bool {
        matches!(self, Self::NeverEvaluated)
    }

    /// Return `true` when this state contributes a hit.
    ///
    /// `NeverEvaluated` never contributes. Evaluated counts contribute when
    /// [`CoverageCount::is_positive`] is true.
    #[must_use]
    pub fn contributes_hit(&self) -> bool {
        match self {
            Self::NeverEvaluated => false,
            Self::Evaluated(count) => count.is_positive(),
        }
    }

    /// Merge branch taken states with Oracle right-identity for `-`.
    ///
    /// Rules encoded here for CORE-001:
    /// - right `NeverEvaluated` is an identity (left wins);
    /// - left `NeverEvaluated` with evaluated right is replaced by right;
    /// - both evaluated: ordered [`CoverageCount::add`].
    pub fn merge_with(&self, right: &Self) -> Result<Self, crate::numeric::AddError> {
        match (self, right) {
            (left, Self::NeverEvaluated) => Ok(left.clone()),
            (Self::NeverEvaluated, right) => Ok(right.clone()),
            (Self::Evaluated(left), Self::Evaluated(right)) => {
                Ok(Self::Evaluated(left.add(right)?))
            }
        }
    }

    /// Borrow the evaluated count when present.
    #[must_use]
    pub fn as_evaluated(&self) -> Option<&CoverageCount> {
        match self {
            Self::NeverEvaluated => None,
            Self::Evaluated(count) => Some(count),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::BranchTaken;
    use crate::numeric::CoverageCount;

    #[test]
    fn dash_token_is_never_evaluated_not_zero() {
        let never = BranchTaken::from_token("-");
        let zero = BranchTaken::from_token("0");
        assert!(never.is_never_evaluated());
        assert!(!zero.is_never_evaluated());
        assert_ne!(never, zero);
        assert!(!never.contributes_hit());
        assert!(!zero.contributes_hit());
    }

    #[test]
    fn never_evaluated_merge_rules() {
        let never = BranchTaken::NeverEvaluated;
        let taken = BranchTaken::evaluated(CoverageCount::from_lexeme("2"));

        assert_eq!(never.merge_with(&taken).expect("replace"), taken.clone());
        assert_eq!(taken.merge_with(&never).expect("identity"), taken.clone());
        assert_eq!(
            never.merge_with(&never).expect("never+never"),
            BranchTaken::NeverEvaluated
        );
    }

    #[test]
    fn evaluated_merge_adds_counts_in_order() {
        let left = BranchTaken::evaluated(CoverageCount::from_lexeme("2"));
        let right = BranchTaken::evaluated(CoverageCount::from_lexeme("3"));
        let merged = left.merge_with(&right).expect("add");
        assert_eq!(
            merged
                .as_evaluated()
                .map(CoverageCount::lexeme)
                .map(|b| b.as_bytes()),
            Some(b"5".as_slice())
        );
        assert!(merged.contributes_hit());
    }
}
