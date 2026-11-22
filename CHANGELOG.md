# Changelog

All notable changes to GenAI Chat are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Each release matches one roadmap branch;
the full notes for a branch are in its `README.<NNN>.md` file.

Finding IDs (R1, H6, M4, ...) refer to the review tracker in [ROADMAP.md](ROADMAP.md).

## [Unreleased] – Branch 010.2 `genai-chat-010.2-ci-quality`

Full notes: [README.010.2.md](README.010.2.md)

### Added
- GitHub Actions CI: ruff, mypy, JavaScript syntax, pytest + coverage on SQLite (Python 3.13 and 3.14)
  and on MySQL 8.4, `check --deploy`, `collectstatic`, gitleaks, pip-audit and a licence policy.
- `pre-commit` hooks, Dependabot (pip + GitHub Actions), `pyproject.toml` tool configuration.
- Content-Security-Policy (Django built-in), SVG favicon.
- `LICENSE` (proprietary), `THIRD_PARTY_LICENSES.md` + generator script, `SECURITY.md`,
  `CONTRIBUTING.md`, pull-request template, `CODEOWNERS` placeholder.
- 24 new tests (51 in total): calculator and web-search tools, CSP and frontend rules, production static files.

### Changed
- Frontend libraries are self-hosted and pinned in `static/vendor/` (Bootstrap 5.3.9,
  Bootstrap Icons 1.13.2, marked 18.2.1, DOMPurify 3.4.18) instead of being loaded from a CDN.
- Login page script and styles moved to `static/web_ui/login.js` / `login.css`; no inline code remains.
- `pypdf` 6.21.3 → 6.21.4.
- The whole code base is formatted with ruff.
- `sample_env.txt` lists every setting exactly once, with defaults.
- `local_settings_example.py`: `utf8mb4`, persistent DB connections, no default DB password.

### Fixed
- **Security:** crafted PDFs could cause an infinite loop or very high memory use in `pypdf`
  (CVE-2026-119203, CVE-2026-119204, CVE-2026-119205).
- **Security:** the calculator tool accepted string constants, so `"a" * 10**10` could exhaust server memory.
- An empty `OPENAI_BASE_URL` was passed to the client as `""` instead of the provider default.
- Exception chaining in the rate limiter (`raise ... from e`).

### Removed
- Dead code: `chat/views/chat_ui_views.py` and `templates/chat/index.html` (not routed; they referenced
  static files that do not exist).
- `test_ratelimit.py` from the project root, with its hardcoded credentials. It is now
  `scripts/manual/smoke_rate_limit.py` and reads credentials from environment variables.

### Security notes
- Known `chromadb` vulnerabilities without a fix are documented as accepted until Chroma is replaced
  by Qdrant (Phase B). See `SECURITY.md`.

## [010] – 2026-11-20 – `genai-chat-010-devops`

Full notes: [README.010.md](README.010.md)

### Fixed
- Download route missing (R2), logout on token expiry (R3), wrong `chunk_count` (M4), uncommitted
  initial migration (R13), files left on disk after failed uploads (R15).

### Security
- History only from the DB (H6), no user text in logs (H8), JWT rotation and blacklist, password
  validation and security headers (M5), per-IP auth rate limits (R11), filename XSS (R4),
  `media/` ignored by Git (R14), release zips built with `git archive` (R1).

### Added
- Duplicate-upload detection by SHA-256 (R5), logout endpoint, first `pytest` suite (27 tests).

### Changed (breaking)
- `history` removed from chat requests; upload response returns `document_id` instead of `file_url`;
  duplicate uploads return `409`; empty uploads return `422`; refresh tokens rotate.

## Earlier releases

Dates for these branches were not recorded. See each branch README for details.

| Branch | Summary | Notes |
|---|---|---|
| 009 `production-ui` | Production UI, dark mode, Redis semantic cache, review fixes H1/H2/H3/H6/H9 | [README.009.md](README.009.md) |
| 008 `agent-tools` | Function calling: calculator and Tavily web search; OpenRouter support | [README.008.md](README.008.md) |
| 007 `security-hardening` | Owner-checked downloads, prompt-injection defence, Redis rate limiting, full data erasure | [README.007.md](README.007.md) |
| 006 `rag-quality` | Hybrid search (BM25 + vector), query rewriting, RAG evaluation | [README.006.md](README.006.md) |
| 005 `db-auth` | MySQL, JWT login and registration, file storage | [README.005.md](README.005.md) |
| 004 `clean-up` | Session isolation, "show sources" | [README.004.md](README.004.md) |
| 003 `rag` | Embeddings, ChromaDB, PDF upload | [README.003.md](README.003.md) |
| 002 `system-prompt` | System prompt and the assistant's identity | [README.002.md](README.002.md) |
| 001 `basic` | Streaming chatbot (Django + Ollama) | [README.md](README.md) |
