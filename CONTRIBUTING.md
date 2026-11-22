# Contributing to GenAI Chat

This guide explains how code gets from your machine to `main`. It applies to everyone,
including the original author.

## 1. One-time setup

```bash
python3 -m venv ~/.venvs/genai-chat
source ~/.venvs/genai-chat/bin/activate
sudo apt-get install -y default-libmysqlclient-dev pkg-config   # for mysqlclient (Ubuntu)
pip install -r requirements-dev.txt
pre-commit install            # runs the checks on every commit
cp sample_env.txt .env        # then fill in the values
cp local_settings_example.py local_settings.py   # optional, for local overrides
```

Requirements: Python 3.13+, **MySQL 8.4+** (Django 6.1 does not support older MySQL), Redis, and
Ollama (or an OpenAI-compatible API key).

**IntelliJ IDEA:** mark `tests/` as *Test Sources Root*, set the pytest runner
(*Settings → Tools → Python Integrated Tools → Testing: pytest*), and enable the Ruff plugin so
formatting matches CI.

## 2. Branches

- `main` is always releasable. Nobody pushes to it directly; every change arrives by pull request.
- Feature branches follow the project numbering: `genai-chat-<NNN>-<short-name>`, for example
  `genai-chat-011-tool-registry`. Sub-steps use a dot: `genai-chat-010.2-ci-quality`.
- Keep a branch focused on one roadmap item (see `ROADMAP.md`).

## 3. Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <summary in the imperative, max ~72 chars>

<why the change is needed; reference finding IDs such as R2 or H6>
```

Types: `feat`, `fix`, `security`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`.
Examples: `fix(chat): add missing download route (R2)`, `ci: add gitleaks and pip-audit`.

## 4. Before you open a pull request

```bash
pre-commit run --all-files    # ruff, formatting, secrets, migrations
mypy .
pytest --cov                  # coverage must not drop below the floor in pyproject.toml
```

If you changed models, run `python manage.py makemigrations` and commit the migration.
If you changed dependencies, run `pip-audit` and `scripts/generate_third_party_licenses.sh`.

## 5. Definition of Done

A change is done when **all** of these are true:

- [ ] CI is green (lint, tests on SQLite and MySQL, deploy check, security scans).
- [ ] New behaviour has tests; fixed bugs have a regression test.
- [ ] No secrets, personal data or real user content in code, tests, fixtures or logs.
- [ ] Migrations are committed and reversible where possible.
- [ ] Docs are updated: the branch README (`README.<NNN>.md`), `CHANGELOG.md`, `ROADMAP.md`,
      `sample_env.txt` for new settings, and an ADR for any architectural decision.
- [ ] Breaking API changes are listed in the release notes with upgrade steps.

## 6. Code style

- Formatting and linting: **ruff** (config in `pyproject.toml`); do not argue with the formatter.
- Types: new modules must pass `mypy` with `disallow_untyped_defs`. Legacy modules are listed in
  `pyproject.toml` and are removed from the ignore list when they are rewritten (never added to it).
- Never log user content directly: use `chat.utilities.log_safety.redact()`.
- Frontend: no inline `<script>`, `<style>`, `style="..."` or `on...=` handlers (the CSP blocks
  them); third-party libraries go into `static/vendor/<name>-<version>/` with their licence.

## 7. Pull request review

At least one approval is required before merging (once there is more than one maintainer).
Reviewers check correctness, security (OWASP Top 10 and OWASP Top 10 for LLM Applications),
tests, and the Definition of Done. Merge with **squash** so that `main` has one commit per change.
