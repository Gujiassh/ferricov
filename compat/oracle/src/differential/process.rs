//! Process execution, identity resolution, timeout, and Docker management.

use super::evidence::{self, CapturedRun, CleanupEvidence, TimeoutEvidence};
use super::{Case, IdentityKind, ImplementationIdentity, Launcher, Runtime};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::OsString;
use std::fs;
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};
use std::process::{Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;
use std::time::{Duration, Instant};
use tempfile::TempDir;

pub(crate) const DEFAULT_TIMEOUT_SECONDS: u64 = 20;
pub(crate) const MAX_TIMEOUT_SECONDS: u64 = 3_600;
const POLL_INTERVAL: Duration = Duration::from_millis(25);
const TERMINATION_GRACE: Duration = Duration::from_secs(1);
const CONTROL_COMMAND_TIMEOUT: Duration = Duration::from_secs(5);
const PIPE_DRAIN_TIMEOUT: Duration = Duration::from_secs(2);
static CONTAINER_SEQUENCE: AtomicU64 = AtomicU64::new(0);

struct ExecuteOutput {
    status: ExitStatus,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
    timeout: TimeoutEvidence,
    cleanup: CleanupEvidence,
}

enum PreparedRuntime {
    Local {
        executable: PathBuf,
    },
    Docker {
        image_id: String,
        user: Option<String>,
    },
}

pub(crate) struct PreparedRun {
    working_directory: TempDir,
    identity: ImplementationIdentity,
    runtime: PreparedRuntime,
}

impl PreparedRun {
    pub(crate) fn identity(&self) -> &ImplementationIdentity {
        &self.identity
    }
}

// ── Identity resolution ──────────────────────────────────────────────────

pub(crate) fn prepare(
    repository_root: &Path,
    launcher: &Launcher,
    case: &Case,
    image_id_cache: &mut BTreeMap<String, String>,
) -> Result<PreparedRun, Box<dyn Error>> {
    let working_directory = TempDir::new()?;
    if let Some(fixture) = &case.fixture {
        let fixture_root = resolve_fixture_root(repository_root, fixture)?;
        copy_directory_contents(&fixture_root, working_directory.path())?;
    }

    let (identity, runtime) = match &launcher.runtime {
        Runtime::Local => {
            let program = substitute(&launcher.program, case);
            let effective_path = launcher_path_override(launcher);
            let executable = resolve_executable_in_context(
                repository_root,
                &program,
                working_directory.path(),
                &effective_path,
            )?;
            let content = fs::read(&executable)?;
            (
                ImplementationIdentity {
                    kind: IdentityKind::LocalExecutable,
                    executable_sha256: format!("sha256:{:x}", Sha256::digest(content)),
                    container_image_sha256: None,
                },
                PreparedRuntime::Local { executable },
            )
        }
        Runtime::DockerImage { image } => {
            if launcher.environment.image != *image {
                return Err(format!(
                    "launcher {} runtime image must match its declared environment image",
                    launcher.name
                )
                .into());
            }
            let image_id = resolve_image_id(image, image_id_cache)?;
            let program = substitute(&launcher.program, case);
            let user = docker_user_argument(working_directory.path());
            let identity_container = unique_container_name("identity");
            let identity_arguments = docker_identity_arguments(
                &image_id,
                &identity_container,
                &program,
                &launcher.environment_variables,
                user.as_deref(),
                working_directory.path(),
            )?;
            let mut docker = Command::new(resolve_host_program("docker")?);
            let output = run_bounded_command(
                &mut docker,
                &identity_arguments,
                Duration::from_secs(effective_timeout_seconds(launcher)),
                "Docker identity",
            );
            let output = match output {
                Ok(output) => output,
                Err(error) => {
                    let cleanup = cleanup_docker_container(&identity_container)
                        .map(|_| "ok".to_owned())
                        .unwrap_or_else(|cleanup_error| cleanup_error.to_string());
                    return Err(
                        format!("Docker identity failed: {error}; cleanup={cleanup}").into(),
                    );
                }
            };
            let container_absent = verify_container_absent(&identity_container)?;
            if !container_absent {
                return Err(format!(
                    "Docker identity container {identity_container} survived execution"
                )
                .into());
            }
            if !output.status.success() {
                return Err(format!(
                    "failed to identify executable {program} in Docker image {image} (resolved to {image_id}): {}",
                    String::from_utf8_lossy(&output.stderr).trim()
                )
                .into());
            }
            let executable_hash = String::from_utf8(output.stdout)?
                .split_ascii_whitespace()
                .next()
                .ok_or("Docker executable identity is empty")?
                .to_owned();
            let executable_identity = format!("sha256:{executable_hash}");
            validate_sha256_identity(&executable_identity)?;
            (
                ImplementationIdentity {
                    kind: IdentityKind::DockerImage,
                    executable_sha256: executable_identity,
                    container_image_sha256: Some(image_id.clone()),
                },
                PreparedRuntime::Docker { image_id, user },
            )
        }
    };

    Ok(PreparedRun {
        working_directory,
        identity,
        runtime,
    })
}

// ── Capture ──────────────────────────────────────────────────────────────

pub(crate) struct CaptureOutcome {
    pub(crate) captured: CapturedRun,
    pub(crate) timeout: TimeoutEvidence,
    pub(crate) cleanup: CleanupEvidence,
}

pub(crate) fn capture(
    prepared: PreparedRun,
    launcher: &Launcher,
    case: &Case,
) -> Result<CaptureOutcome, Box<dyn Error>> {
    let program = substitute(&launcher.program, case);
    let arguments = launcher
        .arguments
        .iter()
        .map(|argument| substitute(argument, case))
        .collect::<Vec<_>>();

    let started = Instant::now();

    let timeout_seconds = effective_timeout_seconds(launcher);
    let output = match &prepared.runtime {
        PreparedRuntime::Local { executable } => {
            let mut cmd = Command::new(executable);
            cmd.args(&arguments);
            cmd.args(&case.arguments);
            cmd.env_clear();
            cmd.envs(&launcher.environment_variables);
            cmd.current_dir(prepared.working_directory.path());
            execute_with_timeout(&mut cmd, timeout_seconds)?
        }
        PreparedRuntime::Docker { image_id, user } => {
            let container_name = unique_container_name("capture");
            let config = DockerRunConfig {
                working_directory: prepared.working_directory.path(),
                image_id,
                container_name: &container_name,
                program: &program,
                launcher_arguments: &arguments,
                case_arguments: &case.arguments,
                environment_variables: &launcher.environment_variables,
                user: user.as_deref(),
            };
            execute_docker(&config, timeout_seconds)?
        }
    };

    let wall_seconds = started.elapsed().as_secs_f64();
    let file_tree = evidence::snapshot_tree(prepared.working_directory.path())?;

    Ok(CaptureOutcome {
        captured: CapturedRun {
            exit_status: output.status,
            stdout: output.stdout,
            stderr: output.stderr,
            file_tree,
            wall_seconds,
        },
        timeout: output.timeout,
        cleanup: output.cleanup,
    })
}

pub(crate) fn effective_timeout_seconds(launcher: &Launcher) -> u64 {
    launcher.timeout_seconds.unwrap_or(DEFAULT_TIMEOUT_SECONDS)
}

// ── PATH helpers ────────────────────────────────────────────────────────

fn launcher_path_override(launcher: &Launcher) -> Option<String> {
    launcher.environment_variables.get("PATH").cloned()
}

fn resolve_host_program(program: &str) -> Result<PathBuf, Box<dyn Error>> {
    let search_path = std::env::var_os("PATH").ok_or("host PATH is not defined")?;
    for directory in std::env::split_paths(&search_path) {
        let candidate = directory.join(program);
        if candidate.is_file() {
            return Ok(fs::canonicalize(candidate)?);
        }
    }
    Err(format!("required host control program not found in PATH: {program}").into())
}

fn run_bounded_command(
    command: &mut Command,
    arguments: &[OsString],
    timeout: Duration,
    label: &str,
) -> Result<std::process::Output, Box<dyn Error>> {
    command
        .args(arguments)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = command.spawn()?;
    let stdout_rx = spawn_drain(child.stdout.take().expect("stdout piped"));
    let stderr_rx = spawn_drain(child.stderr.take().expect("stderr piped"));
    let deadline = Instant::now() + timeout;
    let mut status = None;
    let mut stdout = None;
    let mut stderr = None;

    loop {
        poll_child(&mut child, &mut status)?;
        poll_drain(&stdout_rx, &mut stdout, &format!("{label} stdout"))?;
        poll_drain(&stderr_rx, &mut stderr, &format!("{label} stderr"))?;
        if status.is_some() && stdout.is_some() && stderr.is_some() {
            return Ok(std::process::Output {
                status: status.ok_or("control command exit status missing")?,
                stdout: stdout.take().ok_or("control command stdout missing")?,
                stderr: stderr.take().ok_or("control command stderr missing")?,
            });
        }
        if Instant::now() >= deadline {
            break;
        }
        thread::sleep(POLL_INTERVAL);
    }

    if status.is_none() {
        child
            .kill()
            .map_err(|error| format!("failed to kill timed-out {label}: {error}"))?;
        status = wait_until(&mut child, Instant::now() + TERMINATION_GRACE)?;
    }
    if status.is_none() {
        return Err(format!("{label} timed out and its process was not reaped").into());
    }
    if stdout.is_none() {
        let _ = receive_drain(stdout_rx, &format!("{label} stdout"))?;
    }
    if stderr.is_none() {
        let _ = receive_drain(stderr_rx, &format!("{label} stderr"))?;
    }
    Err(format!("{label} timed out after {:.3}s", timeout.as_secs_f64()).into())
}

// ── Timeout execution (local) ────────────────────────────────────────────

/// Execute a command with a timeout over process lifetime, stream drain, and
/// process-group cleanup.
fn execute_with_timeout(
    cmd: &mut Command,
    timeout_seconds: u64,
) -> Result<ExecuteOutput, Box<dyn Error>> {
    let program = cmd.get_program().to_os_string();
    let args: Vec<OsString> = cmd.get_args().map(OsString::from).collect();
    let envs: Vec<(OsString, OsString)> = cmd
        .get_envs()
        .filter_map(|(k, v)| Some((k.to_os_string(), v?.to_os_string())))
        .collect();
    let current_dir = cmd.get_current_dir().map(PathBuf::from);

    let mut wrapped = Command::new(resolve_host_program("setsid")?);
    wrapped.arg("-w");
    wrapped.arg(resolve_host_program("bwrap")?);
    wrapped.args([
        "--unshare-pid",
        "--as-pid-1",
        "--die-with-parent",
        "--bind",
        "/",
        "/",
        "--dev-bind",
        "/dev",
        "/dev",
        "--proc",
        "/proc",
    ]);
    if let Some(ref dir) = current_dir {
        wrapped.arg("--chdir");
        wrapped.arg(dir);
    }
    wrapped.arg("--");
    wrapped.arg(&program);
    wrapped.args(&args);
    wrapped.stdout(Stdio::piped());
    wrapped.stderr(Stdio::piped());
    wrapped.stdin(Stdio::null());
    wrapped.env_clear();
    for (k, v) in &envs {
        wrapped.env(k, v);
    }
    if let Some(ref dir) = current_dir {
        wrapped.current_dir(dir);
    }

    let mut child = wrapped.spawn()?;
    let pgid = child.id() as i32;
    let child_stdout = child.stdout.take().expect("stdout piped");
    let child_stderr = child.stderr.take().expect("stderr piped");

    // Drain streams concurrently on background threads.
    let stdout_rx = spawn_drain(child_stdout);
    let stderr_rx = spawn_drain(child_stderr);

    let deadline = Instant::now() + Duration::from_secs(timeout_seconds);
    let mut status = None;
    let mut stdout = None;
    let mut stderr = None;

    loop {
        poll_child(&mut child, &mut status)?;
        poll_drain(&stdout_rx, &mut stdout, "stdout")?;
        poll_drain(&stderr_rx, &mut stderr, "stderr")?;
        if status.is_some()
            && stdout.is_some()
            && stderr.is_some()
            && verify_process_group_empty(pgid)?
        {
            return Ok(ExecuteOutput {
                status: status.ok_or("no exit status")?,
                stdout: stdout.ok_or("stdout was not drained")?,
                stderr: stderr.ok_or("stderr was not drained")?,
                timeout: TimeoutEvidence {
                    applied_seconds: timeout_seconds,
                    expired: false,
                    termination_signal_sent: None,
                    escalation_signal_sent: None,
                },
                cleanup: CleanupEvidence {
                    direct_child_reaped: true,
                    process_group_empty: Some(true),
                    container_absent: None,
                },
            });
        }
        if Instant::now() >= deadline {
            break;
        }
        thread::sleep(POLL_INTERVAL);
    }

    let term_sent = signal_process_group(pgid, "TERM")?;
    wait_for_child_and_group(
        &mut child,
        &mut status,
        pgid,
        Instant::now() + TERMINATION_GRACE,
    )?;

    let mut kill_sent = false;
    if status.is_none() || !verify_process_group_empty(pgid)? {
        kill_sent = signal_process_group(pgid, "KILL")?;
        wait_for_child_and_group(
            &mut child,
            &mut status,
            pgid,
            Instant::now() + TERMINATION_GRACE,
        )?;
    }

    if status.is_none() {
        return Err(format!("direct child for process group {pgid} was not reaped").into());
    }
    if !verify_process_group_empty(pgid)? {
        return Err(format!("process group {pgid} survived timeout cleanup").into());
    }

    poll_drain(&stdout_rx, &mut stdout, "stdout")?;
    poll_drain(&stderr_rx, &mut stderr, "stderr")?;
    let stdout = match stdout {
        Some(bytes) => bytes,
        None => receive_drain(stdout_rx, "stdout")?,
    };
    let stderr = match stderr {
        Some(bytes) => bytes,
        None => receive_drain(stderr_rx, "stderr")?,
    };

    Ok(ExecuteOutput {
        status: status.ok_or("no exit status")?,
        stdout,
        stderr,
        timeout: TimeoutEvidence {
            applied_seconds: timeout_seconds,
            expired: true,
            termination_signal_sent: term_sent.then_some(15),
            escalation_signal_sent: kill_sent.then_some(9),
        },
        cleanup: CleanupEvidence {
            direct_child_reaped: true,
            process_group_empty: Some(true),
            container_absent: None,
        },
    })
}

fn drain_reader(mut reader: impl Read) -> io::Result<Vec<u8>> {
    let mut buf = Vec::new();
    reader.read_to_end(&mut buf)?;
    Ok(buf)
}

fn spawn_drain(reader: impl Read + Send + 'static) -> Receiver<io::Result<Vec<u8>>> {
    let (sender, receiver) = mpsc::channel();
    thread::spawn(move || {
        let _ = sender.send(drain_reader(reader));
    });
    receiver
}

fn receive_drain(
    receiver: Receiver<io::Result<Vec<u8>>>,
    stream: &str,
) -> Result<Vec<u8>, Box<dyn Error>> {
    receiver
        .recv_timeout(PIPE_DRAIN_TIMEOUT)
        .map_err(|error| format!("timed out draining {stream}: {error}"))?
        .map_err(|error| format!("failed draining {stream}: {error}").into())
}

fn poll_drain(
    receiver: &Receiver<io::Result<Vec<u8>>>,
    destination: &mut Option<Vec<u8>>,
    stream: &str,
) -> Result<(), Box<dyn Error>> {
    if destination.is_some() {
        return Ok(());
    }
    match receiver.try_recv() {
        Ok(result) => {
            *destination =
                Some(result.map_err(|error| format!("failed draining {stream}: {error}"))?);
            Ok(())
        }
        Err(TryRecvError::Empty) => Ok(()),
        Err(TryRecvError::Disconnected) => {
            Err(format!("{stream} drain worker disconnected without evidence").into())
        }
    }
}

fn poll_child(
    child: &mut std::process::Child,
    status: &mut Option<ExitStatus>,
) -> Result<(), Box<dyn Error>> {
    if status.is_none() {
        *status = child.try_wait()?;
    }
    Ok(())
}

fn wait_until(
    child: &mut std::process::Child,
    deadline: Instant,
) -> Result<Option<ExitStatus>, Box<dyn Error>> {
    loop {
        if let Some(status) = child.try_wait()? {
            return Ok(Some(status));
        }
        if Instant::now() >= deadline {
            return Ok(None);
        }
        thread::sleep(POLL_INTERVAL);
    }
}

fn wait_for_child_and_group(
    child: &mut std::process::Child,
    status: &mut Option<ExitStatus>,
    pgid: i32,
    deadline: Instant,
) -> Result<(), Box<dyn Error>> {
    loop {
        poll_child(child, status)?;
        if status.is_some() && verify_process_group_empty(pgid)? {
            return Ok(());
        }
        if Instant::now() >= deadline {
            return Ok(());
        }
        thread::sleep(POLL_INTERVAL);
    }
}

fn signal_process_group(pgid: i32, signal: &str) -> Result<bool, Box<dyn Error>> {
    let mut command = Command::new(resolve_host_program("kill")?);
    let output = run_bounded_command(
        &mut command,
        &[
            OsString::from(format!("-{signal}")),
            OsString::from("--"),
            OsString::from(format!("-{pgid}")),
        ],
        CONTROL_COMMAND_TIMEOUT,
        "process-group signal",
    )?;
    if output.status.success() {
        return Ok(true);
    }
    if verify_process_group_empty(pgid)? {
        return Ok(false);
    }
    Err(format!(
        "failed to send SIG{signal} to process group {pgid}: {}",
        String::from_utf8_lossy(&output.stderr).trim()
    )
    .into())
}

/// Verify the process group is empty. Returns error if the observer itself
/// fails (fail-closed).
fn verify_process_group_empty(pgid: i32) -> Result<bool, Box<dyn Error>> {
    verify_process_group_empty_with(pgid, &resolve_host_program("ps")?)
}

fn verify_process_group_empty_with(pgid: i32, observer: &Path) -> Result<bool, Box<dyn Error>> {
    let mut command = Command::new(observer);
    let output = run_bounded_command(
        &mut command,
        &[OsString::from("-eo"), OsString::from("pid=,pgid=")],
        CONTROL_COMMAND_TIMEOUT,
        "process-group observer",
    )?;
    if !output.status.success() {
        return Err(format!(
            "ps failed inspecting pgid {pgid}: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        )
        .into());
    }
    for line in String::from_utf8(output.stdout)?.lines() {
        let mut fields = line.split_ascii_whitespace();
        let pid = fields
            .next()
            .ok_or_else(|| format!("ps returned a row without pid: {line:?}"))?
            .parse::<u32>()
            .map_err(|error| format!("ps returned invalid pid data: {error}"))?;
        let observed_pgid = fields
            .next()
            .ok_or_else(|| format!("ps returned a row without pgid: {line:?}"))?
            .parse::<i32>()
            .map_err(|error| format!("ps returned invalid pgid data: {error}"))?;
        if fields.next().is_some() {
            return Err(format!("ps returned unexpected process data: {line:?}").into());
        }
        if observed_pgid == pgid && pid != std::process::id() {
            return Ok(false);
        }
    }
    Ok(true)
}

// ── Docker execution ─────────────────────────────────────────────────────

struct DockerRunConfig<'a> {
    working_directory: &'a Path,
    image_id: &'a str,
    container_name: &'a str,
    program: &'a str,
    launcher_arguments: &'a [String],
    case_arguments: &'a [String],
    environment_variables: &'a BTreeMap<String, String>,
    user: Option<&'a str>,
}

fn execute_docker(
    config: &DockerRunConfig<'_>,
    timeout_seconds: u64,
) -> Result<ExecuteOutput, Box<dyn Error>> {
    let docker_args = docker_capture_arguments(config)?;
    let container_name = config.container_name;

    let mut cmd = Command::new(resolve_host_program("docker")?);
    cmd.args(&docker_args);
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());
    cmd.stdin(Stdio::null());

    let mut child = cmd.spawn()?;
    let child_stdout = child.stdout.take().expect("stdout piped");
    let child_stderr = child.stderr.take().expect("stderr piped");

    let stdout_rx = spawn_drain(child_stdout);
    let stderr_rx = spawn_drain(child_stderr);
    let deadline = Instant::now() + Duration::from_secs(timeout_seconds);
    let mut status = None;
    let mut stdout = None;
    let mut stderr = None;

    loop {
        poll_child(&mut child, &mut status)?;
        poll_drain(&stdout_rx, &mut stdout, "Docker stdout")?;
        poll_drain(&stderr_rx, &mut stderr, "Docker stderr")?;
        if status.is_some() && stdout.is_some() && stderr.is_some() {
            if !verify_container_absent(container_name)? {
                cleanup_docker_container(container_name)?;
                return Err(format!(
                    "Docker container {container_name} remained after docker run completed"
                )
                .into());
            }
            return Ok(ExecuteOutput {
                status: status.ok_or("no Docker exit status")?,
                stdout: stdout.ok_or("Docker stdout was not drained")?,
                stderr: stderr.ok_or("Docker stderr was not drained")?,
                timeout: TimeoutEvidence {
                    applied_seconds: timeout_seconds,
                    expired: false,
                    termination_signal_sent: None,
                    escalation_signal_sent: None,
                },
                cleanup: CleanupEvidence {
                    direct_child_reaped: true,
                    process_group_empty: None,
                    container_absent: Some(true),
                },
            });
        }
        if Instant::now() >= deadline {
            break;
        }
        thread::sleep(POLL_INTERVAL);
    }

    let cleanup_result = cleanup_docker_container(container_name);
    let reap_deadline = Instant::now() + CONTROL_COMMAND_TIMEOUT;
    while status.is_none() && Instant::now() < reap_deadline {
        poll_child(&mut child, &mut status)?;
        poll_drain(&stdout_rx, &mut stdout, "Docker stdout")?;
        poll_drain(&stderr_rx, &mut stderr, "Docker stderr")?;
        thread::sleep(POLL_INTERVAL);
    }
    if status.is_none() {
        child
            .kill()
            .map_err(|error| format!("failed to kill timed-out Docker CLI: {error}"))?;
        status = wait_until(&mut child, Instant::now() + TERMINATION_GRACE)?;
    }
    let status = status.ok_or("timed-out Docker CLI was not reaped")?;
    let stdout = match stdout {
        Some(bytes) => bytes,
        None => receive_drain(stdout_rx, "Docker stdout")?,
    };
    let stderr = match stderr {
        Some(bytes) => bytes,
        None => receive_drain(stderr_rx, "Docker stderr")?,
    };
    cleanup_result?;

    Ok(ExecuteOutput {
        status,
        stdout,
        stderr,
        timeout: TimeoutEvidence {
            applied_seconds: timeout_seconds,
            expired: true,
            // Docker stop semantics depend on the image STOPSIGNAL and may
            // escalate internally. No Unix signal is claimed here.
            termination_signal_sent: None,
            escalation_signal_sent: None,
        },
        cleanup: CleanupEvidence {
            direct_child_reaped: true,
            process_group_empty: None,
            container_absent: Some(true),
        },
    })
}

