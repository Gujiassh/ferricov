//! Source and testcase identity primitives.
//!
//! Lookup identity and writer display path are distinct concerns. The model
//! stores both; filesystem resolution stays outside this crate.

use crate::bytes::ByteString;

/// Lookup key used to decide whether two source records address one entry.
///
/// Case-sensitive lookup uses the configured path bytes directly. Case-
/// insensitive lookup uses an ASCII-folded key while preserving the chosen
/// display path on [`SourceIdentity`].
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SourceLookupKey {
    bytes: ByteString,
}

impl SourceLookupKey {
    /// Create a lookup key from exact path bytes (case-sensitive mode).
    #[must_use]
    pub fn from_path_bytes(path: impl Into<ByteString>) -> Self {
        Self { bytes: path.into() }
    }

    /// Create an ASCII case-insensitive lookup key by folding `A-Z` to `a-z`.
    ///
    /// Unicode case folding is intentionally not applied here; coverage-model
    /// prohibits it unless an Oracle case proves Perl equivalence.
    #[must_use]
    pub fn ascii_case_insensitive(path: impl Into<ByteString>) -> Self {
        let path = path.into();
        let folded = path
            .as_bytes()
            .iter()
            .map(|byte| byte.to_ascii_lowercase())
            .collect::<Vec<u8>>();
        Self {
            bytes: ByteString::new(folded),
        }
    }

    /// Borrow the lookup key bytes.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        self.bytes.as_bytes()
    }

    /// Borrow the lookup key as a [`ByteString`].
    #[must_use]
    pub fn as_byte_string(&self) -> &ByteString {
        &self.bytes
    }
}

impl From<ByteString> for SourceLookupKey {
    fn from(bytes: ByteString) -> Self {
        Self::from_path_bytes(bytes)
    }
}

/// Source identity distinguishing lookup key from display path.
///
/// Optional diagnostic/runtime path bytes may be retained for parser
/// provenance without becoming a second semantic lookup identity.
#[derive(Debug, Clone)]
pub struct SourceIdentity {
    lookup_key: SourceLookupKey,
    display_path: ByteString,
    diagnostic_path: Option<ByteString>,
}

impl PartialEq for SourceIdentity {
    fn eq(&self, other: &Self) -> bool {
        // Semantic identity excludes diagnostic/runtime provenance.
        self.lookup_key == other.lookup_key && self.display_path == other.display_path
    }
}

impl Eq for SourceIdentity {}

impl std::hash::Hash for SourceIdentity {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.lookup_key.hash(state);
        self.display_path.hash(state);
    }
}

impl SourceIdentity {
    /// Construct a source identity from an explicit lookup key and display path.
    #[must_use]
    pub fn new(lookup_key: SourceLookupKey, display_path: impl Into<ByteString>) -> Self {
        Self {
            lookup_key,
            display_path: display_path.into(),
            diagnostic_path: None,
        }
    }

    /// Construct a case-sensitive identity where lookup bytes equal display bytes.
    #[must_use]
    pub fn from_display_path(display_path: impl Into<ByteString>) -> Self {
        let display_path = display_path.into();
        Self {
            lookup_key: SourceLookupKey::from_path_bytes(display_path.clone()),
            display_path,
            diagnostic_path: None,
        }
    }

    /// Construct an ASCII case-insensitive identity while preserving display bytes.
    #[must_use]
    pub fn ascii_case_insensitive(display_path: impl Into<ByteString>) -> Self {
        let display_path = display_path.into();
        Self {
            lookup_key: SourceLookupKey::ascii_case_insensitive(display_path.clone()),
            display_path,
            diagnostic_path: None,
        }
    }

    /// Attach optional diagnostic/runtime path provenance.
    #[must_use]
    pub fn with_diagnostic_path(mut self, path: impl Into<ByteString>) -> Self {
        self.diagnostic_path = Some(path.into());
        self
    }

    /// Borrow the lookup key.
    #[must_use]
    pub fn lookup_key(&self) -> &SourceLookupKey {
        &self.lookup_key
    }

    /// Borrow the Oracle-selected display path bytes.
    #[must_use]
    pub fn display_path(&self) -> &ByteString {
        &self.display_path
    }

    /// Borrow optional diagnostic/runtime path bytes.
    #[must_use]
    pub fn diagnostic_path(&self) -> Option<&ByteString> {
        self.diagnostic_path.as_ref()
    }
}

/// Parser-selected testcase identity.
///
/// Includes the empty name and exact retained `,diff` suffix. Optional
/// unsanitized bytes are diagnostic provenance only and MUST NOT become a
/// second semantic identity.
#[derive(Debug, Clone)]
pub struct TestName {
    identity: ByteString,
    unsanitized: Option<ByteString>,
}

