# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Email **[SECURITY CONTACT EMAIL]** with:

- a description of the issue and its impact,
- steps to reproduce (or a proof of concept),
- the affected version / commit.

We aim to acknowledge reports within **3 working days** and to provide a fix or mitigation plan
within **30 days** for high-severity issues. Please give us reasonable time to fix the issue
before any public disclosure.

## Supported versions

Only the latest release on `main` receives security fixes.

## How security is enforced in the code base

| Control | Where |
|---|---|
| Secret scanning of the whole git history | CI `security` job (gitleaks) + pre-commit hook |
| Known-vulnerability scan of Python dependencies | CI `security` job (pip-audit) + weekly Dependabot PRs |
| Licence policy (no strong copyleft in runtime deps) | CI `security` job (pip-licenses) |
| Static analysis incl. security rules (bandit `S` rules) | ruff, in CI and pre-commit |
| Production settings check (`check --deploy`) | CI `deploy-check` job |
| Content-Security-Policy, no third-party CDNs | `SECURE_CSP` in `config/settings.py`, `static/vendor/` |
| Third-party GitHub Actions pinned to commit SHAs | `.github/workflows/ci.yml` |
| No user text in logs | `chat/utilities/log_safety.redact()` |

Secrets are only ever read from environment variables (`.env`, which is git-ignored).
Use `scripts/make_release_zip.sh` to share source code: it is built with `git archive`, so
untracked files such as `.env` can never be included.

## Accepted vulnerabilities and exceptions

Each exception has an owner, a reason and an end date. CI ignores **only** the IDs listed here.

| ID | Package | Reason it is accepted | Ends |
|---|---|---|---|
| PYSEC-2026-311, PYSEC-2026-3814 | chromadb 1.5.9 | Code injection through the Chroma **server** API with `trust_remote_code`. We use Chroma only as an embedded library (no Chroma server is exposed) and never enable `trust_remote_code`. No fixed release exists. | Phase B (010.3): Chroma is replaced by Qdrant |
| PYSEC-2026-3813, PYSEC-2026-3815 | chromadb 1.5.9 | Missing tenant isolation in Chroma's own multi-tenant authorization. Not used: we filter by user in our code. This is a key reason for moving to Qdrant before multi-tenancy. | Phase B (010.3) |

| Licence exception | Reason | Ends |
|---|---|---|
| mysqlclient (GPL-2.0-or-later) | Accepted for the hosted SaaS, where the software is not distributed to customers. Must be replaced by PyMySQL (MIT) before any self-hosted / on-prem distribution. | Before any on-prem release |

## Incident log

| Date | Incident | Action |
|---|---|---|
| 2026-11-19 | A project zip shared outside Git contained a `.env` with live OpenRouter and Tavily API keys (finding R1). The keys were never committed to Git (verified with gitleaks over the full history). | Keys to be rotated; `scripts/make_release_zip.sh` added; gitleaks added to CI and pre-commit. |
