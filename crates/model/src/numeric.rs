//! Numeric atom and coverage-count primitives.
//!
//! CORE-001 stores the raw accepted lexeme plus an Oracle-visible tagged
//! projection. Full Perl arithmetic/promotion is deferred to later M1 work
//! (`M1-MD-004` / algebra lanes); this module refuses silent saturation,
//! wrapping, or `f64`-first coercion.

use crate::bytes::ByteString;
use std::cmp::Ordering;
use std::fmt;

fn ordering_from_i8(value: i8) -> Ordering {
    value.cmp(&0)
}

/// Oracle-visible numeric class derived from an accepted lexeme.
///
/// This is a tagged projection used for later compare/format decisions. It is
/// not a claim that the value was coerced through binary floating point.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NumericClass {
    /// Finite numeric spelling (including signed zero and scientific forms).
    Finite,
    /// IEEE-style NaN spelling such as `NaN`.
    Nan,
    /// Positive infinity spelling such as `Inf` / `+Infinity`.
    PositiveInfinity,
    /// Negative infinity spelling such as `-Inf`.
    NegativeInfinity,
    /// Lexeme rejected by `looks_like_number`-style acceptance.
    NonNumeric,
}

/// Whether Perl treated the scalar as integer-like or floating-like after
/// numeric projection stages observed by the TF-030 registry.
///
/// CORE-001 records the distinction without inventing a full SV emulator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NumericKind {
    /// Integer-like projection (`IOK` without requiring float storage).
    IntegerLike,
    /// Floating-like projection (`NOK` / non-integral spelling).
    FloatingLike,
    /// Non-numeric or non-finite class where integer/float kind does not apply.
    NotApplicable,
}

/// A parsed numeric atom that retains the original accepted byte lexeme.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NumericAtom {
    lexeme: ByteString,
    class: NumericClass,
    kind: NumericKind,
    signed_zero: bool,
}

impl NumericAtom {
    /// Construct an atom from an explicit lexeme and Oracle-visible tags.
    #[must_use]
    pub fn new(
        lexeme: impl Into<ByteString>,
        class: NumericClass,
        kind: NumericKind,
        signed_zero: bool,
    ) -> Self {
        Self {
            lexeme: lexeme.into(),
            class,
            kind,
            signed_zero,
        }
    }

    /// Classify a general-count lexeme without arithmetic or `f64` coercion.
    ///
    /// Classification is ASCII/byte oriented and preserves the original lexeme
    /// bytes exactly. Non-UTF-8 lexemes are retained as [`NumericClass::NonNumeric`].
    #[must_use]
    pub fn from_lexeme(lexeme: impl Into<ByteString>) -> Self {
        let lexeme = lexeme.into();
        let Some(text) = lexeme.as_utf8() else {
            return Self::new(lexeme, NumericClass::NonNumeric, NumericKind::NotApplicable, false);
        };

        let trimmed = text.trim();
        let lower = trimmed.to_ascii_lowercase();
        if lower == "nan" {
            return Self::new(lexeme, NumericClass::Nan, NumericKind::NotApplicable, false);
        }
        if matches!(lower.as_str(), "inf" | "+inf" | "infinity" | "+infinity") {
            return Self::new(
                lexeme,
                NumericClass::PositiveInfinity,
                NumericKind::NotApplicable,
                false,
            );
        }
        if matches!(lower.as_str(), "-inf" | "-infinity") {
            return Self::new(
                lexeme,
                NumericClass::NegativeInfinity,
                NumericKind::NotApplicable,
                false,
            );
        }

        if !looks_like_number_ascii(trimmed) {
            return Self::new(lexeme, NumericClass::NonNumeric, NumericKind::NotApplicable, false);
        }

        let signed_zero = is_signed_zero_lexeme(trimmed);
        let kind = if is_integer_like_lexeme(trimmed) {
            NumericKind::IntegerLike
        } else {
            NumericKind::FloatingLike
        };
        Self::new(lexeme, NumericClass::Finite, kind, signed_zero)
    }

