//! Record-payload parsing and apply onto an open section / database.
//!
//! Happy-path + key edge semantics for CORE-006. Full Oracle ignore/stop
//! matrices and every malformed continuation quirk remain residual.

use ferricov_model::{
    BranchEdge, BranchKind, BranchTaken, ByteString, CoverageCount, CoverageDatabase,
    GroupSizeKey, LineKey, NumericAtom,
};

use crate::classify::RecordTag;
use crate::commit::{commit_section, ensure_source, CommitOutcome};
use crate::diag::{DiagClass, ParseDiag};
use crate::policy::IgnorePolicy;
use crate::record_parse::{
    is_digits, line_numerically_non_positive, parse_brda_field2, parse_u64_digits,
    split_at_last_comma, split_commas, split_da_count_checksum, split_once,
};
use crate::section::{BranchCursor, OpenSection};
use crate::state::{ParseEvent, ParserState};

/// Result of applying one classified record / terminator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ApplyResult {
    /// Record applied (or intentionally ignored, e.g. summary).
    Ok(ParseEvent),
    /// Ignorable diagnostic recorded; continue or stop per policy.
    Ignorable(ParseEvent, ParseDiag),
    /// Hard failure; caller should stop.
    HardFail(ParseDiag),
}

/// Mutable apply context owned by [`crate::parser::StreamingParser`].
#[derive(Debug, Clone)]
pub struct ApplyContext {
    pub db: CoverageDatabase,
    pub open: Option<OpenSection>,
    pub policy: IgnorePolicy,
    /// Stopped after hard-fail or Stop-policy ignorable.
    pub stopped: bool,
}

impl Default for ApplyContext {
    fn default() -> Self {
        Self::new(IgnorePolicy::Continue)
    }
}

impl ApplyContext {
    /// Create an empty apply context.
    #[must_use]
    pub fn new(policy: IgnorePolicy) -> Self {
        Self {
            db: CoverageDatabase::new(),
            open: None,
            policy,
            stopped: false,
        }
    }

    /// Borrow the coverage database.
    #[must_use]
    pub fn database(&self) -> &CoverageDatabase {
        &self.db
    }

    /// Take ownership of the coverage database.
    #[must_use]
    pub fn into_database(self) -> CoverageDatabase {
        self.db
    }
}

/// Dispatch a [`ParseEvent`] produced by binding-state into record apply.
pub fn apply_event(
    ctx: &mut ApplyContext,
    state: &mut ParserState,
    event: ParseEvent,
) -> ApplyResult {
    if ctx.stopped {
        return ApplyResult::Ok(event);
    }

    match event {
        ParseEvent::SourceBound(binding) => {
            // Opening a new source replaces the open working section without
            // auto-committing the previous one (Oracle filters unterminated).
            ctx.open = Some(OpenSection::new(binding.clone()));
            // Ensure the source exists early so VER can land on it.
            let _ = ensure_source(&mut ctx.db, ctx.open.as_ref().expect("just set"));
            ApplyResult::Ok(ParseEvent::SourceBound(binding))
        }
        ParseEvent::SourceSkippedEmpty { tag, payload } => {
            ctx.open = None;
            ApplyResult::Ok(ParseEvent::SourceSkippedEmpty { tag, payload })
        }
        ParseEvent::Terminator { unconsumed } => apply_terminator(ctx, state, unconsumed),
        ParseEvent::RecordStub {
            tag,
            payload,
            unconsumed,
        } => apply_record(ctx, state, tag, payload, unconsumed),
        ParseEvent::Malformed { kind, line } => {
            let diag = state.diagnostics().last().cloned().unwrap_or_else(|| {
                ParseDiag::error_format(
                    state.line_no(),
                    format!("unexpected .info file record '{}'", line.to_string_lossy()),
                    Some(line.clone()),
                )
            });
            handle_ignorable(ctx, ParseEvent::Malformed { kind, line }, diag)
        }
        other => ApplyResult::Ok(other),
    }
}

