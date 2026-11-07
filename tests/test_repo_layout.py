"""仓库布局与 README 三步命令锁定（防止 README 与脚本漂移）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_required_layout():
    for rel in [
        "README.md",
        "verify.ps1",
        "verify.sh",
        "run.ps1",
        "run.sh",
        "package.json",
        "requirements.txt",
        "vite.config.js",
        "playwright.config.js",
        "mock/app.py",
        "src/App.jsx",
        "src/styles.css",
        "tests/test_api.py",
        "tests/test_contract.py",
        "docs/AC-MAP.md",
        "docs/EVIDENCE.md",
        "docs/USABILITY-GATE-1807.md",
        "docs/openapi.json",
        "VERIFICATION.md",
        "docker-compose.yml",
        "Dockerfile",
        "Dockerfile.web",
        "deploy/nginx.conf",
        ".github/workflows/ci.yml",
        ".github/workflows/container.yml",
    ]:
        assert (ROOT / rel).exists(), f"missing: {rel}"


def test_readme_three_commands_windows():
    assert "npm ci" in README
    assert "python -m venv .venv; .venv\\Scripts\\python -m pip install -r requirements.txt" in README
    assert ".\\run.ps1" in README


def test_readme_three_commands_unix():
    assert "python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" in README
    assert "./run.sh" in README


def test_verify_script_delegates_to_harness():
    harness = (ROOT / "scripts" / "verify.py").read_text(encoding="utf-8")
    for needle in ["pytest", "npm run build", "npx playwright test", "receipt/verify.json", "FAIL-CLOSED"]:
        assert needle in harness, needle


def test_compose_has_mock_and_web():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "mock:" in compose
    assert "web:" in compose
    assert "8001" in compose
    assert "8080:80" in compose
