use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BenchmarkSuite {
    pub schema_version: u32,
    pub suite_id: String,
    pub evidence_scope: String,
    pub image_reference: String,
    pub measurement_tool: RepositoryArtifact,
    pub environment_variables: BTreeMap<String, String>,
    pub cases: Vec<BenchmarkCase>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RepositoryArtifact {
    pub path: String,
    pub sha256: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BenchmarkCase {
    pub id: String,
    pub family: Family,
    pub approval: Approval,
    pub command: String,
    pub arguments: Vec<String>,
    pub fixture: Option<Fixture>,
    pub inventory_entries: Vec<String>,
    pub warmup_runs: usize,
    pub measured_runs: usize,
    pub expected_exit_code: i32,
    pub correctness_requirement: CorrectnessRequirement,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Approval {
    pub representative: bool,
    pub status: String,
    pub basis: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CorrectnessRequirement {
    pub required_evidence_scope: String,
    pub required_status: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Fixture {
    pub path: String,
    pub tree_sha256: String,
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Family {
    Startup,
    Tracefile,
    Operation,
    Report,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Phase {
    Warmup,
    Measured,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShimMetrics {
    pub schema_version: u32,
    pub measurement_backend: String,
    pub clock: String,
    pub wall_time_ns: u64,
    pub user_cpu_time_ns: u64,
    pub system_cpu_time_ns: u64,
    pub peak_rss_bytes: u64,
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Outcome {
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct SampleMetrics {
    pub wall_time_ns: u64,
    pub user_cpu_time_ns: u64,
    pub system_cpu_time_ns: u64,
    pub peak_rss_bytes: u64,
    pub output_bytes: u64,
    pub output_files: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct ArtifactRef {
    pub path: String,
    pub sha256: String,
    pub bytes: u64,
}

#[derive(Debug, Serialize)]
pub struct SampleArtifacts {
    pub stdout: ArtifactRef,
    pub stderr: ArtifactRef,
    pub output_tree: ArtifactRef,
}

#[derive(Debug, Serialize)]
pub struct RawSample {
    pub schema_version: u32,
    pub sample_id: String,
    pub suite_id: String,
    pub case_id: String,
    pub family: Family,
    pub sequence: usize,
    pub phase: Phase,
    pub suite_sha256: String,
    pub execution_manifest_sha256: String,
    pub fixture_tree_sha256: Option<String>,
    pub observed_image_sha256: String,
    pub observed_executable_sha256: String,
    pub measurement_tool_sha256: String,
    pub measurement_backend: String,
    pub clock: String,
    pub outcome: Outcome,
    pub outcome_matches_expected: bool,
    pub metrics: SampleMetrics,
    pub artifacts: SampleArtifacts,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct Distribution {
    pub minimum: u64,
    pub median: u64,
    pub maximum: u64,
}

#[derive(Debug, Eq, PartialEq, Serialize)]
pub struct CaseSummary {
    pub measured_samples: usize,
    pub wall_time_ns: Distribution,
    pub user_cpu_time_ns: Distribution,
    pub system_cpu_time_ns: Distribution,
    pub peak_rss_bytes: Distribution,
    pub output_bytes: u64,
    pub output_files: u64,
}

#[derive(Debug, Serialize)]
pub struct CaseResult {
    pub case_id: String,
    pub family: Family,
    pub warmup_samples: usize,
    pub measured_samples: usize,
    pub summary: CaseSummary,
}

#[derive(Debug, Serialize)]
pub struct GateStatus {
    pub status: &'static str,
    pub reason: &'static str,
}

#[derive(Debug, Serialize)]
pub struct CorrectnessGate {
    pub status: &'static str,
    pub reason: &'static str,
    pub required_evidence_scope: &'static str,
    pub evidence: Option<ArtifactRef>,
}

#[derive(Debug, Serialize)]
pub struct BaselineResult {
    pub schema_version: u32,
    pub result_id: String,
    pub recorded_at: String,
    pub status: &'static str,
    pub performance_gate: GateStatus,
    pub correctness_gate: CorrectnessGate,
    pub suite: ArtifactRef,
    pub execution_manifest: ArtifactRef,
    pub measurement_tool: ArtifactRef,
    pub raw_samples: Vec<ArtifactRef>,
    pub cases: Vec<CaseResult>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct TreeEntry {
    pub path: String,
    pub kind: TreeEntryKind,
    pub bytes: u64,
    pub sha256: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TreeEntryKind {
    File,
    Directory,
    Symlink,
}

#[derive(Debug, Serialize)]
pub struct OutputChange {
    pub path: String,
    pub status: OutputStatus,
    pub kind: TreeEntryKind,
    pub bytes: u64,
    pub sha256: Option<String>,
}

#[derive(Clone, Copy, Debug, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum OutputStatus {
    Created,
    Modified,
    Removed,
}
