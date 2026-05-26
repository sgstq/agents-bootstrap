#!/usr/bin/env python3
"""Bootstrap mirrored agent guidance files into a repository."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.request import urlopen


VERSION = "0.1.0"
PACKAGE_NAME = "agents-bootstrap"
DEFAULT_AGENTS = ("codex", "claude")
INSTRUCTION_FILES = {
    "codex": "AGENTS.md",
    "claude": "CLAUDE.md",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".agents",
    ".claude",
    ".codex",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


CORE_RULES = """# Agent Instructions

These instructions describe how AI coding agents should work in this repository.

## Clarify Before Acting
- Ask questions when the request, current behavior, or desired behavior is unclear.
- State assumptions before implementation.
- If a simpler approach exists, mention it before choosing a larger one.

## Planning First
- Do not implement code changes until the user explicitly asks with words like "implement", "build it", "go ahead", or similar.
- When the user asks a question, answer the question only. Do not make code changes unless explicitly asked.
- For multi-step work, give a short plan with verification steps before editing.

## Simplicity
- Make the smallest change that solves the stated problem.
- Do not add speculative features, unused abstractions, or configurability that was not requested.
- Keep every changed line traceable to the user request.

## Surgical Changes
- Touch only the files needed for the task.
- Match the existing style even if you would normally write it differently.
- Do not refactor adjacent code or delete unrelated dead code unless asked.
- Preserve user changes and never revert work you did not make without explicit approval.

## Code Safety
- Fix root causes. Do not hide errors with broad try/catch, sleeps, ignored type errors, or placeholder returns.
- Do not submit TODO, FIXME, placeholder comments, mock implementations, or incomplete code unless the user explicitly asks for a draft.
- Before creating a new helper, schema, builder, or utility, search for an existing implementation and reuse it when appropriate.

