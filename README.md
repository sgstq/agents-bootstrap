# agents-bootstrap

Personal bootstrap for repository agent guidance.

This project does not claim to provide universal best practices. It installs the agent rules that currently work for this workflow, in a thin format that modern coding agents can read without extra history or noise.

The default guidance is stored as Markdown blocks under `sets/defaults/`. The Python script only detects repository state, renders the selected blocks, shows diffs, and writes files.

### Warning ☠️
<p align="center">
  <b>ALL CODE AND SCRIPTS IN THIS REPOSITORY—EVEN THOSE BASED ON REAL DOCUMENTATION—ARE ENTIRELY EXPERIMENTAL. ALL LOGIC WAS HALLUCINATED BY MATRIX MULTIPLICATIONS….. HAPHAZARDLY. THE FOLLOWING REPOSITORY CONTAINS UNTESTED CODE AND DUE TO ITS CONTENT IT SHOULD NOT BE USED ANYWHERE BY ANYONE ■</b>
</p>

## What It Writes

By default, `agents-bootstrap` writes:

```text
AGENTS.md
CLAUDE.md
.agents/manifest.json
```

`AGENTS.md` and `CLAUDE.md` are mirrored, self-contained instruction files. The manifest is small machine-readable state for agents and update checks.

The installer detects repository languages and includes only relevant language sections:

- Python: `pyproject.toml`, `uv.lock`, `requirements.txt`, or `*.py`
- TypeScript: `package.json`, `tsconfig.json`, lockfiles, or `*.ts` / `*.tsx`

For monorepos, v1 uses one root mirrored pair and includes every detected language section.

## Instruction Sets

The default set is:

```text
sets/defaults/
  core.md
  python.md
  typescript.md
  metadata.json
```

Edit these Markdown files to change generated guidance. Do not hard-code guidance text in `agents_bootstrap.py`.

Use another set by passing a set name or path:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --set defaults
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --set /path/to/custom-set
```

## Agent-Run Usage

Clone this repository somewhere outside the target project, then ask your agent:

```text
Please bootstrap agent files into the current repository using /path/to/agents-bootstrap.
Show me the diff before writing if AGENTS.md or CLAUDE.md already exist.
```

The agent can run:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py check --repo .
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo .
```

If the generated diff looks good:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --yes
```

To install for only one agent:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --agents codex
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --agents claude
```

To record that this repo should not be prompted again:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --decline
```

## Existing Files

If `AGENTS.md` or `CLAUDE.md` already exist, default behavior is review first:

1. print a unified diff
2. ask whether to write, decline, or skip
3. write nothing unless approved

Use `--force` only when replacing the active instruction files is intentional.

## Extra References

You can inline additional reference files into the mirrored instructions:

```bash
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --reference ~/my-agent-rules.md
python /path/to/agents-bootstrap/agents_bootstrap.py init --repo . --reference https://example.com/rules.md
```

References are copied into `AGENTS.md` and `CLAUDE.md`; the target repo does not keep extra history files.

## Manifest

Installed state:

```json
{
  "agents": ["codex", "claude"],
  "package": "agents-bootstrap",
  "schemaVersion": 1,
  "set": "defaults",
  "status": "installed",
  "updatePolicy": "ask",
  "version": "0.2.0"
}
```

Declined state:

```json
{
  "package": "agents-bootstrap",
  "schemaVersion": 1,
  "status": "declined",
  "version": "0.2.0"
}
```

Global agent instructions can check `.agents/manifest.json` at chat start. If it is missing, ask whether to bootstrap. If it says `declined`, do not ask again.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```

This repository's own `AGENTS.md` and `CLAUDE.md` are maintainer guidance for this tool. They are not generated examples of target-repository output.
