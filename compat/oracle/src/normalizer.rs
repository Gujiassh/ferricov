use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt;
use std::str::FromStr;

/// Reviewed transformations that may be applied before comparison.
#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub enum NormalizerId {
    #[serde(rename = "exact-v1")]
    ExactV1,
    #[serde(rename = "text-crlf-to-lf-v1")]
    TextCrlfToLfV1,
}

impl NormalizerId {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ExactV1 => "exact-v1",
            Self::TextCrlfToLfV1 => "text-crlf-to-lf-v1",
        }
    }
}

impl fmt::Display for NormalizerId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl FromStr for NormalizerId {
    type Err = UnknownNormalizer;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "exact-v1" => Ok(Self::ExactV1),
            "text-crlf-to-lf-v1" => Ok(Self::TextCrlfToLfV1),
            _ => Err(UnknownNormalizer(value.to_owned())),
        }
    }
}

#[derive(Debug)]
pub struct UnknownNormalizer(String);

impl fmt::Display for UnknownNormalizer {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "unknown normalizer: {}", self.0)
    }
}

impl Error for UnknownNormalizer {}

pub fn normalize(id: NormalizerId, input: &[u8]) -> Vec<u8> {
    match id {
        NormalizerId::ExactV1 => input.to_vec(),
        NormalizerId::TextCrlfToLfV1 => crlf_to_lf(input),
    }
}

fn crlf_to_lf(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    let mut index = 0;
    while index < input.len() {
        if input[index] == b'\r' && input.get(index + 1) == Some(&b'\n') {
            output.push(b'\n');
            index += 2;
        } else {
            output.push(input[index]);
            index += 1;
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_normalizer_preserves_arbitrary_bytes() {
        let input = b"a\0b\r\nc";

        assert_eq!(normalize(NormalizerId::ExactV1, input), input);
    }

    #[test]
    fn line_ending_normalizer_only_rewrites_crlf_pairs() {
        let input = b"windows\r\nunix\nold-mac\r";

        assert_eq!(
            normalize(NormalizerId::TextCrlfToLfV1, input),
            b"windows\nunix\nold-mac\r"
        );
    }

    #[test]
    fn rejects_unregistered_normalizer() {
        assert!("strip-everything-v1".parse::<NormalizerId>().is_err());
    }
}