    /// Semantic zero with lexeme `0`.
    #[must_use]
    pub fn zero() -> Self {
        Self::new("0", NumericClass::Finite, NumericKind::IntegerLike, false)
    }

    /// Borrow the original accepted lexeme bytes.
    #[must_use]
    pub fn lexeme(&self) -> &ByteString {
        &self.lexeme
    }

    /// Oracle-visible numeric class.
    #[must_use]
    pub fn class(&self) -> NumericClass {
        self.class
    }

    /// Integer-like / floating-like projection tag.
    #[must_use]
    pub fn kind(&self) -> NumericKind {
        self.kind
    }

    /// Whether the lexeme is a signed-zero spelling (`-0`, `-0.0`, ...).
    #[must_use]
    pub fn is_signed_zero(&self) -> bool {
        self.signed_zero
    }

    /// Return `true` when the class is finite.
    #[must_use]
    pub fn is_finite(&self) -> bool {
        self.class == NumericClass::Finite
    }

    /// Return `true` when the class is non-numeric.
    #[must_use]
    pub fn is_non_numeric(&self) -> bool {
        self.class == NumericClass::NonNumeric
    }
}

impl fmt::Display for NumericAtom {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.lexeme.to_string_lossy())
    }
}

/// Outcome of [`CoverageCount::validate`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CountValidation {
    /// Count is usable as-is.
    Valid,
    /// Non-numeric or negative count that becomes semantic zero under ignore.
    CoerceToZero,
    /// Count exceeds a configured excessive threshold but remains semantic.
    Excessive,
}

/// Coverage counter retaining raw lexeme state and semantic count meaning.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct CoverageCount {
    atom: NumericAtom,
    /// Semantic zero after ignored-error coercion of invalid/negative counts.
    coerced_zero: bool,
}

impl CoverageCount {
    /// Wrap an existing numeric atom as a coverage count.
    #[must_use]
    pub fn from_atom(atom: NumericAtom) -> Self {
        Self {
            atom,
            coerced_zero: false,
        }
    }

    /// Parse a coverage count from a raw lexeme without `f64` coercion.
    #[must_use]
    pub fn from_lexeme(lexeme: impl Into<ByteString>) -> Self {
        Self::from_atom(NumericAtom::from_lexeme(lexeme))
    }

    /// Semantic zero count with lexeme `0`.
    #[must_use]
    pub fn zero() -> Self {
        Self::from_atom(NumericAtom::zero())
    }

    /// Borrow the retained numeric atom (lexeme + tags).
    #[must_use]
    pub fn atom(&self) -> &NumericAtom {
        &self.atom
    }

    /// Borrow the original lexeme bytes.
    #[must_use]
    pub fn lexeme(&self) -> &ByteString {
        self.atom.lexeme()
    }

    /// Return `true` when ignored-error coercion forced semantic zero.
    #[must_use]
    pub fn is_coerced_zero(&self) -> bool {
        self.coerced_zero
    }

    /// Validate against Oracle count rules.
    ///
    /// Invalid/negative counts report [`CountValidation::CoerceToZero`]. When
    /// `excessive_threshold` is set and the finite lexeme compares greater as a
    /// decimal integer/float spelling, report [`CountValidation::Excessive`]
    /// without discarding the count.
    #[must_use]
    pub fn validate(&self, excessive_threshold: Option<&str>) -> CountValidation {
        if self.coerced_zero {
            return CountValidation::Valid;
        }
        match self.atom.class() {
            NumericClass::NonNumeric => CountValidation::CoerceToZero,
            NumericClass::Nan | NumericClass::PositiveInfinity | NumericClass::NegativeInfinity => {
                // Non-finite values are retained; threshold comparison is only
                // meaningful for finite spellings in CORE-001.
                CountValidation::Valid
            }
            NumericClass::Finite => {
                if self.is_negative_lexeme() {
                    CountValidation::CoerceToZero
                } else if let Some(threshold) = excessive_threshold {
                    if compare_decimal_lexemes(
                        self.atom.lexeme().as_utf8().unwrap_or(""),
                        threshold,
                    ) == Some(ordering_from_i8(1))
                    {
                        CountValidation::Excessive
                    } else {
                        CountValidation::Valid
                    }
                } else {
                    CountValidation::Valid
                }
            }
        }
    }

