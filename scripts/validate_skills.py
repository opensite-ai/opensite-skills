#!/usr/bin/env python3
"""Validate skill structure, metadata, and bundled helper files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_BLOCK_RE = re.compile(r"```.*?```", re.S)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

METADATA_KEYS = {
    "opensite-category",
    "opensite-scope",
    "opensite-visibility",
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def validate_frontmatter(skill_dir: Path, errors: list[str]) -> dict | None:
    text = (skill_dir / "SKILL.md").read_text()
    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(f"{skill_dir.name}: invalid or missing YAML frontmatter", errors)
        return None

    frontmatter_text, _body = match.groups()
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        fail(f"{skill_dir.name}: frontmatter YAML parse failed: {exc}", errors)
        return None

    if not isinstance(data, dict):
        fail(f"{skill_dir.name}: frontmatter must parse to a mapping", errors)
        return None

    if data.get("name") != skill_dir.name:
        fail(
            f"{skill_dir.name}: frontmatter name does not match directory ({data.get('name')!r})",
            errors,
        )
    if not isinstance(data.get("description"), str) or not data["description"].strip():
        fail(f"{skill_dir.name}: missing description", errors)
    if not isinstance(data.get("compatibility"), str) or not data["compatibility"].strip():
        fail(f"{skill_dir.name}: missing compatibility note", errors)

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        fail(f"{skill_dir.name}: missing metadata mapping", errors)
    else:
        missing = sorted(METADATA_KEYS - set(metadata.keys()))
        if missing:
            fail(
                f"{skill_dir.name}: metadata missing keys: {', '.join(missing)}",
                errors,
            )

    allowed_tools = data.get("allowed-tools")
    if isinstance(allowed_tools, str) and "," in allowed_tools:
        fail(f"{skill_dir.name}: allowed-tools must be space-delimited, not comma-delimited", errors)

    return data


def validate_line_count(skill_dir: Path, errors: list[str]) -> None:
    line_count = sum(1 for _ in (skill_dir / "SKILL.md").open())
    if line_count > 500:
        fail(f"{skill_dir.name}: SKILL.md is {line_count} lines; repo limit is 500", errors)


def validate_openai_yaml(skill_dir: Path, frontmatter: dict | None, errors: list[str]) -> None:
    path = skill_dir / "agents" / "openai.yaml"
    if not path.exists():
        fail(f"{skill_dir.name}: missing agents/openai.yaml", errors)
        return

    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        fail(f"{skill_dir.name}: agents/openai.yaml parse failed: {exc}", errors)
        return

    if not isinstance(data, dict):
        fail(f"{skill_dir.name}: agents/openai.yaml must parse to a mapping", errors)
        return

    interface = data.get("interface")
    if not isinstance(interface, dict):
        fail(f"{skill_dir.name}: agents/openai.yaml missing interface block", errors)
        return

    for key in ("display_name", "short_description", "default_prompt"):
        value = interface.get(key)
        if not isinstance(value, str) or not value.strip():
            fail(f"{skill_dir.name}: interface.{key} is missing", errors)

    short_description = interface.get("short_description", "")
    if isinstance(short_description, str) and not (25 <= len(short_description) <= 64):
        fail(
            f"{skill_dir.name}: interface.short_description must be 25-64 chars",
            errors,
        )

    default_prompt = interface.get("default_prompt", "")
    if isinstance(default_prompt, str) and f"${skill_dir.name}" not in default_prompt:
        fail(
            f"{skill_dir.name}: interface.default_prompt must mention ${skill_dir.name}",
            errors,
        )

    policy = data.get("policy")
    if not isinstance(policy, dict) or "allow_implicit_invocation" not in policy:
        fail(f"{skill_dir.name}: agents/openai.yaml missing policy.allow_implicit_invocation", errors)
        return

    if frontmatter and frontmatter.get("disable-model-invocation") is True:
        if policy.get("allow_implicit_invocation") is not False:
            fail(
                f"{skill_dir.name}: implicit invocation must be false when disable-model-invocation is true",
                errors,
            )


def validate_activation_guide(skill_dir: Path, errors: list[str]) -> None:
    path = skill_dir / "references" / "activation.md"
    if not path.exists():
        fail(f"{skill_dir.name}: missing references/activation.md", errors)


def validate_links(skill_dir: Path, errors: list[str]) -> None:
    text = (skill_dir / "SKILL.md").read_text()
    text = CODE_BLOCK_RE.sub("", text)
    for ref in LINK_RE.findall(text):
        if ref.startswith("http://") or ref.startswith("https://") or ref.startswith("/"):
            continue
        target = skill_dir / ref
        if not target.exists():
            fail(f"{skill_dir.name}: missing linked file {ref}", errors)


def validate_helper_scripts(skill_dir: Path, errors: list[str]) -> None:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.exists():
        return

    python_files = sorted(str(path) for path in scripts_dir.glob("*.py"))
    if python_files:
        result = subprocess.run(
            ["python3", "-B", "-m", "py_compile", *python_files],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail(
                f"{skill_dir.name}: python helper syntax check failed: {result.stderr.strip() or result.stdout.strip()}",
                errors,
            )

    shell_files = sorted(str(path) for path in scripts_dir.glob("*.sh"))
    if shell_files:
        result = subprocess.run(
            ["bash", "-n", *shell_files],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            fail(
                f"{skill_dir.name}: shell helper syntax check failed: {result.stderr.strip() or result.stdout.strip()}",
                errors,
            )


def main() -> int:
    errors: list[str] = []
    skill_dirs = sorted(path for path in REPO_ROOT.iterdir() if (path / "SKILL.md").exists())
    for skill_dir in skill_dirs:
        frontmatter = validate_frontmatter(skill_dir, errors)
        validate_line_count(skill_dir, errors)
        validate_openai_yaml(skill_dir, frontmatter, errors)
        validate_activation_guide(skill_dir, errors)
        validate_links(skill_dir, errors)
        validate_helper_scripts(skill_dir, errors)

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Validated {len(skill_dirs)} skills successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
