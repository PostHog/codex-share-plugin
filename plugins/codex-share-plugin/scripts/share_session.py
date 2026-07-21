#!/usr/bin/env python3
"""Convert a local Codex session to Markdown and optionally publish it to GitHub."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHARE_MARKERS = ("$share-session", "share_session.py", "share this codex session")
ENVIRONMENT_CONTEXT_PATTERN = re.compile(
    r"^\s*<environment_context>.*</environment_context>\s*$", re.DOTALL
)
TERMINAL_PROMPT_PATTERN = re.compile(r"^(?:❯|\$|%)\s")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def read_json_lines(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as session_file:
        for line in session_file:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def session_cwd(path: Path) -> str | None:
    for entry in read_json_lines(path):
        if entry.get("type") == "session_meta":
            payload = entry.get("payload", {})
            cwd = payload.get("cwd") if isinstance(payload, dict) else None
            return cwd if isinstance(cwd, str) else None
    return None


def find_latest_session(current_directory: Path) -> Path:
    session_root = codex_home() / "sessions"
    candidates = list(session_root.glob("**/*.jsonl"))
    if not candidates:
        raise RuntimeError(f"No Codex session logs found under {session_root}")

    matching = [path for path in candidates if session_cwd(path) == str(current_directory)]
    return max(matching or candidates, key=lambda path: path.stat().st_mtime)


def content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if item.get("type") in {"input_text", "output_text", "text"} and isinstance(text, str):
            parts.append(text)
    return "\n\n".join(parts)


def should_skip_message(text: str) -> bool:
    lowered = text.lower()
    return ENVIRONMENT_CONTEXT_PATTERN.fullmatch(text) is not None or any(
        marker in lowered for marker in SHARE_MARKERS
    )


def format_message(text: str, role: str) -> str:
    """Preserve terminal transcripts without changing ordinary Markdown prompts."""
    first_line = text.lstrip().splitlines()[0] if text.strip() else ""
    if role != "user" or "\n" not in text or not TERMINAL_PROMPT_PATTERN.match(first_line):
        return text

    fence = "````" if "```" in text else "```"
    return f"{fence}text\n{text}\n{fence}"


def format_tool_call(payload: dict[str, Any]) -> str:
    name = payload.get("name") or payload.get("type") or "tool"
    raw_arguments = payload.get("arguments", payload.get("input", {}))
    if isinstance(raw_arguments, str):
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = raw_arguments
    else:
        arguments = raw_arguments

    rendered = json.dumps(arguments, indent=2, ensure_ascii=False) if not isinstance(arguments, str) else arguments
    return f"""<details>
<summary><code>{name}</code></summary>

```json
{rendered}
```
</details>"""


def convert_session(path: Path, description: str | None = None) -> str:
    title = description or "Codex session"
    lines = [f"# {title}", "", f"**Exported:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}", ""]

    for entry in read_json_lines(path):
        if entry.get("type") != "response_item":
            continue
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue

        payload_type = payload.get("type")
        if payload_type == "message":
            role = payload.get("role")
            if role not in {"user", "assistant"}:
                continue
            text = content_text(payload.get("content"))
            if not text or should_skip_message(text):
                continue
            heading = "User" if role == "user" else "Codex"
            lines.extend([f"## {heading}", "", format_message(text, role), ""])
        elif payload_type in {"function_call", "custom_tool_call"}:
            rendered = format_tool_call(payload)
            if not should_skip_message(rendered):
                lines.extend([rendered, ""])

    return "\n".join(lines).rstrip() + "\n"


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return sanitized[:50] or "session"


def load_config() -> dict[str, str]:
    config: dict[str, str] = {}
    config_path = codex_home() / "share-plugin-config.json"
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = {
                    key: value
                    for key, value in loaded.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
        except (OSError, json.JSONDecodeError):
            pass

    if repo := os.environ.get("CODEX_SHARE_REPO"):
        config["repo"] = repo
    return config


def configure_repo(repo: str) -> None:
    validate_repo(repo)
    config_path = codex_home() / "share-plugin-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"repo": repo}, indent=2) + "\n", encoding="utf-8")
    print(f"Configured session repository: {repo}")


def validate_repo(repo: str) -> None:
    if not REPO_PATTERN.fullmatch(repo):
        raise RuntimeError("Repository must use the owner/repo format")


def github_username() -> str:
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Could not detect a GitHub user. Run `gh auth login` first.")
    return result.stdout.strip()


def publish(markdown: str, repo: str, description: str | None, branch: str, base_path: str) -> str:
    validate_repo(repo)
    username = github_username()
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    suffix = f"-{sanitize_filename(description)}" if description else ""
    relative_path = Path(base_path) / username / f"{timestamp}{suffix}.md"

    with tempfile.TemporaryDirectory(prefix="codex-share-") as temp_directory:
        clone_path = Path(temp_directory) / "repository"
        clone = subprocess.run(
            ["gh", "repo", "clone", repo, str(clone_path), "--", "--branch", branch, "--depth", "1"],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone.returncode != 0:
            raise RuntimeError(f"Could not clone {repo}: {clone.stderr.strip()}")

        target = clone_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        commit_message = f"Add Codex session: {description}" if description else f"Add Codex session {timestamp}"
        subprocess.run(["git", "add", str(relative_path)], cwd=clone_path, check=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=clone_path, check=True)
        push = subprocess.run(
            ["git", "push", "origin", branch], cwd=clone_path, capture_output=True, text=True, check=False
        )
        if push.returncode != 0:
            raise RuntimeError(f"Could not push to {repo}: {push.stderr.strip()}")

    encoded_path = quote(relative_path.as_posix(), safe="/")
    return f"https://github.com/{repo}/blob/{quote(branch, safe='')}/{encoded_path}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--description", help="Description used as the Markdown title and filename")
    parser.add_argument("--session", type=Path, help="Specific Codex JSONL session to export")
    parser.add_argument("--output", type=Path, help="Preview output path")
    parser.add_argument("--push", action="store_true", help="Publish after generating the transcript")
    parser.add_argument("--repo", help="Override the configured owner/repo")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--base-path", default="sessions/codex")
    parser.add_argument("--configure-repo", metavar="OWNER/REPO")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.configure_repo:
            configure_repo(args.configure_repo)
            return 0

        session = args.session or find_latest_session(Path.cwd())
        markdown = convert_session(session, args.description)
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        preview_path = args.output or Path(tempfile.gettempdir()) / f"codex-session-{timestamp}.md"
        preview_path.write_text(markdown, encoding="utf-8")
        print(f"Preview written to: {preview_path}")

        if args.push:
            repo = args.repo or load_config().get("repo")
            if not repo:
                raise RuntimeError(
                    "No repository configured. Use --configure-repo owner/repo or set CODEX_SHARE_REPO."
                )
            print(f"Published to: {publish(markdown, repo, args.description, args.branch, args.base_path)}")
        else:
            print("Review the preview, then rerun with --push to publish it.")
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
