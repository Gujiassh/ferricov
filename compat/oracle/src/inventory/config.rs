use super::{
    Classification, NamedEntry, SourceKind, SourceReference, named_entry, push_source, slug,
};
use std::collections::BTreeMap;
use std::collections::BTreeSet;
use std::error::Error;
use std::fs;
use std::path::Path;

fn config_key_from_line(line: &str) -> Option<&str> {
    let candidate = line.trim_start().trim_start_matches('#').trim_start();
    let (key, _) = candidate.split_once('=')?;
    let key = key.trim();
    let mut chars = key.chars();
    if !chars
        .next()
        .is_some_and(|first| first.is_ascii_alphabetic())
    {
        return None;
    }
    chars
        .all(|character| character.is_ascii_alphanumeric() || character == '_')
        .then_some(key)
}

/// Extract active and commented syntactic key candidates from `lcovrc` text.
pub fn extract_config_keys(input: &str) -> BTreeSet<String> {
    input
        .lines()
        .filter_map(config_key_from_line)
        .map(str::to_owned)
        .collect()
}

pub(super) fn extract_config_entries(input: &str, source_path: &str) -> Vec<NamedEntry> {
    let mut entries: BTreeMap<String, NamedEntry> = BTreeMap::new();
    for (offset, line) in input.lines().enumerate() {
        let Some(key) = config_key_from_line(line) else {
            continue;
        };
        let source = SourceReference {
            kind: SourceKind::ConfigDefinition,
            path: source_path.to_owned(),
            line: offset + 1,
        };
        match entries.get_mut(key) {
            Some(entry) => push_source(&mut entry.review.source_references, source),
            None => {
                entries.insert(
                    key.to_owned(),
                    named_entry(
                        format!("lcovrc.{}", slug(key)),
                        key.to_owned(),
                        Classification::Unreviewed,
                        source,
                    ),
                );
            }
        }
    }
    entries.into_values().collect()
}

/// Extract config keys that are registered in Perl source code but absent from
/// the distributed `lcovrc` template.  These are active keys with runtime
/// behaviour that the template-only scanner would miss.
pub(super) fn extract_registered_config_entries(
    upstream_root: &Path,
) -> Result<Vec<NamedEntry>, Box<dyn Error>> {
    // Registration regions (path, start_marker, end_marker).
    // These match the actual Perl hash declarations in the pinned upstream.
    let regions: &[(&str, &str, &str)] = &[
        // Shared config keys: lib/lcovutil.pm lines 1116-1203
        ("lib/lcovutil.pm", "my %rc_common = (", ");"),
        // geninfo-specific: lib/lcovutil.pm lines 1221-1235
        ("lib/lcovutil.pm", "our %geninfo_rc_opts = (", ");"),
        // genhtml-specific: bin/genhtml lines 7154-7213
        ("bin/genhtml", "my %genhtml_rc_opts = (", ");"),
        // lcov-specific: bin/lcov line 191
        ("bin/lcov", "my %lcov_rc_params = (", ");"),
    ];

    let mut entries: BTreeMap<String, NamedEntry> = BTreeMap::new();

    for &(path, start, end) in regions {
        let full = upstream_root.join(path);
        if !full.is_file() {
            continue;
        }
        let input = fs::read_to_string(&full)?;
        let keys = extract_registered_config_specifications(&input, start, end)?;
        for (key, line) in keys {
            let source = SourceReference {
                kind: SourceKind::ConfigDefinition,
                path: path.to_owned(),
                line,
            };
            match entries.get_mut(&key) {
                Some(entry) => push_source(&mut entry.review.source_references, source),
                None => {
                    entries.insert(
                        key.clone(),
                        named_entry(
                            format!("lcovrc.{}", slug(&key)),
                            key,
                            Classification::Unreviewed,
                            source,
                        ),
                    );
                }
            }
        }
    }

    // `config_file` is a recursive include directive handled before map lookup,
    // so it is an active public key even though it is absent from every map.
    let path = "lib/lcovutil.pm";
    let input = fs::read_to_string(upstream_root.join(path))?;
    let dynamic_lines = input
        .lines()
        .enumerate()
        .filter_map(|(offset, line)| {
            line.contains("if ($key eq 'config_file')")
                .then_some(offset + 1)
        })
        .collect::<Vec<_>>();
    if dynamic_lines.len() != 1 {
        return Err(format!(
            "expected one dynamic config_file directive, found {}",
            dynamic_lines.len()
        )
        .into());
    }
    let source = SourceReference {
        kind: SourceKind::ConfigDefinition,
        path: path.to_owned(),
        line: dynamic_lines[0],
    };
    let entry = entries.entry("config_file".to_owned()).or_insert_with(|| {
        named_entry(
            "lcovrc.config-file".to_owned(),
            "config_file".to_owned(),
            Classification::Unreviewed,
            source.clone(),
        )
    });
    push_source(&mut entry.review.source_references, source);

    Ok(entries.into_values().collect())
}

fn extract_registered_config_specifications(
    input: &str,
    start_marker: &str,
    end_marker: &str,
) -> Result<Vec<(String, usize)>, Box<dyn Error>> {
    let mut active = false;
    let mut found_end = false;
    let mut specifications = Vec::new();
    for (offset, line) in input.lines().enumerate() {
        if !active {
            if !line.contains(start_marker) {
                continue;
            }
            active = true;
        }

        if let Some(key) = first_quoted_config_key(line) {
            specifications.push((key, offset + 1));
        }
        if line.contains(end_marker) {
            found_end = true;
            break;
        }
    }
    if active && found_end {
        Ok(specifications)
    } else {
        // Region not found is OK — not every command has a config map.
        Ok(Vec::new())
    }
}

/// Extract the first single-quoted string that looks like a config hash key
/// (preceding `=>`).  Skips entries whose value is an array-ref `[...]`
/// (those are deprecated-alias registrations, not active keys).
fn first_quoted_config_key(line: &str) -> Option<String> {
    let (quote_index, quote) = line
        .char_indices()
        .find(|(_, character)| matches!(character, '\'' | '"'))?;
    let rest = &line[quote_index + quote.len_utf8()..];
    let end = rest.find(quote)?;
    let key = &rest[..end];
    let after_key = &rest[end + quote.len_utf8()..];
    // Must have => after the key.
    if !after_key.contains("=>") {
        return None;
    }
    // Skip deprecated-alias registrations whose value is an array-ref.
    let after_arrow = after_key.split_once("=>")?.1.trim_start();
    if after_arrow.starts_with('[') {
        return None;
    }
    Some(key.to_owned())
}
