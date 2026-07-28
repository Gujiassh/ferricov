use crate::differential::evidence::RunResult;
use crate::differential::{
    ComparisonRequest, Environment, EvidenceScope, ImplementationIdentity, Surface,
};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, Serialize)]
pub(super) struct ArtifactReference {
    pub(super) path: String,
    pub(super) sha256: String,
    pub(super) bytes: u64,
}

#[derive(Debug, Serialize)]
pub(super) struct ExecutionPolicy {
    pub(super) network: &'static str,
    pub(super) read_only: bool,
    pub(super) user: String,
    pub(super) working_directory: &'static str,
}

#[derive(Debug, Serialize)]
pub(super) struct OracleObservation {
    pub(super) schema_version: u32,
    pub(super) suite_id: String,
    pub(super) case_id: String,
    pub(super) evidence_scope: EvidenceScope,
    pub(super) upstream_commit: &'static str,
    pub(super) surface: Surface,
    pub(super) command: String,
    pub(super) arguments: Vec<String>,
    pub(super) fixture: Option<String>,
    pub(super) environment: Environment,
    pub(super) effective_environment_variables: BTreeMap<String, String>,
    pub(super) execution_manifest_sha256: String,
    pub(super) oracle_identity: ImplementationIdentity,
    pub(super) execution: ExecutionPolicy,
    pub(super) comparison_contract: Vec<ComparisonRequest>,
    pub(super) reference_run: RunResult,
    pub(super) status: &'static str,
    pub(super) product_compatibility_evidence: bool,
}

#[derive(Debug, Serialize)]
pub(super) struct CorrectnessBaseline {
    pub(super) schema_version: u32,
    pub(super) baseline_id: &'static str,
    pub(super) status: &'static str,
    pub(super) evidence_scope: &'static str,
    pub(super) upstream_release: &'static str,
    pub(super) upstream_commit: &'static str,
    pub(super) oracle_qualification_evidence: bool,
    pub(super) product_compatibility_evidence: bool,
    pub(super) case_contract: ArtifactReference,
    pub(super) execution_manifest: ArtifactReference,
    pub(super) launcher: ArtifactReference,
    pub(super) suites: Vec<ArtifactReference>,
    pub(super) case_count: usize,
    pub(super) cases: Vec<ArtifactReference>,
}
