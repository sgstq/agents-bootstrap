# agents-bootstrap

Personal bootstrap for repository agent guidance.

This project does not claim to provide universal best practices. It installs the agent rules that currently work for this workflow, in a thin format that modern coding agents can read without extra history or noise.

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
  "status": "installed",
  "updatePolicy": "ask",
  "version": "0.1.0"
}
```

Declined state:

```json
{
  "package": "agents-bootstrap",
  "schemaVersion": 1,
  "status": "declined",
  "version": "0.1.0"
}
```

Global agent instructions can check `.agents/manifest.json` at chat start. If it is missing, ask whether to bootstrap. If it says `declined`, do not ask again.

## Development

Run tests:

```bash
python -m unittest discover -s tests
```

