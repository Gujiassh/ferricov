//! Hierarchical ordered branch coverage.
//!
//! Normative layout comes from `coverage-model.md` "Ordered Branch Coverage".
//! Algebra, writer renumbering, and parser transition ownership are deferred.

use crate::branch::BranchTaken;
use crate::bytes::ByteString;
use crate::keys::LineKey;
use std::collections::BTreeMap;
use std::fmt;

/// Branch kind / type. Expressions are not part of the block signature.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum BranchKind {
    /// Ordinary / vanilla branch (`b` signature letter).
    Vanilla,
    /// Exception branch (`e`).
    Exception,
    /// Fallthrough branch (`f`).
    Fallthrough,
}

impl BranchKind {
    /// Single-byte signature letter used by Oracle `BranchElement::signature`.
    #[must_use]
    pub const fn signature_byte(self) -> u8 {
        match self {
            Self::Vanilla => b'b',
            Self::Exception => b'e',
            Self::Fallthrough => b'f',
        }
    }

    /// Parse a signature letter. Unknown letters return `None`.
    #[must_use]
    pub const fn from_signature_byte(byte: u8) -> Option<Self> {
        match byte {
            b'b' => Some(Self::Vanilla),
            b'e' => Some(Self::Exception),
            b'f' => Some(Self::Fallthrough),
            _ => None,
        }
    }
}

/// One edge inside a branch block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BranchEdge {
    derived_index: usize,
    taken: BranchTaken,
    expression: Option<ByteString>,
    kind: BranchKind,
    excluded: bool,
}

impl BranchEdge {
    /// Construct an edge. `derived_index` is assigned by the owning block.
    #[must_use]
    pub fn new(
        taken: BranchTaken,
        kind: BranchKind,
        expression: Option<ByteString>,
        excluded: bool,
    ) -> Self {
        Self {
            derived_index: 0,
            taken,
            expression,
            kind,
            excluded,
        }
    }

    /// Convenience: vanilla, non-excluded edge from a taken token.
    #[must_use]
    pub fn from_taken(taken: BranchTaken) -> Self {
        Self::new(taken, BranchKind::Vanilla, None, false)
    }

    /// Derived edge index (position in the owning block after construction).
    #[must_use]
    pub fn derived_index(&self) -> usize {
        self.derived_index
    }

    /// Borrow taken state (`-` or evaluated count).
    #[must_use]
    pub fn taken(&self) -> &BranchTaken {
        &self.taken
    }

    /// Mutable taken state.
    pub fn taken_mut(&mut self) -> &mut BranchTaken {
        &mut self.taken
    }

    /// Optional expression bytes (not part of signature).
    #[must_use]
    pub fn expression(&self) -> Option<&ByteString> {
        self.expression.as_ref()
    }

    /// Branch kind participating in the block signature.
    #[must_use]
    pub fn kind(&self) -> BranchKind {
        self.kind
    }

    /// Whether this edge is excluded (`U` record retention).
    #[must_use]
    pub fn is_excluded(&self) -> bool {
        self.excluded
    }

    /// Mark excluded (sticky for CORE-003; clearing is not provided).
    pub fn set_excluded(&mut self) {
        self.excluded = true;
    }
}

/// Ordered block of edges with a kind-only signature.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BranchBlock {
    model_position: usize,
    signature: Vec<BranchKind>,
    edges: Vec<BranchEdge>,
}

impl BranchBlock {
    /// Create an empty block at `model_position`.
    #[must_use]
    pub fn new(model_position: usize) -> Self {
        Self {
            model_position,
            signature: Vec::new(),
            edges: Vec::new(),
        }
    }

    /// Model-order position assigned when the block was created.
    #[must_use]
    pub fn model_position(&self) -> usize {
        self.model_position
    }

    /// Ordered kind signature (expressions excluded).
    #[must_use]
    pub fn signature(&self) -> &[BranchKind] {
        &self.signature
    }

    /// Signature as Oracle letter bytes (`b`/`e`/`f`).
    #[must_use]
    pub fn signature_bytes(&self) -> Vec<u8> {
        self.signature
            .iter()
            .map(|k| k.signature_byte())
            .collect()
    }

    /// Borrow edges in derived-index order.
    #[must_use]
    pub fn edges(&self) -> &[BranchEdge] {
        &self.edges
    }