fn handle_ignorable(ctx: &mut ApplyContext, event: ParseEvent, diag: ParseDiag) -> ApplyResult {
    if ctx.policy.stops_on_ignorable() {
        ctx.stopped = true;
    }
    ApplyResult::Ignorable(event, diag)
}

fn apply_terminator(
    ctx: &mut ApplyContext,
    state: &mut ParserState,
    unconsumed: ByteString,
) -> ApplyResult {
    let Some(mut open) = ctx.open.take() else {
        return ApplyResult::Ok(ParseEvent::Terminator { unconsumed });
    };
    if state.source_skipped() {
        return ApplyResult::Ok(ParseEvent::Terminator { unconsumed });
    }

    let current_tn = state.test_name().clone();
    let line_no = state.line_no();
    match commit_section(&mut ctx.db, &mut open, &current_tn, line_no) {
        CommitOutcome::Committed | CommitOutcome::Noop => {
            // Oracle does not fully clear source binding; keep last binding on
            // ParserState but drop working buffers. Re-open is not automatic.
            ctx.open = None;
            ApplyResult::Ok(ParseEvent::Terminator { unconsumed })
        }
        CommitOutcome::HardFail(diag) => {
            state.push_diag(diag.clone());
            ctx.stopped = true;
            // Keep open buffers for diagnostics / residual inspection.
            ctx.open = Some(open);
            ApplyResult::HardFail(diag)
        }
    }
}

fn apply_record(
    ctx: &mut ApplyContext,
    state: &mut ParserState,
    tag: RecordTag,
    payload: ByteString,
    unconsumed: ByteString,
) -> ApplyResult {
    // Summaries never mutate model totals.
    if matches!(
        tag,
        RecordTag::Fnf
            | RecordTag::Fnh
            | RecordTag::Brf
            | RecordTag::Brh
            | RecordTag::Mcf
            | RecordTag::Mch
            | RecordTag::Lf
            | RecordTag::Lh
    ) {
        return ApplyResult::Ok(ParseEvent::RecordApplied {
            tag,
            payload,
            unconsumed,
        });
    }

    if state.source_skipped() || ctx.open.is_none() {
        // Records outside an open source: treat as format error for data tags.
        let diag = ParseDiag::error_format(
            state.line_no(),
            format!(
                "record {} without open source section",
                String::from_utf8_lossy(tag.as_bytes())
            ),
            Some(payload.clone()),
        );
        state.push_diag(diag.clone());
        return handle_ignorable(
            ctx,
            ParseEvent::RecordApplied {
                tag,
                payload,
                unconsumed,
            },
            diag,
        );
    }

    let result = match tag {
        RecordTag::Ver => apply_ver(ctx, state, &payload),
        RecordTag::Da => apply_da(ctx, state, &payload),
        RecordTag::Fn => apply_fn(ctx, state, &payload),
        RecordTag::Fnda => apply_fnda(ctx, state, &payload),
        RecordTag::Fnl => apply_fnl(ctx, state, &payload),
        RecordTag::Fna => apply_fna(ctx, state, &payload),
        RecordTag::Brda => apply_brda(ctx, state, &payload),
        RecordTag::Mcdc => apply_mcdc(ctx, state, &payload),
        _ => Ok(()),
    };

    match result {
        Ok(()) => ApplyResult::Ok(ParseEvent::RecordApplied {
            tag,
            payload,
            unconsumed,
        }),
        Err(diag) => {
            state.push_diag(diag.clone());
            if diag.class == DiagClass::HardFail {
                ctx.stopped = true;
                ApplyResult::HardFail(diag)
            } else {
                handle_ignorable(
                    ctx,
                    ParseEvent::RecordApplied {
                        tag,
                        payload,
                        unconsumed,
                    },
                    diag,
                )
            }
        }
    }
}

