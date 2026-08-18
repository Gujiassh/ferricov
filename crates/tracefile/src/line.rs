//! Logical-line splitting and Perl-compatible normalization.
//!
//! # Oracle chomp / CRLF rule (Linux)
//!
//! Pinned LCOV 2.5 `_read_info` does:
//!
//! 1. Perl `readline` (`<>`) — splits only on `\n` (`$/` default).
//! 2. `chomp` — removes one trailing `\n` (the input record separator).
//! 3. `$line =~ s/\s+$//` — strips trailing Perl `\s`.
//!
//! On the pinned Linux Perl 5.38 runtime without Unicode semantics for these
//! operators, `\s` matches exactly the ASCII set
//! `{0x09,0x0A,0x0B,0x0C,0x0D,0x20}` (`\t \n \v \f \r space`). Bytes such as
//! NEL (`0x85`) and NBSP (`0xA0`) are **not** whitespace.
//!
//! CRLF fixtures therefore normalize as: readline keeps `\r\n` → `chomp`
//! drops `\n` → trailing-`\s` drops the leftover `\r`.
//!
//! # Ferricov splitter choice
//!
//! This crate accepts raw byte streams and therefore splits on `\r\n`, `\n`,
//! or a lone `\r` (universal newlines). After the terminator is stripped, the
//! trailing-`\s` step matches Oracle. For ordinary LF and CRLF fixtures the
//! normalized line bytes are identical to Oracle. Lone-`\r`-only files are
//! split here but would be a single readline record under Oracle on Linux;
//! that difference is intentional for byte-stream robustness and is recorded
//! as a residual for differential cases that use CR-only separators.

/// ASCII Perl `\s` bytes observed on the pinned Linux runtime.
pub const PERL_ASCII_WS: &[u8] = &[0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20];

/// Return `true` when `byte` is in the pinned Perl ASCII `\s` set.
#[must_use]
pub fn is_perl_ascii_ws(byte: u8) -> bool {
    matches!(byte, 0x09 | 0x0A | 0x0B | 0x0C | 0x0D | 0x20)
}

/// Remove all trailing Perl ASCII `\s` bytes (Oracle `$line =~ s/\s+$//`).
#[must_use]
pub fn trim_trailing_perl_ws(bytes: &[u8]) -> &[u8] {
    let mut end = bytes.len();
    while end > 0 && is_perl_ascii_ws(bytes[end - 1]) {
        end -= 1;
    }
    &bytes[..end]
}

/// Apply Oracle-equivalent post-readline normalization to one raw record.
///
/// `raw` is the bytes of one logical line **including** an optional trailing
/// terminator (`\n`, `\r\n`, or `\r`). This function:
///
/// 1. Strips one trailing line terminator (Perl `chomp` for `\n`, plus the
///    `\r` that CRLF leaves for trailing-`\s` to remove — or the universal
///    `\r\n` / `\r` terminator consumed by the Ferricov splitter).
/// 2. Strips trailing Perl ASCII `\s`.
///
/// The result still owns arbitrary payload bytes (including interior `\0` and
/// non-UTF-8). Leading whitespace is preserved.
#[must_use]
pub fn normalize_logical_line(raw: &[u8]) -> Vec<u8> {
    let without_term = strip_line_terminator(raw);
    trim_trailing_perl_ws(without_term).to_vec()
}

/// Strip a single trailing `\r\n`, `\n`, or `\r` terminator if present.
#[must_use]
pub fn strip_line_terminator(raw: &[u8]) -> &[u8] {
    if raw.ends_with(b"\r\n") {
        &raw[..raw.len() - 2]
    } else if raw.ends_with(b"\n") || raw.ends_with(b"\r") {
        &raw[..raw.len() - 1]
    } else {
        raw
    }
}

/// Line terminator kind recognized by the Ferricov byte-stream splitter.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LineEnding {
    /// `\n`
    Lf,
    /// `\r\n`
    Crlf,
    /// Lone `\r`
    Cr,
    /// Final buffer chunk with no terminator.
    None,
}

/// One raw logical line extracted from a byte stream (terminator excluded).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawLogicalLine {
    /// Line bytes without the terminator.
    pub bytes: Vec<u8>,
    /// Terminator that ended this line (or [`LineEnding::None`] at EOF).
    pub ending: LineEnding,
}

impl RawLogicalLine {
    /// Normalize with Perl trailing-`\s` rules.
    #[must_use]
    pub fn normalized(&self) -> Vec<u8> {
        trim_trailing_perl_ws(&self.bytes).to_vec()
    }
}

/// Incremental splitter for `\n` / `\r\n` / lone `\r` without UTF-8 checks.
#[derive(Debug, Default, Clone)]
pub struct LineSplitter {
    buf: Vec<u8>,
    /// True when the previous chunk ended with a bare `\r` that might start CRLF.
    pending_cr: bool,
}