    /// Mutable edges. Call [`BranchBlock::rebuild_signature_and_indexes`] after
    /// structural edits that change kind order or length.
    pub fn edges_mut(&mut self) -> &mut [BranchEdge] {
        &mut self.edges
    }

    /// Append an edge, assigning `derived_index` and extending the signature.
    pub fn append_edge(&mut self, mut edge: BranchEdge) {
        edge.derived_index = self.edges.len();
        self.signature.push(edge.kind);
        self.edges.push(edge);
    }

    /// Rebuild signature from edge kinds and reassign derived indexes.
    pub fn rebuild_signature_and_indexes(&mut self) {
        self.signature.clear();
        for (idx, edge) in self.edges.iter_mut().enumerate() {
            edge.derived_index = idx;
            self.signature.push(edge.kind);
        }
    }

    /// Return `true` when signature equals ordered edge kinds and every
    /// `derived_index` equals its position.
    #[must_use]
    pub fn invariants_hold(&self) -> bool {
        if self.signature.len() != self.edges.len() {
            return false;
        }
        self.edges.iter().enumerate().all(|(idx, edge)| {
            edge.derived_index == idx && self.signature.get(idx) == Some(&edge.kind)
        })
    }
}

/// Branch blocks on a single line, retained in model order.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BranchLine {
    blocks_in_model_order: Vec<BranchBlock>,
}

impl BranchLine {
    /// Create an empty line.
    #[must_use]
    pub fn new() -> Self {
        Self {
            blocks_in_model_order: Vec::new(),
        }
    }

    /// Borrow blocks in model order.
    #[must_use]
    pub fn blocks(&self) -> &[BranchBlock] {
        &self.blocks_in_model_order
    }

    /// Mutable blocks.
    pub fn blocks_mut(&mut self) -> &mut Vec<BranchBlock> {
        &mut self.blocks_in_model_order
    }

    /// Append a new empty block and return its model position.
    pub fn push_block(&mut self) -> usize {
        let pos = self.blocks_in_model_order.len();
        self.blocks_in_model_order.push(BranchBlock::new(pos));
        pos
    }

    /// Append `block`, forcing its `model_position` to the next contiguous index.
    pub fn append_block(&mut self, mut block: BranchBlock) -> usize {
        let pos = self.blocks_in_model_order.len();
        block.model_position = pos;
        self.blocks_in_model_order.push(block);
        pos
    }

    /// Borrow the last block when present.
    #[must_use]
    pub fn last_block(&self) -> Option<&BranchBlock> {
        self.blocks_in_model_order.last()
    }

    /// Mutable last block.
    pub fn last_block_mut(&mut self) -> Option<&mut BranchBlock> {
        self.blocks_in_model_order.last_mut()
    }

    /// Return `true` when no blocks are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.blocks_in_model_order.is_empty()
    }
}

/// Errors from branch invariant checks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BranchError {
    /// Block signature / derived_index invariant failed.
    Invariant(String),
}

impl fmt::Display for BranchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invariant(msg) => write!(f, "branch invariant: {msg}"),
        }
    }
}

impl std::error::Error for BranchError {}

/// Line-keyed hierarchical branch coverage.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BranchCoverage {
    lines: BTreeMap<LineKey, BranchLine>,
}

impl BranchCoverage {
    /// Create an empty branch coverage store.
    #[must_use]
    pub fn new() -> Self {
        Self {
            lines: BTreeMap::new(),
        }
    }

