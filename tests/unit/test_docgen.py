"""The tools/docgen generator is the source of the plan: it must reproduce it as is."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs" / "architecture-plan.md"


def artifact_url() -> str:
    m = re.search(r"https://claude\.ai/artifact/\S+", PLAN.read_text(encoding="utf-8"))
    assert m, "the plan must link to the artifact"
    return m.group(0)


def run_docgen(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    md, html = tmp_path / "plan.md", tmp_path / "plan.html"
    result = subprocess.run(
        [
            sys.executable,
            "tools/docgen/build.py",
            "--artifact-url",
            artifact_url(),
            "--out-md",
            str(md),
            "--out-html",
            str(html),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, md, html


def test_docgen_reproduces_the_committed_plan_exactly(tmp_path: Path):
    result, md, _ = run_docgen(tmp_path)
    assert result.returncode == 0, result.stderr
    assert md.read_text(encoding="utf-8") == PLAN.read_text(encoding="utf-8")


def test_docgen_builds_the_interactive_page_without_leftover_placeholders(tmp_path: Path):
    result, _, html = run_docgen(tmp_path)
    assert result.returncode == 0, result.stderr
    page = html.read_text(encoding="utf-8")
    assert "__DATA__" not in page
    assert "<title>Health Monitor Architecture</title>" in page
    assert "const D = {" in page


def test_docgen_fails_clearly_when_the_template_has_an_unknown_placeholder(tmp_path: Path):
    template = tmp_path / "template.md"
    template.write_text("# Plan\n\n{{UNKNOWN_PLACEHOLDER}}\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "tools/docgen/build.py",
            "--template",
            str(template),
            "--out-md",
            str(tmp_path / "out.md"),
            "--out-html",
            str(tmp_path / "out.html"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "UNKNOWN_PLACEHOLDER" in result.stderr
