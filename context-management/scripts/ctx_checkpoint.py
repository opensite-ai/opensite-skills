#!/usr/bin/env python3
"""
ctx_checkpoint.py — Session state persistence for surviving context compaction.

Saves structured session checkpoints to .ctx/checkpoint.md so agents can resume
after Codex CLI compaction or any context window reset.

Usage:
    # Save a checkpoint
    python ctx_checkpoint.py save --project /path \
      --task "Implementing OAuth2 flow" \
      --completed "Added routes, Created model" \
      --in-progress "Writing middleware" \
      --next-steps "Add tests, Update docs" \
      --decisions "Using tower middleware, JWT RS256" \
      --context "Branch: feature/oauth2, Tests passing"

    # Load the latest checkpoint
    python ctx_checkpoint.py load --project /path

    # List all checkpoints
    python ctx_checkpoint.py list --project /path

    # Save from stdin (for multiline content)
    cat checkpoint_data.md | python ctx_checkpoint.py save-raw --project /path

No external dependencies. Python 3.8+.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def get_git_context() -> str:
    """Auto-capture git branch and last commit if available."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        commit = subprocess.run(
            ["git", "log", "--oneline", "-1"], capture_output=True, text=True, timeout=2
        ).stdout.strip()

        if branch and commit:
            return f"Git: {branch} | {commit}"
        elif branch:
            return f"Git: {branch}"
        else:
            return ""
    except Exception:
        return ""


def get_ctx_dir(project_dir: str) -> Path:
    """Resolve the .ctx/ directory for the given project."""
    ctx_dir = Path(project_dir).resolve() / ".ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    return ctx_dir


def save_checkpoint(
    project_dir: str,
    task: str = "",
    completed: str = "",
    in_progress: str = "",
    next_steps: str = "",
    decisions: str = "",
    context: str = "",
) -> Path:
    """Save a structured checkpoint to .ctx/checkpoint.md."""
    ctx_dir = get_ctx_dir(project_dir)
    checkpoint_path = ctx_dir / "checkpoint.md"
    archive_dir = ctx_dir / "checkpoints"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Archive existing checkpoint if present
    if checkpoint_path.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        archive_path = archive_dir / f"{timestamp}.md"
        shutil.copy2(str(checkpoint_path), str(archive_path))

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    def format_list(text: str) -> str:
        """Convert comma-separated items into a bulleted list (for list fields)."""
        if not text.strip():
            return "- (none)\n"
        items = [item.strip() for item in text.split(",") if item.strip()]
        return "\n".join(f"- {item}" for item in items) + "\n"

    def format_text(text: str) -> str:
        """Format a text field verbatim (no comma splitting)."""
        return text if text.strip() else "(none)"

    # Auto-capture git context if not already provided
    git_context = get_git_context()
    if git_context and context:
        context = f"{git_context}\n{context}"
    elif git_context:
        context = git_context

    content = f"""---
type: checkpoint
created: {date_str}
time: {time_str}
---

# Session Checkpoint

## Current Task
{format_text(task)}

## Completed
{format_list(completed)}
## In Progress
{format_list(in_progress)}
## Next Steps
{format_list(next_steps)}
## Key Decisions
{format_text(decisions)}
## Context / Notes
{format_text(context)}

---
_Saved: {date_str} {time_str}_
"""

    checkpoint_path.write_text(content, encoding="utf-8")
    print(f"Checkpoint saved: {checkpoint_path}")
    return checkpoint_path


def save_raw_checkpoint(project_dir: str, content: str) -> Path:
    """Save raw markdown content as a checkpoint."""
    ctx_dir = get_ctx_dir(project_dir)
    checkpoint_path = ctx_dir / "checkpoint.md"
    archive_dir = ctx_dir / "checkpoints"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Archive existing
    if checkpoint_path.exists():
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        archive_path = archive_dir / f"{timestamp}.md"
        shutil.copy2(str(checkpoint_path), str(archive_path))

    checkpoint_path.write_text(content, encoding="utf-8")
    print(f"Checkpoint saved: {checkpoint_path}")
    return checkpoint_path


