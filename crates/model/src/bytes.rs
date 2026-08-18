//! Explicit byte-preserving string identity for LCOV model fields.
//!
//! `ByteString` stores every input byte and never requires UTF-8. Display
//! conversion is explicit and must not alter stored identity.

use std::borrow::Cow;
use std::fmt;
use std::ops::Deref;

/// Opaque byte sequence used for paths, versions, test names, checksums,
/// aliases, expressions, and similar LCOV identity fields.
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Default)]
pub struct ByteString {
    bytes: Vec<u8>,
}

impl ByteString {
    /// Create a byte string from an owned byte vector.
    #[must_use]
    pub fn new(bytes: Vec<u8>) -> Self {
        Self { bytes }
    }

    /// Create a byte string from any byte slice.
    #[must_use]
    pub fn from_slice(bytes: &[u8]) -> Self {
        Self {
            bytes: bytes.to_vec(),
        }
    }

    /// Borrow the raw stored bytes.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Consume the value and return the owned bytes.
    #[must_use]
    pub fn into_bytes(self) -> Vec<u8> {
        self.bytes
    }

    /// Return `true` when every byte is valid UTF-8.
    #[must_use]
    pub fn is_utf8(&self) -> bool {
        std::str::from_utf8(&self.bytes).is_ok()
    }

    /// Borrow as `&str` when the bytes are valid UTF-8.
    ///
    /// This is an explicit display/view conversion and does not alter the
    /// stored identity.
    #[must_use]
    pub fn as_utf8(&self) -> Option<&str> {
        std::str::from_utf8(&self.bytes).ok()
    }

    /// Lossy UTF-8 display view. The stored bytes are unchanged.
    #[must_use]
    pub fn to_string_lossy(&self) -> Cow<'_, str> {
        String::from_utf8_lossy(&self.bytes)
    }
}

impl Deref for ByteString {
    type Target = [u8];

    fn deref(&self) -> &Self::Target {
        &self.bytes
    }
}

impl AsRef<[u8]> for ByteString {
    fn as_ref(&self) -> &[u8] {
        &self.bytes
    }
}

impl From<Vec<u8>> for ByteString {
    fn from(bytes: Vec<u8>) -> Self {
        Self::new(bytes)
    }
}

impl From<&[u8]> for ByteString {
    fn from(bytes: &[u8]) -> Self {
        Self::from_slice(bytes)
    }
}

impl From<&str> for ByteString {
    fn from(value: &str) -> Self {
        Self::from_slice(value.as_bytes())
    }
}

impl From<String> for ByteString {
    fn from(value: String) -> Self {
        Self::new(value.into_bytes())
    }
}

impl fmt::Debug for ByteString {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "ByteString(")?;
        for &byte in &self.bytes {
            write!(f, "\\x{byte:02x}")?;
        }
        write!(f, ")")
    }
}

impl fmt::Display for ByteString {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Explicit lossy display only. Stored identity remains the raw bytes.
        f.write_str(&self.to_string_lossy())
    }
}

#[cfg(test)]
mod tests {
    use super::ByteString;

    #[test]
    fn preserves_arbitrary_bytes_including_invalid_utf8() {
        let raw = b"path/\x80\xff\x00name".to_vec();
        let value = ByteString::new(raw.clone());
        assert_eq!(value.as_bytes(), raw.as_slice());
        assert!(!value.is_utf8());
        assert!(value.as_utf8().is_none());
        assert_eq!(value.to_string_lossy(), "path/\u{fffd}\u{fffd}\u{0}name");
        assert_eq!(value.as_bytes(), raw.as_slice());
    }

    #[test]
    fn equality_is_byte_exact() {
        let left = ByteString::from("Foo");
        let right = ByteString::from("foo");
        assert_ne!(left, right);
        assert_eq!(ByteString::from(b"a\0b".as_slice()), ByteString::from(b"a\0b".as_slice()));
    }

    #[test]
    fn empty_bytes_are_representable() {
        let empty = ByteString::new(Vec::new());
        assert!(empty.as_bytes().is_empty());
        assert!(empty.is_utf8());
        assert_eq!(empty.as_utf8(), Some(""));
    }

    #[test]
    fn display_and_debug_do_not_mutate_stored_bytes() {
        let value = ByteString::from_slice(b"a\xffb");
        let _ = format!("{value}");
        let _ = format!("{value:?}");
        assert_eq!(value.as_bytes(), b"a\xffb");
    }
}