fn cleanup_docker_container(name: &str) -> Result<(), Box<dyn Error>> {
    if verify_container_absent(name)? {
        return Ok(());
    }

    let stop_result = docker_stop_container(name);
    let absent_after_stop = verify_container_absent(name)?;
    let remove_result = if absent_after_stop {
        Ok(())
    } else {
        docker_remove_container_force(name)
    };
    let absent = verify_container_absent(name)?;

    if !absent {
        return Err(format!("Docker container {name} survived stop and force removal").into());
    }
    stop_result?;
    remove_result?;
    Ok(())
}

fn docker_stop_container(name: &str) -> Result<(), Box<dyn Error>> {
    run_docker_control(&["stop", "--time", "1", name], "docker stop")
}

fn docker_remove_container_force(name: &str) -> Result<(), Box<dyn Error>> {
    run_docker_control(&["rm", "-f", name], "docker rm -f")
}

fn run_docker_control(arguments: &[&str], label: &str) -> Result<(), Box<dyn Error>> {
    let mut command = Command::new(resolve_host_program("docker")?);
    let arguments = arguments.iter().map(OsString::from).collect::<Vec<_>>();
    let output = run_bounded_command(&mut command, &arguments, CONTROL_COMMAND_TIMEOUT, label)?;
    if output.status.success() {
        Ok(())
    } else {
        Err(format!(
            "{label} failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        )
        .into())
    }
}

/// Verify container is absent. Error on observer failure (fail-closed).
fn verify_container_absent(name: &str) -> Result<bool, Box<dyn Error>> {
    let mut command = Command::new(resolve_host_program("docker")?);
    let output = run_bounded_command(
        &mut command,
        &[
            OsString::from("ps"),
            OsString::from("-a"),
            OsString::from("--format"),
            OsString::from("{{.Names}}"),
        ],
        CONTROL_COMMAND_TIMEOUT,
        "docker container observer",
    )?;
    if !output.status.success() {
        return Err(format!(
            "docker ps failed verifying container {name} is absent: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        )
        .into());
    }
    Ok(!String::from_utf8(output.stdout)?
        .lines()
        .any(|container| container == name))
}

// ── Docker image-ID resolution ───────────────────────────────────────────

pub(crate) fn resolve_image_id(
    image: &str,
    cache: &mut BTreeMap<String, String>,
) -> Result<String, Box<dyn Error>> {
    if let Some(id) = cache.get(image) {
        return Ok(id.clone());
    }
    let mut command = Command::new(resolve_host_program("docker")?);
    let output = run_bounded_command(
        &mut command,
        &[
            OsString::from("image"),
            OsString::from("inspect"),
            OsString::from("--format"),
            OsString::from("{{.Id}}"),
            OsString::from(image),
        ],
        CONTROL_COMMAND_TIMEOUT,
        "docker image inspect",
    )?;
    if !output.status.success() {
        return Err(format!("failed to inspect Docker image {image}").into());
    }
    let id = String::from_utf8(output.stdout)?.trim().to_owned();
    validate_sha256_identity(&id)?;
    cache.insert(image.to_owned(), id.clone());
    Ok(id)
}

pub(crate) fn validate_sha256_identity(identity: &str) -> Result<(), Box<dyn Error>> {
    let Some(hex) = identity.strip_prefix("sha256:") else {
        return Err(format!("runtime identity is not SHA-256: {identity}").into());
    };
    if hex.len() != 64 || !hex.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(format!("runtime identity is not SHA-256: {identity}").into());
    }
    Ok(())
}

// ── Executable resolution ────────────────────────────────────────────────

pub(crate) fn resolve_executable_in_context(
    _repository_root: &Path,
    program: &str,
    working_directory: &Path,
    effective_path: &Option<String>,
) -> Result<PathBuf, Box<dyn Error>> {
    let path = Path::new(program);
    if path.components().count() > 1 {
        let resolved = if path.is_relative() {
            working_directory.join(path)
        } else {
            path.to_owned()
        };
        return Ok(fs::canonicalize(resolved)?);
    }
    let search_path = effective_path.clone().unwrap_or_else(|| {
        std::env::var_os("PATH")
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_default()
    });
    for directory in std::env::split_paths(&search_path) {
        let resolved_dir = if Path::new(&directory).is_relative() {
            working_directory.join(&directory)
        } else {
            directory
        };
        let candidate = resolved_dir.join(program);
        if candidate.is_file() {
            return Ok(fs::canonicalize(candidate)?);
        }
    }
    Err(format!("executable not found in PATH: {program}").into())
}

// ── Docker argument construction ─────────────────────────────────────────

fn append_docker_environment_arguments(
    arguments: &mut Vec<OsString>,
    variables: &BTreeMap<String, String>,
) -> Result<(), Box<dyn Error>> {
    for (key, value) in variables {
        if value.contains('\0') {
            return Err(format!("environment variable {key} contains a NUL byte").into());
        }
        arguments.push("--env".into());
        arguments.push(format!("{key}={value}").into());
    }
    Ok(())
}

fn docker_capture_arguments(cfg: &DockerRunConfig<'_>) -> Result<Vec<OsString>, Box<dyn Error>> {
    let mut arguments = vec![
        OsString::from("run"),
        OsString::from("--rm"),
        OsString::from("--name"),
        OsString::from(cfg.container_name),
        OsString::from("--network"),
        OsString::from("none"),
        OsString::from("--read-only"),
    ];
    if let Some(user) = cfg.user {
        arguments.push("--user".into());
        arguments.push(user.into());
    }
    append_docker_environment_arguments(&mut arguments, cfg.environment_variables)?;
    arguments.push("--volume".into());
    arguments.push(format!("{}:/work", cfg.working_directory.display()).into());
    arguments.extend([
        "--workdir".into(),
        "/work".into(),
        "--entrypoint".into(),
        cfg.program.into(),
        cfg.image_id.into(),
    ]);
    arguments.extend(cfg.launcher_arguments.iter().map(OsString::from));
    arguments.extend(cfg.case_arguments.iter().map(OsString::from));
    Ok(arguments)
}

fn docker_identity_arguments(
    image_id: &str,
    container_name: &str,
    program: &str,
    environment_variables: &BTreeMap<String, String>,
    user: Option<&str>,
    working_directory: &Path,
) -> Result<Vec<OsString>, Box<dyn Error>> {
    let mut arguments = vec![
        OsString::from("run"),
        OsString::from("--rm"),
        OsString::from("--name"),
        OsString::from(container_name),
        OsString::from("--network"),
        OsString::from("none"),
        OsString::from("--read-only"),
    ];
    if let Some(user) = user {
        arguments.push("--user".into());
        arguments.push(user.into());
    }
    append_docker_environment_arguments(&mut arguments, environment_variables)?;
    arguments.push("--volume".into());
    arguments.push(format!("{}:/work", working_directory.display()).into());
    arguments.extend([
        "--workdir".into(),
        "/work".into(),
        "--entrypoint".into(),
        "/bin/sh".into(),
        image_id.into(),
        "-c".into(),
        "p=$(command -v -- \"$1\") && test -n \"$p\" && /usr/bin/sha256sum \"$p\"".into(),
        "/bin/sh".into(),
        program.into(),
    ]);
    Ok(arguments)
}

#[cfg(unix)]
fn docker_user_argument(working_directory: &Path) -> Option<String> {
    use std::os::unix::fs::MetadataExt;
    fs::metadata(working_directory)
        .ok()
        .map(|metadata| format!("{}:{}", metadata.uid(), metadata.gid()))
}

#[cfg(not(unix))]
fn docker_user_argument(_working_directory: &Path) -> Option<String> {
    None
}

// ── Placeholder substitution ─────────────────────────────────────────────

pub(crate) fn substitute(template: &str, case: &Case) -> String {
    template
        .replace("{command}", &case.command)
        .replace("{fixture}", ".")
}

// ── Fixture helpers ──────────────────────────────────────────────────────

fn resolve_fixture_root(repository_root: &Path, fixture: &str) -> Result<PathBuf, Box<dyn Error>> {
    let fixture_path = Path::new(fixture);
    if fixture_path.as_os_str().is_empty()
        || fixture_path.components().any(|component| {
            matches!(
                component,
                Component::ParentDir | Component::RootDir | Component::Prefix(_)
            )
        })
    {
        return Err(format!("fixture path must stay relative to the repository: {fixture}").into());
    }
    let repository_root = fs::canonicalize(repository_root)?;
    let fixture_root = fs::canonicalize(repository_root.join(fixture_path))?;
    if !fixture_root.starts_with(&repository_root) || !fixture_root.is_dir() {
        return Err(format!(
            "fixture path is not a repository directory: {}",
            fixture_root.display()
        )
        .into());
    }
    Ok(fixture_root)
}

fn unique_container_name(purpose: &str) -> String {
    let sequence = CONTAINER_SEQUENCE.fetch_add(1, Ordering::Relaxed);
    format!("ferricov-{}-{purpose}-{sequence}", std::process::id())
}

fn copy_directory_contents(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    for entry in fs::read_dir(source)? {
        let entry = entry?;
        copy_entry(&entry.path(), &destination.join(entry.file_name()))?;
    }
    Ok(())
}

fn copy_entry(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    let metadata = fs::symlink_metadata(source)?;
    let file_type = metadata.file_type();
    if file_type.is_file() {
        fs::copy(source, destination)?;
    } else if file_type.is_dir() {
        fs::create_dir(destination)?;
        copy_directory_contents(source, destination)?;
    } else if file_type.is_symlink() {
        copy_symlink(source, destination)?;
    } else {
        return Err(format!("unsupported fixture entry: {}", source.display()).into());
    }
    Ok(())
}

#[cfg(unix)]
fn copy_symlink(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    std::os::unix::fs::symlink(fs::read_link(source)?, destination)?;
    Ok(())
}

#[cfg(windows)]
fn copy_symlink(source: &Path, destination: &Path) -> Result<(), Box<dyn Error>> {
    let target = fs::read_link(source)?;
    if source.is_dir() {
        std::os::windows::fs::symlink_dir(target, destination)?;
    } else {
        std::os::windows::fs::symlink_file(target, destination)?;
    }
    Ok(())
}

// ── Tests ────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    #[cfg(unix)]
    fn make_executable(path: &Path) {
        use std::os::unix::fs::PermissionsExt;
        let mut permissions = fs::metadata(path).unwrap().permissions();
        permissions.set_mode(0o755);
        fs::set_permissions(path, permissions).unwrap();
    }

    fn argument_strings(args: Vec<OsString>) -> Vec<String> {
        args.into_iter()
            .map(|a| a.into_string().expect("UTF-8"))
            .collect()
    }

    #[test]
    fn docker_capture_arguments_use_immutable_image_id() {
        let vars = BTreeMap::from([("POSIXLY_CORRECT".to_owned(), "1".to_owned())]);
        let args = argument_strings(
            docker_capture_arguments(&DockerRunConfig {
                working_directory: Path::new("/tmp/w"),
                image_id: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                container_name: "ferricov-test",
                program: "lcov",
                launcher_arguments: &["--launcher-value".to_owned()],
                case_arguments: &["--hel".to_owned()],
                environment_variables: &vars,
                user: Some("1000:1001"),
            })
            .unwrap(),
        );
        assert_eq!(&args[0..4], ["run", "--rm", "--name", "ferricov-test"]);
        assert!(args.windows(2).any(|pair| pair == ["--network", "none"]));
        assert!(args.contains(&"--read-only".to_owned()));
        assert!(args.windows(2).any(|pair| pair == ["--user", "1000:1001"]));
        let img_pos = args.iter().position(|v| v == "--entrypoint").unwrap() + 2;
        assert_eq!(
            args[img_pos],
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        );
    }

    #[test]
    fn docker_identity_mounts_workdir() {
        let workdir = tempfile::TempDir::new().unwrap();
        let vars = BTreeMap::new();
        let args = argument_strings(
            docker_identity_arguments(
                "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "ferricov-identity-test",
                "lcov",
                &vars,
                Some("1000:1001"),
                workdir.path(),
            )
            .unwrap(),
        );
        assert!(args.contains(&"--user".to_owned()));
        assert!(args.contains(&"1000:1001".to_owned()));
        assert!(args.contains(&"--volume".to_owned()));
        assert!(args.contains(&"--workdir".to_owned()));
        assert!(args.contains(&"--read-only".to_owned()));
    }

    #[test]
    fn identity_and_capture_use_same_image_id() {
        let image_id = "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
        let vars = BTreeMap::from([("POSIXLY_CORRECT".to_owned(), "1".to_owned())]);
        let workdir = tempfile::TempDir::new().unwrap();

        let id_args = argument_strings(
            docker_identity_arguments(
                image_id,
                "identity-test",
                "lcov",
                &vars,
                None,
                workdir.path(),
            )
            .unwrap(),
        );
        let cap_args = argument_strings(
            docker_capture_arguments(&DockerRunConfig {
                working_directory: workdir.path(),
                image_id,
                container_name: "test",
                program: "lcov",
                launcher_arguments: &[],
                case_arguments: &[],
                environment_variables: &vars,
                user: None,
            })
            .unwrap(),
        );
        let id_img = id_args.iter().find(|v| v.starts_with("sha256:")).unwrap();
        let cap_img = cap_args.iter().find(|v| v.starts_with("sha256:")).unwrap();
        assert_eq!(id_img, image_id);
        assert_eq!(cap_img, image_id);
    }

    #[test]
    fn substitutes_case_placeholders() {
        let case = Case {
            id: "tc".to_owned(),
            surface: super::super::Surface::Cli,
            command: "lcov; echo unsafe".to_owned(),
            arguments: vec![],
            fixture: Some("f".to_owned()),
            comparisons: vec![],
        };
        assert_eq!(
            substitute("t={command} f={fixture}", &case),
            "t=lcov; echo unsafe f=."
        );
    }

    #[test]
    fn copies_fixture_tree_preserving_symlinks() {
        let src = tempfile::TempDir::new().unwrap();
        let dst = tempfile::TempDir::new().unwrap();
        fs::create_dir(src.path().join("nested")).unwrap();
        fs::write(src.path().join("nested/file.txt"), b"fixture").unwrap();
        #[cfg(unix)]
        std::os::unix::fs::symlink("nested/file.txt", src.path().join("link.txt")).unwrap();
        copy_directory_contents(src.path(), dst.path()).unwrap();
        assert_eq!(
            fs::read(dst.path().join("nested/file.txt")).unwrap(),
            b"fixture"
        );
        #[cfg(unix)]
        assert_eq!(
            fs::read_link(dst.path().join("link.txt")).unwrap(),
            PathBuf::from("nested/file.txt")
        );
    }

    #[test]
    fn default_bound_yields_complete_evidence() {
        let mut cmd = Command::new("true");
        let output = execute_with_timeout(&mut cmd, DEFAULT_TIMEOUT_SECONDS).unwrap();
        assert!(output.status.success());
        assert!(output.stdout.is_empty());
        assert!(output.stderr.is_empty());
        assert_eq!(output.timeout.applied_seconds, DEFAULT_TIMEOUT_SECONDS);
        assert!(!output.timeout.expired);
        assert!(output.cleanup.direct_child_reaped);
        assert_eq!(output.cleanup.process_group_empty, Some(true));
    }

    #[test]
    fn timeout_not_expired_yields_evidence() {
        let mut cmd = Command::new("true");
        let output = execute_with_timeout(&mut cmd, 5).unwrap();
        let t = output.timeout;
        assert_eq!(t.applied_seconds, 5);
        assert!(!t.expired);
        assert!(t.termination_signal_sent.is_none());
        let c = output.cleanup;
        assert!(c.direct_child_reaped);
        assert_eq!(c.process_group_empty, Some(true));
    }

    #[test]
    fn timeout_expires_yields_evidence() {
        let mut cmd = Command::new("sleep");
        cmd.arg("10");
        let started = Instant::now();
        let output = execute_with_timeout(&mut cmd, 1).unwrap();
        assert!(started.elapsed() < Duration::from_secs(4));
        let t = output.timeout;
        assert!(t.expired);
        assert_eq!(t.termination_signal_sent, Some(15));
        let c = output.cleanup;
        assert!(c.direct_child_reaped);
        assert!(c.process_group_empty.unwrap());
    }

    #[test]
    fn timeout_drains_large_stdout_and_stderr_without_deadlock() {
        let mut cmd = Command::new("sh");
        cmd.arg("-c").arg(
            "head -c 2000000 /dev/zero | tr '\\0' 'x'; \
             head -c 2000000 /dev/zero | tr '\\0' 'y' >&2; echo DONE",
        );
        let output = execute_with_timeout(&mut cmd, 10).unwrap();
        assert!(output.stdout.len() > 1_000_000, "must drain >1 MiB stdout");
        assert!(output.stderr.len() > 1_000_000, "must drain >1 MiB stderr");
        assert!(output.stdout.ends_with(b"DONE\n"));
        assert!(!output.timeout.expired);
        assert!(output.cleanup.process_group_empty.unwrap());
    }

    #[test]
    fn local_identity_resolves_against_effective_path() {
        let workdir = tempfile::TempDir::new().unwrap();
        let exec =
            resolve_executable_in_context(Path::new("."), "true", workdir.path(), &None).unwrap();
        assert!(exec.to_str().unwrap().contains("true"));
    }

    #[test]
    fn local_identity_uses_path_override() {
        let workdir = tempfile::TempDir::new().unwrap();
        #[cfg(unix)]
        {
            let script = workdir.path().join("ferricov-test-helper");
            fs::write(&script, "#!/bin/sh\ntrue\n").unwrap();
            make_executable(&script);
            let override_path = Some(workdir.path().to_string_lossy().to_string());
            let exec = resolve_executable_in_context(
                Path::new("."),
                "ferricov-test-helper",
                workdir.path(),
                &override_path,
            )
            .unwrap();
            assert!(exec.to_str().unwrap().contains("ferricov-test-helper"));
        }
    }

    #[test]
    fn local_identity_and_capture_share_fixture_path_and_workdir() {
        let repository = tempfile::TempDir::new().unwrap();
        let fixture = repository.path().join("fixture");
        fs::create_dir(&fixture).unwrap();
        let tool = fixture.join("tool");
        fs::write(&tool, "#!/bin/sh\nprintf fixture-tool-ok\n").unwrap();
        #[cfg(unix)]
        make_executable(&tool);

        let launcher = Launcher {
            schema_version: 1,
            name: "fixture-path".to_owned(),
            program: "{command}".to_owned(),
            arguments: Vec::new(),
            environment_variables: BTreeMap::from([("PATH".to_owned(), ".".to_owned())]),
            timeout_seconds: Some(5),
            runtime: Runtime::Local,
            environment: super::super::Environment {
                image: "local-test".to_owned(),
                operating_system: "linux".to_owned(),
                architecture: std::env::consts::ARCH.to_owned(),
                compiler: None,
                cpu: None,
            },
        };
        let case = Case {
            id: "fixture-path".to_owned(),
            surface: super::super::Surface::Cli,
            command: "tool".to_owned(),
            arguments: Vec::new(),
            fixture: Some("fixture".to_owned()),
            comparisons: Vec::new(),
        };
        let mut cache = BTreeMap::new();
        let prepared = prepare(repository.path(), &launcher, &case, &mut cache).unwrap();
        assert_eq!(
            prepared.identity().executable_sha256,
            format!("sha256:{:x}", Sha256::digest(fs::read(&tool).unwrap()))
        );
        let outcome = capture(prepared, &launcher, &case).unwrap();
        assert_eq!(outcome.captured.stdout, b"fixture-tool-ok");
        assert!(!outcome.timeout.expired);
    }

    #[test]
    fn fixture_root_rejects_absolute_and_parent_traversal() {
        let repository = tempfile::TempDir::new().unwrap();
        let outside = tempfile::TempDir::new().unwrap();
        let mut cache = BTreeMap::new();
        let launcher = Launcher {
            schema_version: 1,
            name: "fixture-path".to_owned(),
            program: "{command}".to_owned(),
            arguments: Vec::new(),
            environment_variables: BTreeMap::new(),
            timeout_seconds: Some(5),
            runtime: Runtime::Local,
            environment: super::super::Environment {
                image: "local-test".to_owned(),
                operating_system: "linux".to_owned(),
                architecture: std::env::consts::ARCH.to_owned(),
                compiler: None,
                cpu: None,
            },
        };
        for fixture in [
            "../outside".to_owned(),
            outside.path().to_string_lossy().into_owned(),
        ] {
            let case = Case {
                id: "fixture-path".to_owned(),
                surface: super::super::Surface::Cli,
                command: "true".to_owned(),
                arguments: Vec::new(),
                fixture: Some(fixture),
                comparisons: Vec::new(),
            };
            let error = match prepare(repository.path(), &launcher, &case, &mut cache) {
                Ok(_) => panic!("fixture traversal unexpectedly prepared"),
                Err(error) => error,
            };
            assert!(
                error
                    .to_string()
                    .contains("fixture path must stay relative")
            );
        }
    }

    #[test]
    fn fail_closed_cleanup_errors_on_observer_failure() {
        let directory = tempfile::TempDir::new().unwrap();
        let observer = directory.path().join("broken-ps");
        fs::write(&observer, "#!/bin/sh\nexit 7\n").unwrap();
        #[cfg(unix)]
        make_executable(&observer);
        let error = verify_process_group_empty_with(999_999, &observer).unwrap_err();
        assert!(error.to_string().contains("ps failed inspecting pgid"));
    }

    #[test]
    fn bounded_command_reaps_a_hung_control_process() {
        let mut command = Command::new("sleep");
        let started = Instant::now();
        let error = run_bounded_command(
            &mut command,
            &[OsString::from("30")],
            Duration::from_millis(100),
            "hung-control",
        )
        .unwrap_err();
        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(error.to_string().contains("timed out"));
    }

    #[test]
    fn pid_namespace_removes_a_setsid_descendant() {
        let directory = tempfile::TempDir::new().unwrap();
        let helper = directory.path().join("escaped-descendant-helper");
        let ready = directory.path().join("ready");
        fs::write(&helper, "#!/bin/sh\nprintf x > \"$1\"\n/usr/bin/sleep 30\n").unwrap();
        #[cfg(unix)]
        make_executable(&helper);

        let mut command = Command::new("/bin/sh");
        command.current_dir(directory.path()).arg("-c").arg(format!(
            "/usr/bin/setsid '{}' '{}' & while [ ! -s '{}' ]; do :; done",
            helper.display(),
            ready.display(),
            ready.display()
        ));
        let started = Instant::now();
        let output = execute_with_timeout(&mut command, 5).unwrap();
        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(!output.timeout.expired);
        assert!(!process_cmdline_contains(&helper));
    }

    #[test]
    fn timeout_removes_a_setsid_descendant_within_bound() {
        let directory = tempfile::TempDir::new().unwrap();
        let helper = directory.path().join("timed-out-descendant-helper");
        let ready = directory.path().join("ready");
        fs::write(&helper, "#!/bin/sh\nprintf x > \"$1\"\n/usr/bin/sleep 30\n").unwrap();
        #[cfg(unix)]
        make_executable(&helper);

        let mut command = Command::new("/bin/sh");
        command.current_dir(directory.path()).arg("-c").arg(format!(
            "/usr/bin/setsid '{}' '{}' & while [ ! -s '{}' ]; do :; done; /usr/bin/sleep 30",
            helper.display(),
            ready.display(),
            ready.display()
        ));
        let started = Instant::now();
        let output = execute_with_timeout(&mut command, 1).unwrap();
        assert!(started.elapsed() < Duration::from_secs(4));
        assert!(output.timeout.expired);
        assert!(!process_cmdline_contains(&helper));
    }

    fn process_cmdline_contains(needle: &Path) -> bool {
        let needle = needle.as_os_str().as_encoded_bytes();
        fs::read_dir("/proc")
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .bytes()
                    .all(|byte| byte.is_ascii_digit())
            })
            .filter_map(|entry| fs::read(entry.path().join("cmdline")).ok())
            .any(|cmdline| cmdline.windows(needle.len()).any(|window| window == needle))
    }

    /// Prove image-ID caching works: second resolution uses cache, no re-inspect.
    #[test]
    fn image_id_is_cached_and_reused() {
        // We can't test actual Docker inspect in unit tests, but we can test
        // the cache behaviour: if a key exists, return cached without calling
        // docker inspect. Test by pre-populating the cache.
        let mut cache: BTreeMap<String, String> = BTreeMap::new();
        cache.insert(
            "test-image:v1".to_owned(),
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".to_owned(),
        );
        let id = resolve_image_id("test-image:v1", &mut cache).unwrap();
        assert_eq!(
            id,
            "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        );
        // Second call returns same.
        let id2 = resolve_image_id("test-image:v1", &mut cache).unwrap();
        assert_eq!(id, id2);
    }
}
