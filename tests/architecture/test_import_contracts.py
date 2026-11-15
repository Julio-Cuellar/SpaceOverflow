import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINT = [sys.executable, "-m", "importlinter.cli"]


def run_lint(cwd: Path, extra_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ}
    if extra_path:
        env["PYTHONPATH"] = str(extra_path)
    return subprocess.run(
        [shutil.which("lint-imports") or "lint-imports", "--config", "pyproject.toml"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_real_code_respects_every_contract():
    r = run_lint(ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def _canary(tmp: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Replicates the real config on a minimal tree with one violation."""
    cfg = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    tmp.joinpath("pyproject.toml").write_text(
        cfg[cfg.index("[tool.importlinter]") :], encoding="utf-8"
    )
    for p in ["spaceapp", "spaceapp/modules", "spaceapp/platform"]:
        (tmp / p).mkdir(parents=True, exist_ok=True)
        (tmp / p / "__init__.py").write_text("")
    for m in [
        "telemetry",
        "monitoring",
        "knowledge",
        "assistant",
        "crew",
        "facility",
        "engagement",
        "groundlink",
        "realtime",
    ]:
        for sub in ["", "domain", "application", "ports", "adapters"]:
            d = tmp / "spaceapp/modules" / m / sub
            d.mkdir(parents=True, exist_ok=True)
            (d / "__init__.py").write_text("")
        (tmp / "spaceapp/modules" / m / "contracts.py").write_text("")
        (tmp / "spaceapp/modules" / m / "facade.py").write_text("")
    (tmp / "spaceapp/modules/telemetry/domain/x.py").write_text(body)
    return run_lint(tmp, tmp)


def test_canary_a_module_cannot_import_another_modules_domain(tmp_path: Path):
    r = _canary(tmp_path, "import spaceapp.modules.monitoring.domain\n")
    assert r.returncode != 0
    assert "independ" in (r.stdout + r.stderr).lower()


def test_canary_a_module_may_import_another_modules_contracts_and_facade(tmp_path: Path):
    body = (
        "import spaceapp.modules.monitoring.contracts\nimport spaceapp.modules.monitoring.facade\n"
    )
    r = _canary(tmp_path, body)
    assert r.returncode == 0, r.stdout + r.stderr


def test_canary_the_domain_cannot_import_infrastructure(tmp_path: Path):
    r = _canary(tmp_path, "import sqlalchemy\n")
    assert r.returncode != 0


def test_canary_the_platform_cannot_import_modules(tmp_path: Path):
    (tmp_path / "spaceapp/platform").mkdir(parents=True, exist_ok=True)
    r = _canary(tmp_path, "")
    (tmp_path / "spaceapp/platform/bad.py").write_text("import spaceapp.modules.telemetry\n")
    r = run_lint(tmp_path, tmp_path)
    assert r.returncode != 0
