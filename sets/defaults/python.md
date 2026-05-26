## Python
- Prefer the Python version configured by the repository, such as `pyproject.toml`, `.python-version`, or `mise.toml`.
- If the repo uses `uv`, manage dependencies with `uv`; do not edit dependency files by hand.
- Use the repository virtual environment when one exists.
- Put imports at the top of the file unless there is a clear local pattern requiring otherwise.
- Do not use `cast`, `# type: ignore`, or `# noqa` to silence tooling without explicit approval.
- Add or update focused tests when changing behavior.
