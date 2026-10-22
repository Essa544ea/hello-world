"""Shared experiment plumbing: provenance + parallel map."""
import json, os, platform, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def provenance(**extra):
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "src", "csrc"], capture_output=True, text=True, cwd=ROOT).stdout.strip())
    cpu = ""
    try:
        cpu = next(l.split(":")[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
    except Exception:
        pass
    return {"git": git, "dirty_tree": dirty, "python": platform.python_version(), "cpu": cpu,
            "ncpu": os.cpu_count(), "started": time.strftime("%Y-%m-%d %H:%M:%S"), **extra}


def save(name, obj):
    (ROOT / "results").mkdir(exist_ok=True)
    p = ROOT / "results" / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1))
    return p