impl PartialEq for TestName {
    fn eq(&self, other: &Self) -> bool {
        self.identity == other.identity
    }
}

impl Eq for TestName {}

impl PartialOrd for TestName {
    fn partial_cmp(&self, other: &Self) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for TestName {
    fn cmp(&self, other: &Self) -> core::cmp::Ordering {
        self.identity.cmp(&other.identity)
    }
}

impl std::hash::Hash for TestName {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.identity.hash(state);
    }
}

impl TestName {
    /// Create a test name from the parser-selected byte identity.
    #[must_use]
    pub fn new(identity: impl Into<ByteString>) -> Self {
        Self {
            identity: identity.into(),
            unsanitized: None,
        }
    }

    /// Empty testcase name (`TN:` with no payload).
    #[must_use]
    pub fn empty() -> Self {
        Self::new(ByteString::new(Vec::new()))
    }

    /// Attach optional unsanitized diagnostic provenance bytes.
    #[must_use]
    pub fn with_unsanitized(mut self, bytes: impl Into<ByteString>) -> Self {
        self.unsanitized = Some(bytes.into());
        self
    }

    /// Borrow the semantic identity bytes.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        self.identity.as_bytes()
    }

    /// Borrow the semantic identity as a [`ByteString`].
    #[must_use]
    pub fn as_byte_string(&self) -> &ByteString {
        &self.identity
    }

    /// Borrow optional unsanitized diagnostic provenance.
    #[must_use]
    pub fn unsanitized(&self) -> Option<&ByteString> {
        self.unsanitized.as_ref()
    }

    /// Return `true` when the semantic identity is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.identity.as_bytes().is_empty()
    }
}

impl From<ByteString> for TestName {
    fn from(identity: ByteString) -> Self {
        Self::new(identity)
    }
}

impl From<&str> for TestName {
    fn from(identity: &str) -> Self {
        Self::new(identity)
    }
}

#[cfg(test)]
mod tests {
    use super::{SourceIdentity, SourceLookupKey, TestName};
    use crate::bytes::ByteString;

    #[test]
    fn source_identity_distinguishes_lookup_from_display() {
        let display = ByteString::from("Src/Foo.C");
        let identity = SourceIdentity::ascii_case_insensitive(display.clone());
        assert_eq!(identity.display_path(), &display);
        assert_eq!(identity.lookup_key().as_bytes(), b"src/foo.c");
        assert_ne!(
            identity.lookup_key().as_bytes(),
            identity.display_path().as_bytes()
        );
    }

    #[test]
    fn case_sensitive_lookup_keeps_exact_bytes() {
        let identity = SourceIdentity::from_display_path("Src/Foo.C");
        assert_eq!(identity.lookup_key().as_bytes(), b"Src/Foo.C");
        assert_eq!(identity.display_path().as_bytes(), b"Src/Foo.C");
    }

    #[test]
    fn diagnostic_path_is_optional_and_non_identity() {
        let left =
            SourceIdentity::from_display_path("/build/a.c").with_diagnostic_path("/resolved/a.c");
        let right = SourceIdentity::from_display_path("/build/a.c");
        assert_eq!(left.lookup_key(), right.lookup_key());
        assert_eq!(left.display_path(), right.display_path());
        // Provenance must not create a second semantic identity.
        assert_eq!(left, right);
        assert_eq!(
            left.diagnostic_path().map(ByteString::as_bytes),
            Some(b"/resolved/a.c".as_slice())
        );
        assert!(right.diagnostic_path().is_none());
    }

    #[test]
    fn unsanitized_test_name_provenance_is_not_semantic() {
        let clean = TestName::new("clean");
        let with_raw = TestName::new("clean").with_unsanitized("raw,name");
        assert_eq!(clean, with_raw);
    }

    #[test]
    fn test_name_preserves_empty_and_diff_suffix_bytes() {
        assert!(TestName::empty().is_empty());
        let diff = TestName::new("suite,diff");
        assert_eq!(diff.as_bytes(), b"suite,diff");
        let with_raw = TestName::new("clean").with_unsanitized("raw,name");
        assert_eq!(with_raw.as_bytes(), b"clean");
        assert_eq!(
            with_raw.unsanitized().map(ByteString::as_bytes),
            Some(b"raw,name".as_slice())
        );
    }

    #[test]
    fn lookup_key_equality_follows_constructed_bytes() {
        let sensitive = SourceLookupKey::from_path_bytes("A.c");
        let folded = SourceLookupKey::ascii_case_insensitive("A.c");
        assert_ne!(sensitive, folded);
        assert_eq!(
            SourceLookupKey::ascii_case_insensitive("A.c"),
            SourceLookupKey::ascii_case_insensitive("a.C")
        );
    }
}