    /// Apply ignored-error coercion: invalid/negative become semantic zero
    /// while retaining the original lexeme on the atom for provenance.
    #[must_use]
    pub fn coerce_invalid_to_zero(mut self) -> Self {
        match self.validate(None) {
            CountValidation::CoerceToZero => {
                self.coerced_zero = true;
                self
            }
            CountValidation::Valid | CountValidation::Excessive => self,
        }
    }

    /// Return `true` when the semantic count is zero (including signed zero and
    /// coerced zero). Non-numeric atoms are not treated as zero until coerced.
    #[must_use]
    pub fn is_zero(&self) -> bool {
        if self.coerced_zero {
            return true;
        }
        match self.atom.class() {
            NumericClass::Finite => {
                self.atom.is_signed_zero()
                    || self
                        .atom
                        .lexeme()
                        .as_utf8()
                        .is_some_and(|text| is_zero_lexeme(text.trim()))
            }
            NumericClass::Nan
            | NumericClass::PositiveInfinity
            | NumericClass::NegativeInfinity
            | NumericClass::NonNumeric => false,
        }
    }

    /// Return `true` when the semantic count is strictly positive.
    #[must_use]
    pub fn is_positive(&self) -> bool {
        if self.coerced_zero || !self.atom.is_finite() {
            return false;
        }
        !self.is_zero() && !self.is_negative_lexeme()
    }

    /// Compare this count to an excessive-count threshold lexeme.
    ///
    /// Returns `None` when either side is not a comparable finite spelling.
    /// This does not coerce through `f64`.
    #[must_use]
    pub fn compare_threshold(&self, threshold: &str) -> Option<Ordering> {
        if self.coerced_zero || !self.atom.is_finite() {
            return None;
        }
        let left = self.atom.lexeme().as_utf8()?;
        compare_decimal_lexemes(left, threshold)
    }

    /// Add two coverage counts while preserving operand order.
    ///
    /// CORE-001 implements exact decimal addition for finite integer-like and
    /// simple decimal lexemes. Non-finite or non-numeric operands, and any case
    /// that would require inventing Perl promotion, return [`AddError`]. The
    /// original lexemes remain available on both operands.
    pub fn add(&self, right: &Self) -> Result<Self, AddError> {
        if self.coerced_zero && right.coerced_zero {
            return Ok(Self::zero());
        }
        if self.coerced_zero {
            return Ok(right.clone());
        }
        if right.coerced_zero {
            return Ok(self.clone());
        }
        if !self.atom.is_finite() || !right.atom.is_finite() {
            return Err(AddError::UnsupportedOperandClass);
        }
        let left_text = self
            .atom
            .lexeme()
            .as_utf8()
            .ok_or(AddError::UnsupportedOperandClass)?;
        let right_text = right
            .atom
            .lexeme()
            .as_utf8()
            .ok_or(AddError::UnsupportedOperandClass)?;

        let sum = add_decimal_lexemes(left_text.trim(), right_text.trim())
            .ok_or(AddError::UnsupportedOperandClass)?;
        Ok(Self::from_lexeme(sum))
    }

    fn is_negative_lexeme(&self) -> bool {
        if self.coerced_zero || !self.atom.is_finite() || self.atom.is_signed_zero() {
            return false;
        }
        self.atom
            .lexeme()
            .as_utf8()
            .is_some_and(|text| text.trim().starts_with('-'))
    }
}

