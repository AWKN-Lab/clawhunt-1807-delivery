# scripts/verify.py：一条命令跑 pytest + 前端构建 + Playwright E2E，fail-closed 写 receipt/verify.json
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "receipt" / "logs"
RECEIPT_PATH = ROOT / "receipt" / "verify.json"
SHA_PATH = ROOT / "receipt" / "verify.sha256"
SCREENSHOT_DIR = ROOT / "evidence" / "screenshots"
PLAYWRIGHT_JSON = ROOT / "evidence" / "playwright.json"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def run_step(name: str, command, timeout: int, shell: bool = False) -> dict:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    browsers_path = env.get("PLAYWRIGHT_BROWSERS_PATH")
    if browsers_path and not Path(browsers_path).exists():
        # 本机可能残留指向不存在盘符的 PATH，会让 Playwright 启动失败
        env.pop("PLAYWRIGHT_BROWSERS_PATH", None)
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            shell=shell,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        stdout, stderr, exit_code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + f"\nTIMEOUT after {timeout}s"
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        exit_code = 124
    duration = int((time.time() - started) * 1000)
    log_path = LOG_DIR / f"{name}.log"
    log_path.write_text((stdout or "") + "\n--- STDERR ---\n" + (stderr or ""), encoding="utf-8")
    shown = (stdout or "").strip().splitlines()
    tail = "\n".join(shown[-80:]) if shown else ""
    if stderr.strip():
        tail += "\n--- STDERR ---\n" + "\n".join(stderr.strip().splitlines()[-30:])
    print(f"\n=== [{name}] exit={exit_code} {duration}ms ===")
    if tail:
        print(tail)
    return {
        "name": name,
        "command": command if isinstance(command, str) else " ".join(command),
        "exit_code": exit_code,
        "duration_ms": duration,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "log": str(log_path.relative_to(ROOT)),
    }


def pytest_summary() -> tuple[str, int]:
    report = ROOT / "receipt" / "pytest.xml"
    if not report.exists():
        return "no junit xml", 0
    try:
        tree = ET.parse(report)
        suite = tree.getroot()
        if suite.tag == "testsuites":
            suite = suite.find("testsuite")
        total = int(suite.get("tests", 0))
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        passed = max(total - failures - errors - skipped, 0)
        return f"{passed} passed / {total} total (failures={failures}, errors={errors}, skipped={skipped})", failures + errors
    except (ET.ParseError, AttributeError, TypeError):
        return "junit xml 解析失败", 1


def playwright_summary() -> tuple[str, int]:
    if not PLAYWRIGHT_JSON.exists():
        return "no playwright json", 1
    try:
        data = json.loads(PLAYWRIGHT_JSON.read_text(encoding="utf-8"))
        stats = data.get("stats", {})
        expected = int(stats.get("expected", 0))
        unexpected = int(stats.get("unexpected", 0))
        skipped = int(stats.get("skipped", 0))
        flaky = int(stats.get("flaky", 0))
        return (
            f"{expected} passed / {expected + unexpected + skipped} total "
            f"(unexpected={unexpected}, flaky={flaky}, skipped={skipped})",
            unexpected,
        )
    except (json.JSONDecodeError, ValueError):
        return "playwright json 解析失败", 1


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def collect_screenshots() -> list[dict]:
    items = []
    if not SCREENSHOT_DIR.exists():
        return items
    for path in sorted(SCREENSHOT_DIR.glob("*.png")):
        width, height = png_size(path)
        items.append(
            {
                "file": str(path.relative_to(ROOT)),
                "width": width,
                "height": height,
                "bytes": path.stat().st_size,
            }
        )
    return items


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() or "uncommitted"
    except (OSError, subprocess.SubprocessError):
        return "no-git"


def main() -> int:
    print("ClawHunt #1807 · verify（pytest → build → Playwright E2E）")
    print(f"root: {ROOT}")
    print(f"python: {sys.executable} ({platform.python_version()})")

    steps = []
    steps.append(
        run_step(
            "pytest",
            [sys.executable, "-m", "pytest", "-q", "--junitxml=receipt/pytest.xml", "tests"],
            300,
        )
    )
    steps.append(run_step("build", "npm run build", 300, shell=True))

    if PLAYWRIGHT_JSON.exists():
        PLAYWRIGHT_JSON.unlink()
    steps.append(run_step("playwright", "npx playwright test", 900, shell=True))

    py_summary, py_failures = pytest_summary()
    pw_summary, pw_unexpected = playwright_summary()
    for step, summary, failures in (
        (steps[0], py_summary, py_failures),
        (steps[2], pw_summary, pw_unexpected),
    ):
        step["summary"] = summary
        if failures > 0:
            step["status"] = "FAIL"

    screenshots = collect_screenshots()
    perf_path = ROOT / "evidence" / "perf.json"
    artifacts_ok = len(screenshots) >= 3 and perf_path.exists()
    artifacts = {
        "name": "evidence-artifacts",
        "command": "检查 evidence/screenshots/*.png（>=3）与 evidence/perf.json",
        "exit_code": 0 if artifacts_ok else 1,
        "duration_ms": 0,
        "status": "PASS" if artifacts_ok else "FAIL",
        "summary": f"screenshots={len(screenshots)}, perf={'yes' if perf_path.exists() else 'no'}",
    }
    steps.append(artifacts)

    failed = [step for step in steps if step["status"] != "PASS"]
    conclusion = "PASS" if not failed else "FAIL"

    dist_bytes = 0
    dist_files = 0
    for item in (ROOT / "dist").glob("**/*"):
        if item.is_file():
            dist_bytes += item.stat().st_size
            dist_files += 1

    receipt = {
        "project": "clawhunt-1807/candidate-h5",
        "generated_at": now_iso(),
        "conclusion": conclusion,
        "exit_code": 0 if conclusion == "PASS" else 1,
        "git_commit": git_commit(),
        "platform": {
            "os": platform.system(),
            "python": platform.python_version(),
            "node": shutil.which("node") or "missing",
        },
        "steps": steps,
        "dist": {"files": dist_files, "bytes": dist_bytes},
        "screenshots": screenshots,
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    digest = hashlib.sha256(RECEIPT_PATH.read_bytes()).hexdigest()
    SHA_PATH.write_text(f"sha256:{digest}  verify.json\n", encoding="ascii")

    print("\n=== SUMMARY ===")
    for step in steps:
        print(f"{step['status']:<4} {step['name']:<18} exit={step['exit_code']} {step.get('summary', '')}")
    print(f"conclusion: {conclusion}")
    print(f"receipt: receipt/verify.json (sha256:{digest})")
    print(f"screenshots: {len(screenshots)} -> evidence/screenshots/")
    if conclusion != "PASS":
        print("FAIL-CLOSED: 任一环节失败即 exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
