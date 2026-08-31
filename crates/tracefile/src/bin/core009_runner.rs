//! Parent watchdog for one exact CORE-009 manifest tuple.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    thread,
    time::{Duration, Instant},
};

const WALL_LIMIT: Duration = Duration::from_secs(2);
const ADDRESS_SPACE_BYTES: u64 = 512 * 1024 * 1024;

#[derive(Deserialize)]
struct Manifest {
    entries: Vec<Entry>,
}
#[derive(Deserialize)]
struct Entry {
    case_id: String,
    sha256: String,
    targets: Vec<String>,
    derived_seeds: std::collections::BTreeMap<String, u64>,
}
#[derive(Serialize)]
struct Artifact {
    schema_version: u8,
    target_id: String,
    case_id: String,
    seed: u64,
    input_sha256: String,
    outcome: Outcome,
    stdout: String,
    stderr: String,
    wall_ms: u128,
    peak_rss_bytes: Option<u64>,
    address_space_limit_bytes: Option<u64>,
}
#[derive(Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
enum Outcome {
    Exit { code: i32 },
    Signal { signal: i32 },
    Timeout,
    RssLimit,
}

fn reject(kind: &str, detail: impl std::fmt::Display) -> ! {
    eprintln!("CORE009_RUNNER_REJECT kind={kind} detail={detail}");
    std::process::exit(64)
}
fn arg(name: &str, index: usize) -> String {
    std::env::args()
        .nth(index)
        .unwrap_or_else(|| reject("missing_argument", name))
}
fn atomic_json(path: &Path, value: &Artifact) -> Result<(), Box<dyn std::error::Error>> {
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)?;
    let mut temp = tempfile::NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(&mut temp, value)?;
    temp.write_all(b"\n")?;
    temp.as_file().sync_all()?;
    temp.persist(path)?;
    Ok(())
}
#[cfg(unix)]
fn peak_rss(pid: u32) -> Option<u64> {
    let status = fs::read_to_string(format!("/proc/{pid}/status")).ok()?;
    status
        .lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")
                .or_else(|| line.strip_prefix("VmRSS:"))
        })
        .and_then(|value| value.split_whitespace().next()?.parse::<u64>().ok())
        .map(|kb| kb * 1024)
}
#[cfg(not(unix))]
fn peak_rss(_: u32) -> Option<u64> {
    None
}
fn drain(mut pipe: impl Read + Send + 'static) -> thread::JoinHandle<std::io::Result<Vec<u8>>> {
    thread::spawn(move || {
        let mut bytes = Vec::new();
        pipe.read_to_end(&mut bytes)?;
        Ok(bytes)
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let worker = PathBuf::from(arg("worker", 1));
    let mode = arg("mode", 2);
    let target = arg("target-id", 3);
    let case_id = arg("case-id", 4);
    let seed: u64 = arg("seed", 5)
        .parse()
        .unwrap_or_else(|e| reject("invalid_seed", e));
    let input = fs::read(arg("input", 6))?;
    let artifact_path = PathBuf::from(arg("artifact", 7));
    let manifest: Manifest = serde_json::from_slice(&fs::read(arg("manifest", 8))?)?;
    let input_hash = format!("{:x}", Sha256::digest(&input));
    let matches: Vec<_> = manifest
        .entries
        .iter()
        .filter(|entry| {
            entry.case_id == case_id && entry.targets.iter().any(|candidate| candidate == &target)
        })
        .collect();
    if matches.len() != 1 {
        reject(
            if matches.is_empty() {
                "unknown_manifest_tuple"
            } else {
                "ambiguous_manifest_tuple"
            },
            format!("{target}/{case_id}"),
        )
    }
    let entry = matches[0];
    if entry.sha256 != input_hash {
        reject(
            "input_hash_mismatch",
            format!("expected={} observed={input_hash}", entry.sha256),
        )
    }
    let expected = entry
        .derived_seeds
        .get(&target)
        .unwrap_or_else(|| reject("missing_derived_seed", &target));
    if *expected != seed {
        reject(
            "seed_mismatch",
            format!("expected={expected} observed={seed}"),
        )
    }
    #[cfg(unix)]
    let mut command = {
        let mut c = Command::new("prlimit");
        c.arg(format!("--as={ADDRESS_SPACE_BYTES}:{ADDRESS_SPACE_BYTES}"))
            .arg("--")
            .arg(&worker);
        c
    };
    #[cfg(not(unix))]
    let mut command = Command::new(&worker);
    command
        .arg(&mode)
        .arg(&target)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let started = Instant::now();
    let mut child = command.spawn()?;
    child.stdin.take().expect("piped stdin").write_all(&input)?;
    let stdout = drain(child.stdout.take().expect("piped stdout"));
    let stderr = drain(child.stderr.take().expect("piped stderr"));
    let mut peak = None;
    let mut timed_out = false;
    let status = loop {
        peak = peak.max(peak_rss(child.id()));
        if let Some(status) = child.try_wait()? {
            break status;
        }
        if started.elapsed() >= WALL_LIMIT {
            timed_out = true;
            child.kill()?;
            break child.wait()?;
        }
        thread::sleep(Duration::from_millis(10))
    };
    let stdout = stdout.join().map_err(|_| "stdout drain panicked")??;
    let stderr = stderr.join().map_err(|_| "stderr drain panicked")??;
    #[cfg(unix)]
    use std::os::unix::process::ExitStatusExt;
    let resource_observed = peak.is_some_and(|value| value >= ADDRESS_SPACE_BYTES * 9 / 10)
        || stderr
            .windows(17)
            .any(|window| window == b"memory allocation");
    let outcome = if timed_out {
        Outcome::Timeout
    } else if resource_observed {
        Outcome::RssLimit
    } else if let Some(code) = status.code() {
        Outcome::Exit { code }
    } else {
        #[cfg(unix)]
        {
            Outcome::Signal {
                signal: status.signal().unwrap_or_default(),
            }
        }
        #[cfg(not(unix))]
        {
            Outcome::Signal { signal: 0 }
        }
    };
    atomic_json(
        &artifact_path,
        &Artifact {
            schema_version: 1,
            target_id: target,
            case_id,
            seed,
            input_sha256: input_hash,
            outcome,
            stdout: String::from_utf8_lossy(&stdout).into_owned(),
            stderr: String::from_utf8_lossy(&stderr).into_owned(),
            wall_ms: started.elapsed().as_millis(),
            peak_rss_bytes: peak,
            address_space_limit_bytes: cfg!(unix).then_some(ADDRESS_SPACE_BYTES),
        },
    )?;
    Ok(())
}