/// Error returned when [`CoverageCount::add`] cannot proceed without inventing
/// Perl numeric promotion behavior.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AddError {
    /// One or both operands are non-finite, non-numeric, or use a spelling that
    /// CORE-001 deliberately does not evaluate yet.
    UnsupportedOperandClass,
}

impl fmt::Display for AddError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnsupportedOperandClass => {
                f.write_str("coverage count add requires supported finite lexemes")
            }
        }
    }
}

impl std::error::Error for AddError {}

fn looks_like_number_ascii(text: &str) -> bool {
    // Conservative ASCII approximation of Perl's looks_like_number for the
    // spellings retained by the TF-030 matrix. Non-matching lexemes stay
    // NonNumeric with their raw bytes preserved.
    let bytes = text.as_bytes();
    if bytes.is_empty() {
        return false;
    }
    let mut i = 0usize;
    if bytes[i] == b'+' || bytes[i] == b'-' {
        i += 1;
        if i == bytes.len() {
            return false;
        }
    }
    let start = i;
    let mut saw_digit = false;
    let mut saw_dot = false;
    while i < bytes.len() {
        match bytes[i] {
            b'0'..=b'9' => {
                saw_digit = true;
                i += 1;
            }
            b'.' if !saw_dot => {
                saw_dot = true;
                i += 1;
            }
            b'e' | b'E' => break,
            _ => return false,
        }
    }
    if !saw_digit && !(saw_dot && start < i) {
        // Require at least one digit somewhere in the mantissa (".5" / "1.").
        if !(saw_dot && bytes[start..i].iter().any(u8::is_ascii_digit)) {
            return false;
        }
    }
    if i < bytes.len() {
        if bytes[i] != b'e' && bytes[i] != b'E' {
            return false;
        }
        i += 1;
        if i < bytes.len() && (bytes[i] == b'+' || bytes[i] == b'-') {
            i += 1;
        }
        if i == bytes.len() {
            return false;
        }
        let exp_start = i;
        while i < bytes.len() && bytes[i].is_ascii_digit() {
            i += 1;
        }
        if i == exp_start || i != bytes.len() {
            return false;
        }
        return saw_digit || bytes[start..exp_start - 1].iter().any(u8::is_ascii_digit);
    }
    saw_digit || bytes[start..].iter().any(u8::is_ascii_digit)
}

fn is_integer_like_lexeme(text: &str) -> bool {
    let trimmed = text.trim();
    let body = trimmed
        .strip_prefix('+')
        .or_else(|| trimmed.strip_prefix('-'))
        .unwrap_or(trimmed);
    !body.is_empty() && body.bytes().all(|b| b.is_ascii_digit())
}

fn is_signed_zero_lexeme(text: &str) -> bool {
    let trimmed = text.trim();
    trimmed.starts_with('-') && is_zero_lexeme(trimmed)
}

fn is_zero_lexeme(text: &str) -> bool {
    let trimmed = text.trim();
    let body = trimmed
        .strip_prefix('+')
        .or_else(|| trimmed.strip_prefix('-'))
        .unwrap_or(trimmed);
    if body.is_empty() {
        return false;
    }
    // Finite zero spellings: 0, 0.0, 0e0, .0, 0., etc. without non-zero digits.
    let mut saw_digit = false;
    let mut i = 0usize;
    let bytes = body.as_bytes();
    while i < bytes.len() {
        match bytes[i] {
            b'0' => {
                saw_digit = true;
                i += 1;
            }
            b'.' => i += 1,
            b'e' | b'E' => {
                i += 1;
                if i < bytes.len() && (bytes[i] == b'+' || bytes[i] == b'-') {
                    i += 1;
                }
                if i == bytes.len() {
                    return false;
                }
                while i < bytes.len() {
                    if !bytes[i].is_ascii_digit() {
                        return false;
                    }
                    i += 1;
                }
                return saw_digit || body.contains('0');
            }
            _ => return false,
        }
    }
    saw_digit || body.contains('0')
}