## Verification
- Define success criteria before changing code.
- Run the smallest relevant validation command after changes.
- If validation cannot be run, explain why and describe the remaining risk.
"""


PYTHON_RULES = """## Python
- Prefer the Python version configured by the repository, such as `pyproject.toml`, `.python-version`, or `mise.toml`.
- If the repo uses `uv`, manage dependencies with `uv`; do not edit dependency files by hand.
- Use the repository virtual environment when one exists.
- Put imports at the top of the file unless there is a clear local pattern requiring otherwise.
- Do not use `cast`, `# type: ignore`, or `# noqa` to silence tooling without explicit approval.
- Add or update focused tests when changing behavior.
"""


TYPESCRIPT_RULES = """## TypeScript
- Use the package manager already used by the repository.
- Do not edit dependency manifests by hand to add packages; use the package manager command.
- Avoid `any`; use precise types, `unknown`, or generics.
- Avoid type assertions. Fix the underlying types instead.
- Let TypeScript infer obvious callback and local variable types.
- Remove unused parameters instead of prefixing or ignoring them unless the existing codebase clearly does otherwise.
"""


@dataclass(frozen=True)
class RenderedInstructions:
    content: str
    languages: list[str]
    references: list[str]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def detect_languages(repo: Path) -> list[str]:
    found = set()

    for root, dirs, files in os.walk(repo):
        dirs[:] = [directory for directory in dirs if directory not in SKIP_DIRS]
        file_set = set(files)
        current = Path(root)

        if {"pyproject.toml", "uv.lock", "requirements.txt"} & file_set:
            found.add("python")
        if {"package.json", "tsconfig.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"} & file_set:
            found.add("typescript")

        for name in files:
            suffix = current.joinpath(name).suffix
            if suffix == ".py":
                found.add("python")
            if suffix in {".ts", ".tsx"}:
                found.add("typescript")

        if found == {"python", "typescript"}:
            break

    return [language for language in ("python", "typescript") if language in found]


def load_reference(reference: str, repo: Path) -> tuple[str, str]:
    if reference.startswith(("http://", "https://")):
        with urlopen(reference, timeout=15) as response:
            content = response.read().decode("utf-8")
        return reference, content.strip()

    path = Path(reference).expanduser()
    if not path.is_absolute():
        path = repo / path
    return str(path), read_text(path).strip()


def render_instructions(repo: Path, references: list[str], languages: list[str] | None) -> RenderedInstructions:
    detected_languages = detect_languages(repo) if languages is None else languages
    sections = [CORE_RULES.strip()]

    if "python" in detected_languages:
        sections.append(PYTHON_RULES.strip())
    if "typescript" in detected_languages:
        sections.append(TYPESCRIPT_RULES.strip())

    loaded_references = []
    for reference in references:
        resolved_reference, content = load_reference(reference, repo)
        loaded_references.append(resolved_reference)
        sections.append(f"## Additional Reference\n{content}")

    return RenderedInstructions(
        content="\n\n".join(sections).strip() + "\n",
        languages=detected_languages,
        references=loaded_references,
    )


def selected_instruction_files(agents: list[str]) -> dict[str, str]:
    invalid = sorted(set(agents) - set(INSTRUCTION_FILES))
    if invalid:
        names = ", ".join(invalid)
        raise SystemExit(f"Unknown agent name: {names}")
    return {agent: INSTRUCTION_FILES[agent] for agent in agents}


def unified_diff(path: Path, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"{path} (generated)",
        )
    )


def manifest_path(repo: Path) -> Path:
    return repo / ".agents" / "manifest.json"


def load_manifest(repo: Path) -> dict[str, object] | None:
    path = manifest_path(repo)
    if not path.exists():
        return None
    return json.loads(read_text(path))


def write_manifest(repo: Path, manifest: dict[str, object]) -> None:
    write_text(manifest_path(repo), json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def installed_manifest(
    agents: list[str],
    languages: list[str],
    references: list[str],
    files: dict[str, str],
    source: str,
    update_policy: str,
) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "package": PACKAGE_NAME,
        "status": "installed",
        "version": VERSION,
        "source": source,
        "agents": agents,
        "languages": languages,
        "references": references,
        "updatePolicy": update_policy,
        "files": files,
    }


def declined_manifest(source: str) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "package": PACKAGE_NAME,
        "status": "declined",
        "version": VERSION,
        "source": source,
        "declinedAt": date.today().isoformat(),
    }


def print_status(repo: Path) -> None:
    manifest = load_manifest(repo)
    languages = detect_languages(repo)
    print(f"Repository: {repo}")
    print(f"Detected languages: {', '.join(languages) if languages else 'none'}")
    if manifest is None:
        print("Manifest: missing")
        return
    print(f"Manifest: {manifest.get('status')} ({manifest.get('package')} {manifest.get('version')})")
    if manifest.get("status") == "installed":
        agents = manifest.get("agents", [])
        print(f"Agents: {', '.join(agents) if isinstance(agents, list) else agents}")
        print(f"Update policy: {manifest.get('updatePolicy', 'ask')}")


def prompt_choice(prompt: str, choices: set[str]) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return answer
        print(f"Choose one of: {', '.join(sorted(choices))}")


def init_repo(args: argparse.Namespace) -> int:
    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        raise SystemExit(f"Repository path does not exist: {repo}")

    agents = args.agents.split(",") if args.agents else list(DEFAULT_AGENTS)
    agents = [agent.strip() for agent in agents if agent.strip()]
    instruction_files = selected_instruction_files(agents)

    languages = None if args.languages == "auto" else [item.strip() for item in args.languages.split(",") if item.strip()]
    rendered = render_instructions(repo, args.reference, languages)

    if args.decline:
        write_manifest(repo, declined_manifest(args.source))
        print(f"Wrote declined manifest: {manifest_path(repo)}")
        return 0

    existing_manifest = load_manifest(repo)
    update_policy = args.update_policy or "ask"
    if existing_manifest and existing_manifest.get("status") == "installed":
        update_policy = str(existing_manifest.get("updatePolicy", update_policy))

    changes: dict[Path, tuple[str, str]] = {}
    for filename in instruction_files.values():
        path = repo / filename
        before = read_text(path) if path.exists() else ""
        after = rendered.content
        if before != after:
            changes[path] = (before, after)

    if not changes:
        files = {filename: sha256_text(rendered.content) for filename in instruction_files.values()}
        write_manifest(
            repo,
            installed_manifest(
                agents=agents,
                languages=rendered.languages,
                references=rendered.references,
                files=files,
                source=args.source,
                update_policy=update_policy,
            ),
        )
        print("Instruction files are already up to date.")
        return 0

    should_write = args.force or update_policy in {"overwrite", "patch-managed"}

    if not should_write:
        for path, (before, after) in changes.items():
            print(unified_diff(path, before, after))

        if args.yes:
            should_write = True
        else:
            choice = prompt_choice(
                "Write generated instruction files? [w]rite, [d]ecline, [s]kip: ",
                {"w", "d", "s"},
            )
            if choice == "d":
                write_manifest(repo, declined_manifest(args.source))
                print(f"Wrote declined manifest: {manifest_path(repo)}")
                return 0
            if choice == "s":
                print("Skipped without writing files.")
                return 0
            should_write = True

    if should_write:
        for path, (_, after) in changes.items():
            write_text(path, after)

        files = {filename: sha256_text(rendered.content) for filename in instruction_files.values()}
        write_manifest(
            repo,
            installed_manifest(
                agents=agents,
                languages=rendered.languages,
                references=rendered.references,
                files=files,
                source=args.source,
                update_policy=update_policy,
            ),
        )
        print(f"Wrote {len(changes)} instruction file(s) and {manifest_path(repo)}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap mirrored agent files into a repository.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create or update agent guidance files.")
    init_parser.add_argument("--repo", default=".", help="Repository path. Defaults to current directory.")
    init_parser.add_argument("--agents", default="codex,claude", help="Comma-separated agents: codex,claude.")
    init_parser.add_argument("--languages", default="auto", help="Comma-separated languages or 'auto'.")
    init_parser.add_argument("--reference", action="append", default=[], help="Extra local file or URL to inline.")
    init_parser.add_argument("--source", default="local", help="Source identifier stored in the manifest.")
    init_parser.add_argument("--update-policy", choices=["ask", "patch-managed", "overwrite"], help="Stored update policy.")
    init_parser.add_argument("--yes", action="store_true", help="Accept generated diffs after showing them.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite without showing diffs.")
    init_parser.add_argument("--decline", action="store_true", help="Record a declined manifest and write no instructions.")
    init_parser.set_defaults(func=init_repo)

    check_parser = subparsers.add_parser("check", help="Show detected repo state.")
    check_parser.add_argument("--repo", default=".", help="Repository path. Defaults to current directory.")
    check_parser.set_defaults(func=lambda args: print_status(Path(args.repo).expanduser().resolve()) or 0)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