fn apply_ver(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // Full: nonempty payload (`^VER:(.+)$`).
    if payload.as_bytes().is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "empty VER payload",
            Some(payload.clone()),
        ));
    }
    let open = ctx.open.as_mut().expect("checked");
    if let Some(existing) = &open.version {
        if existing != payload {
            return Err(ParseDiag::version_conflict(
                state.line_no(),
                format!(
                    "conflicting version '{}' vs '{}'",
                    existing.to_string_lossy(),
                    payload.to_string_lossy()
                ),
                Some(payload.clone()),
            ));
        }
        return Ok(());
    }
    // Also conflict against already-committed source version.
    let key = open.identity().lookup_key().clone();
    if let Some(src) = ctx.db.get(&key) {
        if let Some(existing) = src.version() {
            if existing != payload {
                return Err(ParseDiag::version_conflict(
                    state.line_no(),
                    format!(
                        "conflicting version for {}: '{}' vs '{}'",
                        open.identity().display_path().to_string_lossy(),
                        existing.to_string_lossy(),
                        payload.to_string_lossy()
                    ),
                    Some(payload.clone()),
                ));
            }
        }
    }
    open.version = Some(payload.clone());
    Ok(())
}

fn apply_da(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^DA:(\d+),([^,]+)(,([^,\s]+))?` — prefix; split ourselves.
    let bytes = payload.as_bytes();
    let Some((line_tok, rest)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed DA record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(line_tok) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "DA line is not digits",
            Some(payload.clone()),
        ));
    }
    let line_key = LineKey::from_lexeme(line_tok.to_vec());
    if line_numerically_non_positive(line_tok) {
        // ERROR_FORMAT; under Continue policy we still retain the invalid line.
        // Record diagnostic via Err → Ignorable path, but we need mutation.
        // Handle by mutating then returning Err.
        let (count_tok, checksum) = split_da_count_checksum(rest);
        let count = CoverageCount::from_lexeme(count_tok.to_vec()).coerce_invalid_to_zero();
        accumulate_line(ctx, &line_key, count, checksum)?;
        return Err(ParseDiag::error_format(
            state.line_no(),
            "DA line number <= 0",
            Some(payload.clone()),
        ));
    }
    let (count_tok, checksum) = split_da_count_checksum(rest);
    let mut count = CoverageCount::from_lexeme(count_tok.to_vec());
    if matches!(
        count.validate(None),
        ferricov_model::CountValidation::CoerceToZero
    ) {
        count = count.coerce_invalid_to_zero();
        accumulate_line(ctx, &line_key, count, checksum)?;
        return Err(ParseDiag::error_format(
            state.line_no(),
            "nonnumeric or negative DA count",
            Some(payload.clone()),
        ));
    }
    accumulate_line(ctx, &line_key, count, checksum)
}

fn accumulate_line(
    ctx: &mut ApplyContext,
    line_key: &LineKey,
    count: CoverageCount,
    checksum: Option<ByteString>,
) -> Result<(), ParseDiag> {
    let open = ctx.open.as_mut().expect("checked");
    if let Some(existing) = open.lines.get(line_key).cloned() {
        let summed = existing.add(&count).unwrap_or_else(|_| count.clone());
        open.lines.insert(line_key.clone(), summed);
    } else {
        open.lines.insert(line_key.clone(), count);
    }
    if let Some(chk) = checksum {
        open.checksums
            .entry(line_key.clone())
            .or_insert(chk);
    }
    Ok(())
}


fn apply_fn(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^FN:(\d+),((\d+),)?(.+)$`
    let bytes = payload.as_bytes();
    let Some((start_tok, rest)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FN record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(start_tok) || rest.is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FN record",
            Some(payload.clone()),
        ));
    }
    let start = LineKey::from_lexeme(start_tok.to_vec());
    let (end, name) = match split_once(rest, b',') {
        Some((maybe_end, name_rest)) if is_digits(maybe_end) && !name_rest.is_empty() => {
            // Optional end line present.
            (
                Some(LineKey::from_lexeme(maybe_end.to_vec())),
                ByteString::from_slice(name_rest),
            )
        }
        _ => (None, ByteString::from_slice(rest)),
    };
    if name.as_bytes().is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "empty FN name",
            Some(payload.clone()),
        ));
    }
    if line_numerically_non_positive(start_tok)
        || end
            .as_ref()
            .is_some_and(|e| line_numerically_non_positive(e.lexeme().as_bytes()))
    {
        let open = ctx.open.as_mut().expect("checked");
        let _ = open.functions.ensure_group(start, name, end);
        return Err(ParseDiag::error_format(
            state.line_no(),
            "FN start/end <= 0",
            Some(payload.clone()),
        ));
    }
    let open = ctx.open.as_mut().expect("checked");
    open.functions
        .ensure_group(start, name, end)
        .map_err(|err| {
            ParseDiag::error_format(state.line_no(), format!("FN conflict: {err}"), None)
        })?;
    Ok(())
}