    /// Return `true` when no branch lines are stored.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.lines.is_empty()
    }

    /// Number of lines that currently hold branch data.
    #[must_use]
    pub fn line_len(&self) -> usize {
        self.lines.len()
    }

    /// Insert or replace a full [`BranchLine`].
    pub fn insert_line(&mut self, key: LineKey, line: BranchLine) -> Option<BranchLine> {
        self.lines.insert(key, line)
    }

    /// Ensure a line exists and return a mutable reference.
    pub fn entry_line(&mut self, key: LineKey) -> &mut BranchLine {
        self.lines.entry(key).or_default()
    }

    /// Borrow a branch line.
    #[must_use]
    pub fn get_line(&self, key: &LineKey) -> Option<&BranchLine> {
        self.lines.get(key)
    }

    /// Mutable borrow of a branch line.
    pub fn get_line_mut(&mut self, key: &LineKey) -> Option<&mut BranchLine> {
        self.lines.get_mut(key)
    }

    /// Return `true` when the map contains `key`.
    #[must_use]
    pub fn contains_line(&self, key: &LineKey) -> bool {
        self.lines.contains_key(key)
    }

    /// Iterate lines in key order.
    pub fn lines(&self) -> impl Iterator<Item = (&LineKey, &BranchLine)> {
        self.lines.iter()
    }

    /// Append a taken edge to the last block on `key`, creating line/block as needed.
    ///
    /// Convenience for store smoke tests and simple construction. Kind defaults
    /// to [`BranchKind::Vanilla`], non-excluded.
    pub fn push_taken_on_line(&mut self, key: LineKey, taken: BranchTaken) {
        let line = self.entry_line(key);
        if line.is_empty() {
            line.push_block();
        }
        line.last_block_mut()
            .expect("block just ensured")
            .append_edge(BranchEdge::from_taken(taken));
    }

    /// Assert signature / derived_index invariants for every block.
    pub fn assert_invariants(&self) -> Result<(), BranchError> {
        for (key, line) in &self.lines {
            for (pos, block) in line.blocks().iter().enumerate() {
                if block.model_position() != pos {
                    return Err(BranchError::Invariant(format!(
                        "line {}: block model_position {} != order index {}",
                        key.lexeme(),
                        block.model_position(),
                        pos
                    )));
                }
                if !block.invariants_hold() {
                    return Err(BranchError::Invariant(format!(
                        "line {}: block {} signature/derived_index mismatch",
                        key.lexeme(),
                        pos
                    )));
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{BranchCoverage, BranchEdge, BranchKind, BranchLine};
    use crate::branch::BranchTaken;
    use crate::bytes::ByteString;
    use crate::keys::LineKey;
    use crate::numeric::CoverageCount;

    #[test]
    fn append_edges_builds_signature_and_derived_indexes() {
        let mut line = BranchLine::new();
        let pos = line.push_block();
        assert_eq!(pos, 0);
        let block = line.last_block_mut().unwrap();
        block.append_edge(BranchEdge::new(
            BranchTaken::from_token("1"),
            BranchKind::Vanilla,
            Some(ByteString::from("x > 0")),
            false,
        ));
        block.append_edge(BranchEdge::new(
            BranchTaken::from_token("0"),
            BranchKind::Exception,
            None,
            false,
        ));
        block.append_edge(BranchEdge::new(
            BranchTaken::NeverEvaluated,
            BranchKind::Fallthrough,
            None,
            false,
        ));

        assert_eq!(
            block.signature(),
            &[
                BranchKind::Vanilla,
                BranchKind::Exception,
                BranchKind::Fallthrough
            ]
        );
        assert_eq!(block.signature_bytes(), b"bef");
        // expressions are not in the signature
        assert_eq!(block.edges().len(), 3);
        assert!(block.edges()[0].expression().is_some());
        for (idx, edge) in block.edges().iter().enumerate() {
            assert_eq!(edge.derived_index(), idx);
        }
        assert!(block.invariants_hold());
    }

    #[test]
    fn excluded_edge_retained_and_never_evaluated_distinct_from_zero() {
        let mut coverage = BranchCoverage::new();
        let key = LineKey::from_lexeme("12");
        let mut line = BranchLine::new();
        line.push_block();
        {
            let block = line.last_block_mut().unwrap();
            let mut excluded = BranchEdge::new(
                BranchTaken::evaluated(CoverageCount::from_lexeme("2")),
                BranchKind::Vanilla,
                None,
                false,
            );
            excluded.set_excluded();
            block.append_edge(excluded);
            block.append_edge(BranchEdge::from_taken(BranchTaken::from_token("-")));
            block.append_edge(BranchEdge::from_taken(BranchTaken::from_token("0")));
        }
        coverage.insert_line(key.clone(), line);

        let block = &coverage.get_line(&key).unwrap().blocks()[0];
        assert!(block.edges()[0].is_excluded());
        assert!(!block.edges()[0].taken().is_never_evaluated());
        assert!(block.edges()[1].taken().is_never_evaluated());
        assert!(!block.edges()[2].taken().is_never_evaluated());
        assert_ne!(block.edges()[1].taken(), block.edges()[2].taken());
        // excluded edge remains representable / serializable as data
        assert_eq!(block.edges().len(), 3);
        coverage.assert_invariants().unwrap();
    }
}
