# agents-bootstrap Maintainer Guide

This repository builds mirrored agent guidance files for other repositories.

## Source Of Truth
- Do not hard-code default instruction text in `agents_bootstrap.py`.
- Default guidance lives in `sets/defaults/*.md`.
- Set metadata lives in `sets/defaults/metadata.json`.
- The Python script should only detect repository state, select blocks, render files, print diffs, and write manifests.

## Generated Output
- Target repositories receive `AGENTS.md`, `CLAUDE.md`, and `.agents/manifest.json`.
- `AGENTS.md` and `CLAUDE.md` must remain mirrored unless the user explicitly asks for agent-specific differences.
- Do not add proposed/history folders to target repositories. Proposed changes should be shown as diffs, not written as extra repo noise.

## Development
- Keep the implementation dependency-free unless there is a clear reason to add packaging.
- Run `python -m unittest discover -s tests` after changes.
- Add or update tests when changing rendering, detection, manifest, or CLI behavior.