fn apply_fnda(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^FNDA:([^,]+),(.+)$`
    let bytes = payload.as_bytes();
    let Some((count_tok, name)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNDA record",
            Some(payload.clone()),
        ));
    };
    if name.is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "empty FNDA name",
            Some(payload.clone()),
        ));
    }
    let name_bs = ByteString::from_slice(name);
    let open = ctx.open.as_mut().expect("checked");
    if !open.functions.contains_alias(&name_bs) {
        return Err(ParseDiag::function_mismatch(
            state.line_no(),
            format!("unknown function '{}'", name_bs.to_string_lossy()),
            Some(payload.clone()),
        ));
    }
    let count = CoverageCount::from_lexeme(count_tok.to_vec()).coerce_invalid_to_zero();
    // Find start via reverse index and add.
    let start = open
        .functions
        .alias_index()
        .find(|(a, _)| *a == &name_bs)
        .map(|(_, s)| s.clone())
        .expect("contains_alias");
    open.functions
        .insert_alias_at(start, name_bs, count)
        .map_err(|err| {
            ParseDiag::error_format(state.line_no(), format!("FNDA failed: {err}"), None)
        })?;
    Ok(())
}

fn apply_fnl(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^FNL:(\d+),(\d+)(,(\d+))?$`
    let bytes = payload.as_bytes();
    let parts: Vec<&[u8]> = split_commas(bytes);
    if parts.len() < 2 || parts.len() > 3 {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNL record",
            Some(payload.clone()),
        ));
    }
    if !parts.iter().all(|p| is_digits(p)) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNL record",
            Some(payload.clone()),
        ));
    }
    let index = parse_u64_digits(parts[0]).unwrap_or(0);
    let start = LineKey::from_lexeme(parts[1].to_vec());
    let end = parts
        .get(2)
        .map(|p| LineKey::from_lexeme(p.to_vec()));
    let open = ctx.open.as_mut().expect("checked");
    if open.fnl_index.contains_key(&index) {
        return Err(ParseDiag::duplicate_fnl(
            state.line_no(),
            format!("duplicate FNL index {index}"),
        ));
    }
    open.fnl_index.insert(index, (start, end));
    Ok(())
}

