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


VERSION = "0.2.0"
PACKAGE_NAME = "agents-bootstrap"
ROOT = Path(__file__).resolve().parent
SETS_DIR = ROOT / "sets"
DEFAULT_SET = "defaults"
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


@dataclass(frozen=True)
class RenderedInstructions:
    content: str
    set_name: str
    languages: list[str]
    references: list[str]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(read_text(path))


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


def resolve_set_dir(set_name: str) -> Path:
    set_dir = Path(set_name).expanduser()
    if not set_dir.is_absolute():
        set_dir = SETS_DIR / set_name
    if not set_dir.exists():
        raise SystemExit(f"Instruction set does not exist: {set_dir}")
    return set_dir


def load_set_metadata(set_name: str) -> tuple[Path, dict[str, object]]:
    set_dir = resolve_set_dir(set_name)
    metadata_path = set_dir / "metadata.json"
    if not metadata_path.exists():
        raise SystemExit(f"Instruction set is missing metadata.json: {set_dir}")
    return set_dir, load_json(metadata_path)


def metadata_string(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"Instruction set metadata must define string field: {key}")
    return value


def language_blocks(metadata: dict[str, object]) -> dict[str, str]:
    value = metadata.get("languageBlocks")
    if not isinstance(value, dict):
        raise SystemExit("Instruction set metadata must define object field: languageBlocks")

    blocks = {}
    for language, filename in value.items():
        if not isinstance(language, str) or not isinstance(filename, str):
            raise SystemExit("Instruction set languageBlocks must map strings to strings")
        blocks[language] = filename
    return blocks


def load_set_sections(set_name: str, languages: list[str]) -> tuple[str, list[str]]:
    set_dir, metadata = load_set_metadata(set_name)
    core_file = metadata_string(metadata, "core")
    blocks = language_blocks(metadata)
    sections = [read_text(set_dir / core_file).strip()]
    included_languages = []

    for language in languages:
        block_file = blocks.get(language)
        if block_file is None:
            continue
        sections.append(read_text(set_dir / block_file).strip())
        included_languages.append(language)

    return "\n\n".join(sections), included_languages


def render_instructions(
    repo: Path,
    set_name: str,
    references: list[str],
    languages: list[str] | None,
) -> RenderedInstructions:
    detected_languages = detect_languages(repo) if languages is None else languages
    set_content, included_languages = load_set_sections(set_name, detected_languages)
    sections = [set_content]

    loaded_references = []
    for reference in references:
        resolved_reference, content = load_reference(reference, repo)
        loaded_references.append(resolved_reference)
        sections.append(f"## Additional Reference\n{content}")

    return RenderedInstructions(
        content="\n\n".join(sections).strip() + "\n",
        set_name=set_name,
        languages=included_languages,
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
    return load_json(path)


def write_manifest(repo: Path, manifest: dict[str, object]) -> None:
    write_text(manifest_path(repo), json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def installed_manifest(
    agents: list[str],
    set_name: str,
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
        "set": set_name,
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
    rendered = render_instructions(repo, args.set, args.reference, languages)

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
                set_name=rendered.set_name,
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
                set_name=rendered.set_name,
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
    init_parser.add_argument("--set", default=DEFAULT_SET, help="Instruction set name or path. Defaults to 'defaults'.")
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
