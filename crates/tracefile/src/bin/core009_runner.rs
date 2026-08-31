//! Parent watchdog for one exact CORE-009 manifest tuple.
use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;
use sha2::{Digest, Sha256};

const WALL_LIMIT: Duration = Duration::from_secs(2);
const ADDRESS_SPACE_BYTES: u64 = 512 * 1024 * 1024;

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

fn arg(name: &str, index: usize) -> String {
    std::env::args().nth(index).unwrap_or_else(|| {
        eprintln!("missing {name}");
        std::process::exit(64)
    })
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

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let worker = PathBuf::from(arg("worker", 1));
    let mode = arg("mode", 2);
    let target = arg("target-id", 3);
    let case_id = arg("case-id", 4);
    let seed: u64 = arg("seed", 5).parse()?;
    let input_path = PathBuf::from(arg("input", 6));
    let artifact_path = PathBuf::from(arg("artifact", 7));
    let input = fs::read(&input_path)?;

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
    #[cfg(unix)]
    command
        .arg(&mode)
        .arg(&target)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let started = Instant::now();
    let mut child = command.spawn()?;
    child.stdin.take().expect("piped stdin").write_all(&input)?;
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
        thread::sleep(Duration::from_millis(10));
    };
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    child
        .stdout
        .take()
        .expect("piped stdout")
        .read_to_end(&mut stdout)?;
    child
        .stderr
        .take()
        .expect("piped stderr")
        .read_to_end(&mut stderr)?;
    #[cfg(unix)]
    use std::os::unix::process::ExitStatusExt;
    let outcome = if timed_out {
        Outcome::Timeout
    } else if let Some(code) = status.code() {
        if mode == "allocate" && code != 0 {
            Outcome::RssLimit
        } else {
            Outcome::Exit { code }
        }
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
    let artifact = Artifact {
        schema_version: 1,
        target_id: target,
        case_id,
        seed,
        input_sha256: format!("{:x}", Sha256::digest(&input)),
        outcome,
        stdout: String::from_utf8_lossy(&stdout).into_owned(),
        stderr: String::from_utf8_lossy(&stderr).into_owned(),
        wall_ms: started.elapsed().as_millis(),
        peak_rss_bytes: peak,
        address_space_limit_bytes: if cfg!(unix) {
            Some(ADDRESS_SPACE_BYTES)
        } else {
            None
        },
    };
    atomic_json(&artifact_path, &artifact)?;
    Ok(())
}