fn apply_fna(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^FNA:(\d+),([^,]+),(.+)$`
    let bytes = payload.as_bytes();
    let Some((idx_tok, rest)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNA record",
            Some(payload.clone()),
        ));
    };
    let Some((count_tok, alias)) = split_once(rest, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNA record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(idx_tok) || alias.is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed FNA record",
            Some(payload.clone()),
        ));
    }
    let index = parse_u64_digits(idx_tok).unwrap_or(0);
    let open = ctx.open.as_mut().expect("checked");
    let Some((start, end)) = open.fnl_index.get(&index).cloned() else {
        return Err(ParseDiag::unknown_fnl(
            state.line_no(),
            format!("unknown FNL index {index}"),
        ));
    };
    let count = CoverageCount::from_lexeme(count_tok.to_vec()).coerce_invalid_to_zero();
    let alias_bs = ByteString::from_slice(alias);
    open.functions
        .ensure_group(start.clone(), alias_bs.clone(), end)
        .map_err(|err| {
            ParseDiag::error_format(state.line_no(), format!("FNA ensure: {err}"), None)
        })?;
    open.functions
        .insert_alias_at(start, alias_bs, count)
        .map_err(|err| {
            ParseDiag::error_format(state.line_no(), format!("FNA insert: {err}"), None)
        })?;
    Ok(())
}

fn apply_brda(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^BRDA:(\d+),([ef]?)(U?)(\d+),(.+)$`
    let bytes = payload.as_bytes();
    let Some((line_tok, rest)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed BRDA record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(line_tok) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "BRDA line is not digits",
            Some(payload.clone()),
        ));
    }
    let line_key = LineKey::from_lexeme(line_tok.to_vec());
    // Second field: [ef]? U? digits  then comma + expression,taken
    let Some(comma2) = rest.iter().position(|&b| b == b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed BRDA record",
            Some(payload.clone()),
        ));
    };
    let field2 = &rest[..comma2];
    let tail = &rest[comma2 + 1..];
    let (kind, excluded, block_tok) = parse_brda_field2(field2).ok_or_else(|| {
        ParseDiag::error_format(
            state.line_no(),
            "malformed BRDA block field",
            Some(payload.clone()),
        )
    })?;
    // Split tail at last comma → expression, taken
    let (expr, taken_tok) = split_at_last_comma(tail);
    let taken = BranchTaken::from_token(taken_tok);
    let expression = if expr.is_empty() {
        None
    } else {
        Some(ByteString::from_slice(expr))
    };

    let open = ctx.open.as_mut().expect("checked");
    let block_token = ByteString::from_slice(block_tok);
    let need_new_block = match &open.branch_cursor {
        Some(cur) if cur.line == line_key && cur.block_token == block_token => false,
        _ => true,
    };
    let bline = open.branches.entry_line(line_key.clone());
    if need_new_block || bline.is_empty() {
        bline.push_block();
    }
    bline
        .last_block_mut()
        .expect("block")
        .append_edge(BranchEdge::new(taken, kind, expression, excluded));
    open.branch_cursor = Some(BranchCursor {
        line: line_key.clone(),
        block_token,
    });

    if line_numerically_non_positive(line_tok) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "BRDA line number <= 0",
            Some(payload.clone()),
        ));
    }
    Ok(())
}