impl LineSplitter {
    /// Create an empty splitter.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Feed more input bytes and return completed raw lines (terminator excluded).
    pub fn feed(&mut self, input: &[u8]) -> Vec<RawLogicalLine> {
        let mut out = Vec::new();
        let mut i = 0usize;
        while i < input.len() {
            let byte = input[i];
            if self.pending_cr {
                self.pending_cr = false;
                if byte == b'\n' {
                    // Completed CRLF across the chunk boundary.
                    out.push(RawLogicalLine {
                        bytes: std::mem::take(&mut self.buf),
                        ending: LineEnding::Crlf,
                    });
                    i += 1;
                    continue;
                }
                // Lone CR ended the previous line; current byte starts the next.
                out.push(RawLogicalLine {
                    bytes: std::mem::take(&mut self.buf),
                    ending: LineEnding::Cr,
                });
                // Fall through to process `byte` as the start of a new line.
            }

            match byte {
                b'\n' => {
                    out.push(RawLogicalLine {
                        bytes: std::mem::take(&mut self.buf),
                        ending: LineEnding::Lf,
                    });
                    i += 1;
                }
                b'\r' => {
                    // May be CRLF; peek next byte if available.
                    if i + 1 < input.len() {
                        if input[i + 1] == b'\n' {
                            out.push(RawLogicalLine {
                                bytes: std::mem::take(&mut self.buf),
                                ending: LineEnding::Crlf,
                            });
                            i += 2;
                        } else {
                            out.push(RawLogicalLine {
                                bytes: std::mem::take(&mut self.buf),
                                ending: LineEnding::Cr,
                            });
                            i += 1;
                        }
                    } else {
                        // CR at end of chunk — defer until next feed/finish.
                        self.pending_cr = true;
                        i += 1;
                    }
                }
                _ => {
                    self.buf.push(byte);
                    i += 1;
                }
            }
        }
        out
    }

    /// Flush any buffered final line (including a deferred lone `\r`).
    pub fn finish(&mut self) -> Option<RawLogicalLine> {
        if self.pending_cr {
            self.pending_cr = false;
            return Some(RawLogicalLine {
                bytes: std::mem::take(&mut self.buf),
                ending: LineEnding::Cr,
            });
        }
        if self.buf.is_empty() {
            None
        } else {
            Some(RawLogicalLine {
                bytes: std::mem::take(&mut self.buf),
                ending: LineEnding::None,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn chomp_lf_and_crlf_match_oracle_linux() {
        // Oracle: chomp drops \n; trailing \s drops leftover \r from CRLF.
        assert_eq!(normalize_logical_line(b"TN:name\n"), b"TN:name");
        assert_eq!(normalize_logical_line(b"TN:name\r\n"), b"TN:name");
        assert_eq!(normalize_logical_line(b"TN:name  \t\r\n"), b"TN:name");
        assert_eq!(normalize_logical_line(b"TN:name\r"), b"TN:name");
    }

    #[test]
    fn trailing_ws_uses_perl_ascii_set_only() {
        assert_eq!(trim_trailing_perl_ws(b"a\t\n\x0B\x0C\r "), b"a");
        // NEL / NBSP are not Perl ASCII \s on the pinned runtime.
        assert_eq!(trim_trailing_perl_ws(b"a\x85"), b"a\x85");
        assert_eq!(trim_trailing_perl_ws(b"a\xA0"), b"a\xA0");
    }

    #[test]
    fn leading_ws_preserved() {
        assert_eq!(normalize_logical_line(b" #not-comment\n"), b" #not-comment");
        assert_eq!(normalize_logical_line(b"  TN:x\n"), b"  TN:x");
    }

    #[test]
    fn splitter_handles_lf_crlf_and_lone_cr() {
        let mut s = LineSplitter::new();
        let lines = s.feed(b"a\nb\r\nc\rd");
        let last = s.finish();
        assert_eq!(lines.len(), 3);
        assert_eq!(lines[0].bytes, b"a");
        assert_eq!(lines[0].ending, LineEnding::Lf);
        assert_eq!(lines[1].bytes, b"b");
        assert_eq!(lines[1].ending, LineEnding::Crlf);
        assert_eq!(lines[2].bytes, b"c");
        assert_eq!(lines[2].ending, LineEnding::Cr);
        assert_eq!(last.unwrap().bytes, b"d");
    }

    #[test]
    fn splitter_defers_cr_across_chunks() {
        let mut s = LineSplitter::new();
        assert!(s.feed(b"ab\r").is_empty());
        let lines = s.feed(b"\ncd\n");
        assert_eq!(lines.len(), 2);
        assert_eq!(lines[0].bytes, b"ab");
        assert_eq!(lines[0].ending, LineEnding::Crlf);
        assert_eq!(lines[1].bytes, b"cd");
        assert_eq!(lines[1].ending, LineEnding::Lf);
        assert!(s.finish().is_none());
    }

    #[test]
    fn non_utf8_bytes_survive_normalization() {
        let raw = b"SF:path/\xff\x80\n";
        assert_eq!(normalize_logical_line(raw), b"SF:path/\xff\x80");
    }
}