def load_checkpoint(project_dir: str, as_json: bool = False) -> str:
    """Load and return the latest checkpoint content."""
    ctx_dir = get_ctx_dir(project_dir)
    checkpoint_path = ctx_dir / "checkpoint.md"

    if not checkpoint_path.exists():
        return (
            json.dumps({"error": "no checkpoint found"})
            if as_json
            else "(no checkpoint found)"
        )

    content = checkpoint_path.read_text(encoding="utf-8")

    if as_json:
        # Parse the markdown into structured JSON
        lines = content.splitlines()
        data = {
            "raw": content,
            "task": "",
            "completed": [],
            "in_progress": [],
            "next_steps": [],
            "decisions": "",
            "context": "",
            "timestamp": "",
        }

        current_section = None
        for line in lines:
            line = line.strip()
            if line.startswith("## "):
                section_name = line[3:].lower().replace("/", "").strip()
                if "task" in section_name:
                    current_section = "task"
                elif "completed" in section_name:
                    current_section = "completed"
                elif "in progress" in section_name:
                    current_section = "in_progress"
                elif "next step" in section_name:
                    current_section = "next_steps"
                elif "decision" in section_name:
                    current_section = "decisions"
                elif "context" in section_name or "note" in section_name:
                    current_section = "context"
            elif line.startswith("- ") and current_section in [
                "completed",
                "in_progress",
                "next_steps",
            ]:
                data[current_section].append(line[2:])
            elif line.startswith("_Saved:"):
                data["timestamp"] = line.replace("_Saved:", "").replace("_", "").strip()
            elif line and not line.startswith("---") and current_section:
                if current_section in ["task", "decisions", "context"]:
                    if data[current_section]:
                        data[current_section] += "\n" + line
                    else:
                        data[current_section] = line
                elif current_section in ["completed", "in_progress", "next_steps"]:
                    # Non-bullet line in a list section - skip or append to last item
                    pass

        # Normalize "(none)" strings to empty strings for JSON output
        for key in ["task", "decisions", "context"]:
            if data[key] in ["(none)", "(not specified)"]:
                data[key] = ""

        return json.dumps(data, indent=2)

    return content


def list_checkpoints(project_dir: str) -> list:
    """List all archived checkpoints."""
    ctx_dir = get_ctx_dir(project_dir)
    archive_dir = ctx_dir / "checkpoints"

    if not archive_dir.exists():
        return []

    checkpoints = sorted(archive_dir.glob("*.md"), reverse=True)
    return checkpoints


def main():
    parser = argparse.ArgumentParser(description="Session checkpoint manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Save command
    save_parser = subparsers.add_parser("save", help="Save a structured checkpoint")
    save_parser.add_argument("--project", default=".", help="Project directory")
    save_parser.add_argument("--task", default="", help="Current task description")
    save_parser.add_argument(
        "--completed", default="", help="Completed items (comma-separated)"
    )
    save_parser.add_argument(
        "--in-progress", default="", help="In-progress items (comma-separated)"
    )
    save_parser.add_argument(
        "--next-steps", default="", help="Next steps (comma-separated)"
    )
    save_parser.add_argument(
        "--decisions",
        default="",
        help="Key decisions (verbatim text; use '\\n' for multiple items)",
    )
    save_parser.add_argument(
        "--context", default="", help="Additional context or notes"
    )

    # Save-raw command
    raw_parser = subparsers.add_parser(
        "save-raw", help="Save raw markdown as checkpoint (stdin)"
    )
    raw_parser.add_argument("--project", default=".", help="Project directory")

    # Load command
    load_parser = subparsers.add_parser("load", help="Load the latest checkpoint")
    load_parser.add_argument("--project", default=".", help="Project directory")
    load_parser.add_argument(
        "--json", action="store_true", help="Output as structured JSON"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List all archived checkpoints")
    list_parser.add_argument("--project", default=".", help="Project directory")

    args = parser.parse_args()

    if args.command == "save":
        save_checkpoint(
            project_dir=args.project,
            task=args.task,
            completed=args.completed,
            in_progress=args.in_progress,
            next_steps=args.next_steps,
            decisions=args.decisions,
            context=args.context,
        )

    elif args.command == "save-raw":
        if sys.stdin.isatty():
            print("Error: pipe checkpoint content to stdin.", file=sys.stderr)
            sys.exit(1)
        content = sys.stdin.read()
        save_raw_checkpoint(args.project, content)

    elif args.command == "load":
        content = load_checkpoint(args.project, as_json=args.json)
        print(content)

    elif args.command == "list":
        checkpoints = list_checkpoints(args.project)
        if not checkpoints:
            print("  No archived checkpoints.")
            return
        print(f"\nArchived Checkpoints ({len(checkpoints)} total)")
        print("-" * 50)
        for cp in checkpoints[:20]:
            size = cp.stat().st_size
            print(f"  {cp.name:<30} {size:>6,} bytes")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