fn apply_mcdc(
    ctx: &mut ApplyContext,
    state: &ParserState,
    payload: &ByteString,
) -> Result<(), ParseDiag> {
    // `^MCDC:(\d+),(U?)(\d+),([tf]),(\d+),(\d+),(.+)$`
    let bytes = payload.as_bytes();
    let Some((line_tok, rest)) = split_once(bytes, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(line_tok) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "MCDC line is not digits",
            Some(payload.clone()),
        ));
    }
    let line_key = LineKey::from_lexeme(line_tok.to_vec());

    // field2: optional U + digits (group size)
    let Some((field2, rest)) = split_once(rest, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC record",
            Some(payload.clone()),
        ));
    };
    let (excluded, group_tok) = if field2.starts_with(b"U") {
        (true, &field2[1..])
    } else {
        (false, field2)
    };
    if !is_digits(group_tok) {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC group size",
            Some(payload.clone()),
        ));
    }
    let Some((sense_tok, rest)) = split_once(rest, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC record",
            Some(payload.clone()),
        ));
    };
    let true_sense = match sense_tok {
        b"t" => true,
        b"f" => false,
        _ => {
            return Err(ParseDiag::error_format(
                state.line_no(),
                "MCDC sense must be t or f",
                Some(payload.clone()),
            ));
        }
    };
    let Some((count_tok, rest)) = split_once(rest, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC record",
            Some(payload.clone()),
        ));
    };
    let Some((index_tok, expr)) = split_once(rest, b',') else {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC record",
            Some(payload.clone()),
        ));
    };
    if !is_digits(count_tok) || !is_digits(index_tok) || expr.is_empty() {
        return Err(ParseDiag::error_format(
            state.line_no(),
            "malformed MCDC count/index/expression",
            Some(payload.clone()),
        ));
    }

    // Contiguous line rule / already-defined hard-fail.
    {
        let open = ctx.open.as_ref().expect("checked");
        if open.mcdc_closed_lines.contains_key(&line_key) {
            return Err(ParseDiag::mcdc_already_defined(
                state.line_no(),
                format!(
                    "MCDC already defined for {}",
                    line_key.lexeme().to_string_lossy()
                ),
            ));
        }
        if let Some(cur) = &open.mcdc_current_line {
            if cur != &line_key {
                // Closing previous line in the open block: mark it closed for
                // revisit, but keep data in mcdc_open until section commit.
                // Soft close of previous line identity only.
            }
        }
    }
    // If switching lines, mark previous line as closed within this section.
    {
        let open = ctx.open.as_mut().expect("checked");
        if let Some(cur) = open.mcdc_current_line.clone() {
            if cur != line_key {
                open.mcdc_closed_lines.insert(cur, ());
                // If we're returning to a line that was already closed → hard fail
                // (checked above via mcdc_closed_lines for line_key).
            }
        }
        // Returning to a previously closed line in this section:
        if open.mcdc_closed_lines.contains_key(&line_key) {
            return Err(ParseDiag::mcdc_already_defined(
                state.line_no(),
                format!(
                    "MCDC already defined for {}",
                    line_key.lexeme().to_string_lossy()
                ),
            ));
        }
        open.mcdc_current_line = Some(line_key.clone());
        open.mcdc_closed = false;
    }

    let group_key = GroupSizeKey::from_lexeme(group_tok.to_vec());
    let declared = NumericAtom::from_lexeme(index_tok.to_vec());
    let count = CoverageCount::from_lexeme(count_tok.to_vec());
    let expr_bs = ByteString::from_slice(expr);
    let line_no = state.line_no();

    let open = ctx.open.as_mut().expect("checked");
    let mline = open.mcdc_open.entry_line(line_key.clone());

    // Find existing by declared index lexeme (immutable probe).
    let existing_pos = mline
        .get_group(&group_key)
        .and_then(|group| {
            group
                .iter()
                .position(|e| e.declared_index().lexeme().as_bytes() == index_tok)
        });
    let next_pos = mline
        .get_group(&group_key)
        .map(|g| g.len())
        .unwrap_or(0);
    let mut gap_diag: Option<ParseDiag> = None;
    if let Some(pos) = existing_pos {
        let group = mline.entry_group(group_key.clone());
        let expr_ref = &mut group[pos];
        let mismatch = expr_ref.expression() != &expr_bs;
        expr_ref
            .set_sense(true_sense, count, excluded)
            .map_err(|err| {
                ParseDiag::error_format(line_no, format!("MCDC sense add: {err}"), None)
            })?;
        if mismatch {
            return Err(ParseDiag::inconsistent_data(
                line_no,
                "MCDC expression mismatch for index",
                Some(payload.clone()),
            ));
        }
    } else {
        // Contiguity: first new index must be 0; later contiguous. Gap → format.
        let idx_num = parse_u64_digits(index_tok).unwrap_or(u64::MAX);
        if (next_pos == 0 && idx_num != 0)
            || (next_pos > 0 && idx_num != next_pos as u64)
        {
            gap_diag = Some(ParseDiag::error_format(
                line_no,
                if next_pos == 0 {
                    "MCDC index gap (first index must be 0)"
                } else {
                    "MCDC index gap"
                },
                Some(payload.clone()),
            ));
        }
        let expr_ref = mline.append_expression(group_key, declared, expr_bs);
        expr_ref
            .set_sense(true_sense, count, excluded)
            .map_err(|err| {
                ParseDiag::error_format(line_no, format!("MCDC sense: {err}"), None)
            })?;
    }

    if line_numerically_non_positive(line_tok) {
        return Err(ParseDiag::error_format(
            line_no,
            "MCDC line number <= 0",
            Some(payload.clone()),
        ));
    }
    if let Some(diag) = gap_diag {
        return Err(diag);
    }
    Ok(())
}
