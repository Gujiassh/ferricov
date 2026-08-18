//! Location and map keys for coverage stores.
//!
//! `LineKey` is intentionally not a plain `u64`. Parser-facing construction
//! must retain Oracle zero and ignored-error states; a public canonical path
//! may still require positive values.

use crate::bytes::ByteString;
use crate::numeric::{NumericAtom, NumericClass, NumericKind};

/// Line / location map key that preserves retained Oracle numeric states.
///
/// The key wraps a [`NumericAtom`] so zero, negative, non-numeric, and other
/// ignored-error spellings remain representable without coercing through a
/// fixed-width integer.
///
/// Map ordering is by retained lexeme bytes, not by numeric magnitude. Numeric
/// sort behavior for writer output remains a later CORE concern.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct LineKey {
    atom: NumericAtom,
}

impl PartialOrd for LineKey {
    fn partial_cmp(&self, other: &Self) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for LineKey {
    fn cmp(&self, other: &Self) -> core::cmp::Ordering {
        self.atom.lexeme().cmp(other.atom.lexeme())
    }
}

impl LineKey {
    /// Construct a key from an explicit numeric atom.
    #[must_use]
    pub fn from_atom(atom: NumericAtom) -> Self {
        Self { atom }
    }

    /// Parser-facing construction: retain every accepted lexeme state.
    ///
    /// This path MUST represent Oracle-retained zeros and ignored-error states.
    /// It does not require the value to be a positive canonical line number.
    #[must_use]
    pub fn from_lexeme(lexeme: impl Into<ByteString>) -> Self {
        Self::from_atom(NumericAtom::from_lexeme(lexeme))
    }

    /// Canonical constructor for positive line numbers.
    ///
    /// Returns `None` when the lexeme is not a finite positive integer-like
    /// spelling. Use [`LineKey::from_lexeme`] for parser-retained states.
    #[must_use]
    pub fn try_canonical_positive(lexeme: impl Into<ByteString>) -> Option<Self> {
        let atom = NumericAtom::from_lexeme(lexeme);
        if atom.class() != NumericClass::Finite || atom.kind() != NumericKind::IntegerLike {
            return None;
        }
        let text = atom.lexeme().as_utf8()?.trim();
        if text.is_empty() || text.starts_with('-') || text.starts_with('+') {
            return None;
        }
        if !text.bytes().all(|b| b.is_ascii_digit()) {
            return None;
        }
        if text.bytes().all(|b| b == b'0') {
            return None;
        }
        Some(Self::from_atom(atom))
    }

    /// Borrow the retained numeric atom.
    #[must_use]
    pub fn atom(&self) -> &NumericAtom {
        &self.atom
    }

    /// Borrow the original key lexeme bytes.
    #[must_use]
    pub fn lexeme(&self) -> &ByteString {
        self.atom.lexeme()
    }

    /// Return `true` when the retained key is a semantic zero spelling.
    #[must_use]
    pub fn is_zero(&self) -> bool {
        if self.atom.class() != NumericClass::Finite {
            return false;
        }
        if self.atom.is_signed_zero() {
            return true;
        }
        let Some(text) = self.atom.lexeme().as_utf8() else {
            return false;
        };
        let trimmed = text.trim();
        !trimmed.is_empty()
            && trimmed.bytes().all(|b| b == b'0')
    }
}

#[cfg(test)]
mod tests {
    use super::LineKey;
    use crate::numeric::{NumericClass, NumericKind};

    #[test]
    fn line_key_represents_zero_and_retained_states() {
        let zero = LineKey::from_lexeme("0");
        assert!(zero.is_zero());
        assert_eq!(zero.lexeme().as_bytes(), b"0");
        assert_eq!(zero.atom().class(), NumericClass::Finite);

        let signed_zero = LineKey::from_lexeme("-0");
        assert!(signed_zero.is_zero());
        assert_eq!(signed_zero.lexeme().as_bytes(), b"-0");

        let ignored = LineKey::from_lexeme("nope");
        assert_eq!(ignored.atom().class(), NumericClass::NonNumeric);
        assert_eq!(ignored.lexeme().as_bytes(), b"nope");
        assert!(!ignored.is_zero());
    }

    #[test]
    fn canonical_positive_rejects_zero_and_non_integer() {
        assert!(LineKey::try_canonical_positive("1").is_some());
        assert!(LineKey::try_canonical_positive("0").is_none());
        assert!(LineKey::try_canonical_positive("-1").is_none());
        assert!(LineKey::try_canonical_positive("1.5").is_none());
        assert!(LineKey::try_canonical_positive("x").is_none());

        let one = LineKey::try_canonical_positive("1").expect("canonical");
        assert_eq!(one.atom().kind(), NumericKind::IntegerLike);
    }
}