fn compare_decimal_lexemes(left: &str, right: &str) -> Option<Ordering> {
    let left_norm = normalize_decimal(left.trim())?;
    let right_norm = normalize_decimal(right.trim())?;
    Some(compare_normalized(&left_norm, &right_norm))
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct NormalizedDecimal {
    negative: bool,
    digits: String,
    scale: usize,
}

fn normalize_decimal(text: &str) -> Option<NormalizedDecimal> {
    if !looks_like_number_ascii(text) {
        return None;
    }
    let lower = text.to_ascii_lowercase();
    if matches!(
        lower.as_str(),
        "nan" | "inf" | "+inf" | "infinity" | "+infinity" | "-inf" | "-infinity"
    ) {
        return None;
    }

    let mut rest = text;
    let mut negative = false;
    if let Some(stripped) = rest.strip_prefix('+') {
        rest = stripped;
    } else if let Some(stripped) = rest.strip_prefix('-') {
        negative = true;
        rest = stripped;
    }

    let (mantissa, exponent) = match rest.find(['e', 'E']) {
        Some(index) => {
            let exp: i32 = rest[index + 1..].parse().ok()?;
            (&rest[..index], exp)
        }
        None => (rest, 0),
    };

    let (int_part, frac_part) = match mantissa.split_once('.') {
        Some((int_part, frac_part)) => (int_part, frac_part),
        None => (mantissa, ""),
    };
    if int_part.is_empty() && frac_part.is_empty() {
        return None;
    }
    if !int_part.is_empty() && !int_part.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    if !frac_part.is_empty() && !frac_part.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }

    let mut digits = String::new();
    digits.push_str(if int_part.is_empty() { "0" } else { int_part });
    digits.push_str(frac_part);
    // value = digits * 10^{-frac_len} * 10^{exponent}
    let mut scale = frac_part.len() as i32 - exponent;
    if scale < 0 {
        for _ in 0..(-scale) {
            digits.push('0');
        }
        scale = 0;
    }
    // Strip leading zeros but keep one digit for zero values.
    let trimmed = digits.trim_start_matches('0');
    let digits = if trimmed.is_empty() {
        "0".to_owned()
    } else {
        trimmed.to_owned()
    };
    if digits == "0" {
        // Canonical zero is non-negative for comparisons.
        negative = false;
        scale = 0;
    }
    Some(NormalizedDecimal {
        negative,
        digits,
        scale: scale as usize,
    })
}

fn compare_normalized(left: &NormalizedDecimal, right: &NormalizedDecimal) -> Ordering {
    if left.negative != right.negative {
        return if left.negative {
            ordering_from_i8(-1)
        } else {
            ordering_from_i8(1)
        };
    }
    let max_scale = left.scale.max(right.scale);
    let left_digits = pad_fraction(&left.digits, left.scale, max_scale);
    let right_digits = pad_fraction(&right.digits, right.scale, max_scale);
    let cmp = if left_digits.len() == right_digits.len() {
        left_digits.cmp(&right_digits)
    } else {
        left_digits.len().cmp(&right_digits.len())
    };
    if left.negative {
        cmp.reverse()
    } else {
        cmp
    }
}

fn pad_fraction(digits: &str, scale: usize, max_scale: usize) -> String {
    let mut out = digits.to_owned();
    for _ in 0..(max_scale - scale) {
        out.push('0');
    }
    out
}

