#!/usr/bin/env python3
"""Transactionally minimize, replay, and retain one real libFuzzer finding."""
from __future__ import annotations
import argparse, contextlib, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time

def sha(path: pathlib.Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def outcome(result: subprocess.CompletedProcess) -> tuple[str, int]:
    return ("signal", -result.returncode) if result.returncode < 0 else ("exit", result.returncode)

def _owner_alive(pid: int) -> bool:
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return True

@contextlib.contextmanager
def exclusive_lock(path: pathlib.Path, stale_after: int = 600):
    for attempt in range(2):
        try: fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); break
        except FileExistsError as exc:
            try:
                facts=json.loads(path.read_text(encoding="utf-8")); pid=int(facts["pid"]); created=float(facts["created"])
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                pid,created=-1,0
            if attempt or (_owner_alive(pid) and time.time()-created <= stale_after):
                raise RuntimeError(f"retention lock held: {path}") from exc
            with contextlib.suppress(FileNotFoundError): path.unlink()
    try:
        os.write(fd, (json.dumps({"pid":os.getpid(),"created":time.time()})+"\n").encode()); os.close(fd); yield
    finally:
        with contextlib.suppress(FileNotFoundError): path.unlink()

def run(command: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

def retain(root: pathlib.Path, target: str, case_id: str, raw: pathlib.Path,
           runtime_manifest: pathlib.Path, origins: list[str]) -> pathlib.Path:
    fuzz = root / "fuzz"; manifest_path = fuzz / "corpus/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tuples = [(e, e["derived_seeds"][target]) for e in manifest["entries"]
              if e["case_id"] == case_id and target in e["derived_seeds"]]
    if len(tuples) != 1: raise ValueError("target/case must resolve to exactly one manifest tuple")
    _, seed = tuples[0]
    if not raw.is_file(): raise ValueError("raw finding is absent")
    runtime = json.loads(runtime_manifest.read_text(encoding="utf-8"))
    target_bin = target.lower().replace("-", "_")
    destination = fuzz / "corpus" / target_bin
    destination.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(fuzz / "corpus/.retain.lock"), tempfile.TemporaryDirectory(dir=fuzz) as temp:
        stage = pathlib.Path(temp); staged_raw = stage / f"{case_id}.raw"; minimized = stage / f"{case_id}.minimized"
        shutil.copyfile(raw, staged_raw)
        common = [f"-seed={seed}", "-timeout=2", "-rss_limit_mb=512", "-max_len=1048576"]
        cargo=os.environ.get("FERRICOV_CARGO_FUZZ","cargo")
        tmin = run([cargo, "+nightly", "fuzz", "tmin", target_bin, str(staged_raw), "--output", str(minimized), "--", *common])
        if tmin.returncode == 0 or not minimized.is_file(): raise RuntimeError("tmin did not reproduce a failing outcome")
        replay = run([cargo, "+nightly", "fuzz", "run", target_bin, str(minimized), "--", *common, "-runs=1"])
        if replay.returncode == 0 or outcome(replay) != outcome(tmin): raise RuntimeError("plain replay outcome drift")
        sidecar = pathlib.Path(str(minimized) + ".json")
        value = {"schema_version":1,"target_id":target,"case_id":case_id,"seed":seed,
            "raw_sha256":sha(staged_raw),"minimized_sha256":sha(minimized),"raw_artifact":staged_raw.name,
            "first_failing_operation":"decoded by retained target replay","semantic_snapshots":{"replay_input_sha256":sha(minimized)},
            "process":{"exit_code":replay.returncode if replay.returncode >= 0 else None,
                       "signal":-replay.returncode if replay.returncode < 0 else None,"timed_out":False,
                       "stdout":replay.stdout.decode("utf-8","replace"),"stderr":replay.stderr.decode("utf-8","replace")},
            "runtime_manifest":runtime,"origin_ids":sorted(set(origins + [target]))}
        sidecar.write_text(json.dumps(value, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        validator = run(["python3", str(fuzz/"scripts/validate_artifacts.py"), "--sidecar", str(sidecar)])
        if validator.returncode: raise RuntimeError("staged sidecar failed schema validation")
        installs = [(staged_raw,destination/staged_raw.name),(minimized,destination/minimized.name),(sidecar,destination/sidecar.name)]
        if any(dst.exists() for _,dst in installs): raise RuntimeError("retained destination already exists")
        installed=[]
        try:
            for src,dst in installs: os.replace(src,dst); installed.append(dst)
            failure={"case_id":case_id,"target_id":target,"seed":seed,"raw_sha256":value["raw_sha256"],
                     "minimized_sha256":value["minimized_sha256"],"sidecar":str(installs[-1][1].relative_to(fuzz)).replace("\\","/")}
            manifest["known_failures"] = sorted(manifest["known_failures"]+[failure], key=lambda x:(x["target_id"],x["case_id"]))
            tmp=manifest_path.with_suffix(".json.tmp"); tmp.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8"); os.replace(tmp,manifest_path)
        except BaseException:
            for path in reversed(installed):
                with contextlib.suppress(FileNotFoundError): path.unlink()
            raise
    return destination / f"{case_id}.minimized.json"

def main():
    p=argparse.ArgumentParser(); p.add_argument("target"); p.add_argument("case_id"); p.add_argument("raw",type=pathlib.Path)
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[2]); p.add_argument("--runtime-manifest",type=pathlib.Path,required=True); p.add_argument("--origin",action="append",default=[])
    a=p.parse_args(); print(retain(a.root,a.target,a.case_id,a.raw,a.runtime_manifest,a.origin))
if __name__ == "__main__": main()