fn add_decimal_lexemes(left: &str, right: &str) -> Option<String> {
    let left_norm = normalize_decimal(left)?;
    let right_norm = normalize_decimal(right)?;
    let max_scale = left_norm.scale.max(right_norm.scale);
    let left_digits = pad_fraction(&left_norm.digits, left_norm.scale, max_scale);
    let right_digits = pad_fraction(&right_norm.digits, right_norm.scale, max_scale);

    let (negative, digits) = if left_norm.negative == right_norm.negative {
        (
            left_norm.negative,
            add_digit_strings(&left_digits, &right_digits),
        )
    } else {
        match compare_digit_strings(&left_digits, &right_digits) {
            ordering if ordering == ordering_from_i8(1) => (
                left_norm.negative,
                sub_digit_strings(&left_digits, &right_digits),
            ),
            ordering if ordering == ordering_from_i8(-1) => (
                right_norm.negative,
                sub_digit_strings(&right_digits, &left_digits),
            ),
            _ => (false, "0".to_owned()),
        }
    };

    Some(format_normalized(negative, &digits, max_scale))
}

fn add_digit_strings(left: &str, right: &str) -> String {
    let left = left.as_bytes();
    let right = right.as_bytes();
    let mut out = Vec::new();
    let mut carry = 0u8;
    let mut i = left.len();
    let mut j = right.len();
    while i > 0 || j > 0 || carry > 0 {
        let mut sum = carry;
        if i > 0 {
            i -= 1;
            sum += left[i] - b'0';
        }
        if j > 0 {
            j -= 1;
            sum += right[j] - b'0';
        }
        out.push(b'0' + (sum % 10));
        carry = sum / 10;
    }
    out.reverse();
    String::from_utf8(out).expect("digits are ascii")
}

fn sub_digit_strings(left: &str, right: &str) -> String {
    // Precondition: left >= right as unsigned digit strings.
    let left = left.as_bytes();
    let right = right.as_bytes();
    let mut out = Vec::new();
    let mut borrow = 0i16;
    let mut i = left.len();
    let mut j = right.len();
    while i > 0 {
        i -= 1;
        let mut digit = i16::from(left[i] - b'0') - i16::from(borrow);
        let sub = if j > 0 {
            j -= 1;
            i16::from(right[j] - b'0')
        } else {
            0
        };
        if digit < sub {
            digit += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        out.push(b'0' + u8::try_from(digit - sub).expect("digit"));
    }
    while out.last() == Some(&b'0') && out.len() > 1 {
        out.pop();
    }
    out.reverse();
    String::from_utf8(out).expect("digits are ascii")
}

fn compare_digit_strings(left: &str, right: &str) -> Ordering {
    if left.len() == right.len() {
        left.cmp(right)
    } else {
        left.len().cmp(&right.len())
    }
}

fn format_normalized(negative: bool, digits: &str, scale: usize) -> String {
    let digits = digits.trim_start_matches('0');
    let digits = if digits.is_empty() { "0" } else { digits };
    if digits == "0" {
        return "0".to_owned();
    }
    let mut body = if scale == 0 {
        digits.to_owned()
    } else if digits.len() <= scale {
        let mut frac = format!("0.{}", "0".repeat(scale - digits.len()));
        frac.push_str(digits);
        // Trim trailing zeros after decimal, but keep at least one digit.
        while frac.ends_with('0') && frac.contains('.') {
            frac.pop();
        }
        if frac.ends_with('.') {
            frac.pop();
        }
        frac
    } else {
        let split = digits.len() - scale;
        let mut body = format!("{}.{}", &digits[..split], &digits[split..]);
        while body.ends_with('0') {
            body.pop();
        }
        if body.ends_with('.') {
            body.pop();
        }
        body
    };
    if negative && body != "0" {
        body.insert(0, '-');
    }
    body
}

#[cfg(test)]
mod tests {
    use super::{
        ordering_from_i8, AddError, CountValidation, CoverageCount, NumericAtom, NumericClass,
        NumericKind,
    };
    use crate::bytes::ByteString;

    #[test]
    fn numeric_atom_preserves_raw_lexeme_bytes() {
        let raw = ByteString::from_slice(b"1e3\xff");
        let atom = NumericAtom::from_lexeme(raw.clone());
        assert_eq!(atom.lexeme(), &raw);
        assert_eq!(atom.class(), NumericClass::NonNumeric);
        assert_eq!(atom.kind(), NumericKind::NotApplicable);
    }

    #[test]
    fn classifies_finite_nan_inf_and_nonnumeric_without_f64() {
        let finite = NumericAtom::from_lexeme("9007199254740993");
        assert_eq!(finite.class(), NumericClass::Finite);
        assert_eq!(finite.kind(), NumericKind::IntegerLike);
        assert_eq!(finite.lexeme().as_bytes(), b"9007199254740993");

        let floatish = NumericAtom::from_lexeme("1.5e+20");
        assert_eq!(floatish.class(), NumericClass::Finite);
        assert_eq!(floatish.kind(), NumericKind::FloatingLike);

        assert_eq!(NumericAtom::from_lexeme("NaN").class(), NumericClass::Nan);
        assert_eq!(
            NumericAtom::from_lexeme("Inf").class(),
            NumericClass::PositiveInfinity
        );
        assert_eq!(
            NumericAtom::from_lexeme("-Infinity").class(),
            NumericClass::NegativeInfinity
        );
        assert_eq!(
            NumericAtom::from_lexeme("1.a0e+19").class(),
            NumericClass::NonNumeric
        );
    }

    #[test]
    fn signed_zero_is_tagged_and_counts_as_zero() {
        let atom = NumericAtom::from_lexeme("-0");
        assert!(atom.is_signed_zero());
        let count = CoverageCount::from_atom(atom);
        assert!(count.is_zero());
        assert!(!count.is_positive());
    }

    #[test]
    fn validate_coerces_invalid_and_negative_but_keeps_excessive() {
        let nonnumeric = CoverageCount::from_lexeme("nope");
        assert_eq!(nonnumeric.validate(None), CountValidation::CoerceToZero);
        let coerced = nonnumeric.coerce_invalid_to_zero();
        assert!(coerced.is_coerced_zero());
        assert!(coerced.is_zero());
        assert_eq!(coerced.lexeme().as_bytes(), b"nope");

        let negative = CoverageCount::from_lexeme("-3");
        assert_eq!(negative.validate(None), CountValidation::CoerceToZero);

        let large = CoverageCount::from_lexeme("1000");
        assert_eq!(
            large.validate(Some("100")),
            CountValidation::Excessive
        );
        assert!(large.is_positive());
    }

    #[test]
    fn add_preserves_large_integer_precision() {
        let left = CoverageCount::from_lexeme("9007199254740992");
        let right = CoverageCount::from_lexeme("1");
        let sum = left.add(&right).expect("supported");
        assert_eq!(sum.lexeme().as_bytes(), b"9007199254740993");
        assert!(sum.is_positive());
    }

    #[test]
    fn add_rejects_non_finite_without_inventing_promotion() {
        let left = CoverageCount::from_lexeme("1");
        let right = CoverageCount::from_lexeme("Inf");
        assert_eq!(left.add(&right), Err(AddError::UnsupportedOperandClass));
    }

    #[test]
    fn compare_threshold_uses_decimal_lexeme_order() {
        let count = CoverageCount::from_lexeme("1.0e+3");
        assert_eq!(count.compare_threshold("999"), Some(ordering_from_i8(1)));
        assert_eq!(count.compare_threshold("1000"), Some(ordering_from_i8(0)));
    }

    #[test]
    fn leading_whitespace_lexeme_bytes_are_preserved() {
        let atom = NumericAtom::from_lexeme(" 1");
        assert_eq!(atom.lexeme().as_bytes(), b" 1");
        assert_eq!(atom.class(), NumericClass::Finite);
        assert!(CoverageCount::from_atom(atom).is_positive());
    }
}
