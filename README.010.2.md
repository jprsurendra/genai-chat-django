# Branch 010.2: `genai-chat-010.2-ci-quality` 🛡️

**Goal:**
Phase A of the "lead-architect" plan: build the engineering safety net that every later change
depends on. CI, code quality, supply-chain security and repository governance, so that the product
can be developed, audited and sold professionally.

> **Context (2026-11-22):** `010.1-docker-celery` is on hold. Product decisions taken for the
> next phases: **multi-tenant SaaS**, **Qdrant** as the vector store, **GitHub Actions** for CI.
> Order of work: **A (this branch) → B (architecture + tenancy) → C (architecture docs) → D (security & data)**.
> See [ROADMAP.md](ROADMAP.md).

---

## 🎯 What we do in this branch, and why

The app works, but nothing *protects* it. There are tests that nobody runs automatically, no check stops
a secret or a vulnerable library from being merged, the frontend depends on third-party CDNs, and the
README says the code is MIT-licensed, although it is meant to be sold. Every later phase (architecture,
multi-tenancy, Qdrant, agents) will change a lot of code; without a safety net those changes would be
risky. So this branch comes **first**.

| # | What | Why (the problem it solves) |
|---|---|---|
| 1 | **CI pipeline on GitHub Actions** (lint, types, tests, deploy check, security) on every push and pull request | 27 tests existed but ran only when someone remembered. Branch 010 showed the cost: the initial migration was never committed (R13), so a fresh clone had no chat tables. CI turns such mistakes into a red build instead of a production outage. |
| 2 | **Tests on real MySQL 8.4**, not only SQLite | SQLite hides MySQL-specific problems (collation, strictness, versions). Django 6.1 refuses MySQL older than 8.4 (R18); only a real MySQL job proves the migrations work. |
| 3 | **ruff (lint + format + security rules), mypy, coverage floor** | One code style for everyone, bugs and insecure patterns (bandit `S` rules) caught before review, and a coverage number that can only go up. Legacy modules are handled with a "ratchet" so the build is green today and gets stricter over time. |
| 4 | **Secret scanning (gitleaks) in CI and pre-commit** | Real API keys already leaked once through a shared zip (R1). Scanning the full history proves nothing was committed, and the hook stops it from happening in future. |
| 5 | **Dependency vulnerability scan (pip-audit) + Dependabot** | Known CVEs arrive in libraries without anyone noticing. The first scan immediately found three in `pypdf`, the library that parses users' uploaded PDFs (R17). |
| 6 | **Licence policy, proprietary `LICENSE`, `THIRD_PARTY_LICENSES.md`** | The README declared **MIT**, which lets anyone resell the code (R19). Buyers and investors run licence due diligence; we must know every dependency licence and block strong copyleft (GPL/AGPL) automatically. |
| 7 | **Self-hosted frontend libraries + Content-Security-Policy** | `marked` was loaded from a CDN **without a version**: the app silently changed whenever the CDN did. CDNs are also an availability and supply-chain risk. A strict CSP is the main defence against XSS while the JWT lives in `localStorage` (R22). |
| 8 | **Tests for the AI tools and frontend rules** | The calculator and web-search tools (security-critical: DoS, prompt injection) had 19% test coverage. Writing these tests found a new memory-DoS bug (R16). |
| 9 | **Production settings check (`check --deploy`, `collectstatic`)** | Mis-configured production settings (HSTS, cookies, static files) are found in CI, not after the first deployment. |
| 10 | **`SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, PR template** | A product that is sold needs a vulnerability-reporting process, a written Definition of Done, and a release history that customers and auditors can read. |

**Out of scope for this branch** (each has its own branch, see [ROADMAP.md](ROADMAP.md)):
- Docker Compose and Celery → `010.1-docker-celery` (on hold)
- Layered architecture, multi-tenancy, Qdrant, API v1, architecture docs → `010.3-architecture`
- RBAC, threat model, retention and backups → `010.4-security-data`

**The branch is done when:** CI is green on GitHub with all four jobs, `pre-commit run --all-files`
passes, no CDN or inline code remains in the templates, the licence and security documents exist, and
every finding fixed here (R16, R17, R19, R22, R23) has a test or an automated check.

---

## 📦 Release Notes: Branch 010.2 (2026-11-22)

### Summary
Every push and pull request now runs a full CI pipeline: lint, types, tests on SQLite **and** MySQL 8.4,
a production-settings check, secret scanning, vulnerability scanning and a licence policy. The
frontend no longer depends on any CDN and is protected by a strict Content-Security-Policy. Two
security bugs were found and fixed while adding tests. The repository now has the legal and process
documents a buyer or auditor expects.

### 🔄 CI pipeline (`.github/workflows/ci.yml`)

| Job | What it checks |
|---|---|
| **lint** | `ruff check`, `ruff format --check`, `mypy`, `node --check` for all JS |
| **test** | `makemigrations --check`, `pytest --cov` on Python 3.13 + 3.14 (SQLite) and on **MySQL 8.4** (with real migrations); coverage report artifact |
| **deploy-check** | `check --deploy --fail-level WARNING` with production settings, `migrate` and `collectstatic` (manifest storage) on MySQL |
| **security** | gitleaks over the **full** git history (binary verified by SHA-256), `pip-audit`, licence policy (fails on GPL/AGPL/SSPL/EUPL except documented exceptions) |

- All third-party actions are **pinned to commit SHAs**; Dependabot proposes updates weekly
  (pip and GitHub Actions, grouped).
- The workflow was validated with `actionlint`.

### 🧹 Code quality
- `pyproject.toml` configures **ruff** (pycodestyle, pyflakes, isort, bugbear, pyupgrade, **bandit security rules**,
  Django, comprehensions, simplify), **mypy** and **coverage**.
- The code base was formatted once with ruff and all lint findings were fixed.
- **mypy ratchet:** clean modules are checked strictly; three legacy modules (`llm.py`, `rag_engine.py`,
  `evaluate_rag.py`) are temporarily ignored and must leave the list when they are rewritten (011 / 013).
- **Coverage floor 55%** (currently 56%): CI fails if coverage drops. Raise it as coverage grows.
- **pre-commit** runs ruff, whitespace fixes (Markdown-safe), YAML/TOML checks, private-key detection,
  gitleaks and the migration check before every commit.

### 🔐 Security fixes
- **pypdf 6.21.3 → 6.21.4.** Three CVEs (CVE-2026-119203/119204/119205): a crafted PDF could cause
  an infinite loop or huge memory use. Users upload PDFs, so this was a direct denial-of-service path.
- **Calculator memory DoS.** The tool accepted string constants: `"a" * 10**10` passed the exponent
  check and tried to allocate ~10 GB. Only real numbers (not booleans) are accepted now.
- **Content-Security-Policy** (Django 6 built-in `SECURE_CSP`): `script-src 'self'`, `style-src 'self'`,
  `object-src 'none'`, `frame-ancestors 'none'`, no `unsafe-inline`. This is the main defence if an XSS
  bug ever appears, because the JWT is stored in `localStorage`.
- **No CDN.** Bootstrap 5.3.9, Bootstrap Icons 1.13.2, marked 18.2.1 (was loaded **without a version**,
  i.e. whatever the CDN served that day) and DOMPurify 3.4.18 are now in `static/vendor/<name>-<version>/`,
  with their licences and source maps.
- Inline login script/styles and all `style="..."` attributes moved to static files and CSS classes.
- Root `test_ratelimit.py` contained hardcoded credentials; it is now
  `scripts/manual/smoke_rate_limit.py` and reads `SMOKE_USERNAME` / `SMOKE_PASSWORD`.
- Example DB settings no longer contain a default password.
- gitleaks over the complete history: **no secrets were ever committed** (the R1 keys were only in a zip).

### ⚖️ Legal and governance
- **`LICENSE` is now proprietary** (all rights reserved). The README previously said **MIT**, which
  would have allowed anyone to use and resell the code. Fill in the copyright holder and contact email.
- `THIRD_PARTY_LICENSES.md` (generated by `scripts/generate_third_party_licenses.sh`): 4 frontend
  libraries + all runtime Python packages including transitive ones.
- `SECURITY.md`: reporting process, controls, **accepted vulnerabilities with end dates**, incident log.
- `CONTRIBUTING.md`: setup (incl. IntelliJ), branch and commit conventions, Definition of Done.
- `CHANGELOG.md` (Keep a Changelog), pull-request template, `CODEOWNERS` placeholder.

### 🧪 Tests
51 tests (24 new): calculator safety (incl. code-execution and DoS attempts), web search
(untrusted wrapper, injection filter, errors), CSP header, "no external assets", "no inline code",
and production `collectstatic`. The app was also checked in headless Chrome under the CSP:
login, tabs, icons, markdown + DOMPurify, layout, **no console errors**.

### 🧹 Other changes
- Dead code removed: `chat/views/chat_ui_views.py`, `templates/chat/index.html`.
- `sample_env.txt` rewritten: every setting once, with its default and a comment.
- Empty `OPENAI_BASE_URL` now means "provider default" (it was passed as `""`).
- `local_settings_example.py`: `utf8mb4`, `CONN_MAX_AGE`, `CONN_HEALTH_CHECKS`.
- README: Django version corrected (6.1, not 5.x), licence section updated.

### ⚠️ Important findings (action needed)

| # | Finding | What to do |
|---|---|---|
| 1 | **Django 6.1 requires MySQL 8.4 or later.** With MySQL 8.0 the app refuses to connect (verified). | Check your server: `SELECT VERSION();`. Upgrade to MySQL 8.4 LTS if it is older. |
| 2 | **`mysqlclient` is GPL-2.0-or-later.** Fine for a hosted SaaS (no distribution), but buyers' due diligence will ask, and it blocks an on-prem edition. | Decide: keep it for now (documented exception) or switch to PyMySQL (MIT). |
| 3 | **Earlier code was published as MIT.** Anyone who already received a copy may keep using it under MIT. | Make the GitHub repository **private** now; future versions are proprietary. Ask a lawyer if the repo was public. |
| 4 | **chromadb** has 4 unfixed vulnerabilities, two of them about tenant isolation. | Accepted until Phase B replaces Chroma with Qdrant. |
| 5 | Placeholders in `LICENSE`, `SECURITY.md`, `CODEOWNERS`. | Fill in the legal owner, contact emails and GitHub username. |

### 🔧 Upgrade steps
1. Apply the patch (IntelliJ: **Git → Patch → Apply Patch…**) on top of the 010 changes.
2. `pip install -r requirements-dev.txt`
3. `pre-commit install`
4. Hard-refresh the browser (Ctrl+Shift+R): the frontend now loads from `static/vendor/`.
5. On GitHub: **Settings → Branches → Add rule** for `main`: require a pull request, require the
   status checks `Lint & type check`, `Tests (...)`, `Production settings check`, `Security scans`.
6. On GitHub: enable **Dependabot alerts** and **secret scanning** (Settings → Code security).

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस branch का मकसद:**
Phase A, यानी engineering की वह सुरक्षा-जाल जिस पर आगे का हर बदलाव टिका है: CI, code quality, supply-chain security और repository governance। इसके बाद product को professional तरीके से develop, audit और बेचा जा सकेगा।

**फैसले:** Multi-tenant SaaS, vector store के लिए Qdrant, और CI के लिए GitHub Actions। `010.1-docker-celery` अभी hold पर है।

**क्या करेंगे और क्यों:**
App काम करता है, पर उसकी कोई सुरक्षा नहीं है। Tests हैं पर कोई उन्हें अपने आप नहीं चलाता। कोई secret या vulnerable library merge होने से रोकने वाला कोई check नहीं है। Frontend बाहरी CDNs पर टिका है। README में MIT license लिखा है, जबकि product बेचना है। आगे के phases (architecture, multi-tenancy, Qdrant, agents) बहुत सारा code बदलेंगे, और safety net के बिना यह जोखिम भरा होगा। इसलिए यह branch **सबसे पहले** है।

1. **CI pipeline:** 010 में initial migration commit ही नहीं हुई थी (R13), और fresh clone पर tables नहीं बनती थीं। CI ऐसी गलती को production outage बनने से पहले red build में बदल देता है।
2. **असली MySQL 8.4 पर tests:** SQLite, MySQL की समस्याएँ छुपा देता है, और Django 6.1 को MySQL 8.4+ चाहिए (R18)।
3. **ruff, mypy और coverage floor:** सबके लिए एक code style, security वाली गलतियाँ review से पहले पकड़ी जाएँ, और coverage सिर्फ ऊपर जाए।
4. **Secret scanning (gitleaks):** API keys एक बार zip के ज़रिए leak हो चुकी हैं (R1)। आगे ऐसा दोबारा न हो।
5. **pip-audit और Dependabot:** पहले ही scan में `pypdf` की 3 CVEs मिलीं (R17), और यही library users की PDFs पढ़ती है।
6. **License policy और proprietary LICENSE:** MIT के तहत कोई भी code बेच सकता था (R19)। Buyers की due diligence के लिए हर dependency का license पता होना चाहिए।
7. **CDN हटाना और CSP:** `marked` बिना version के load होती थी, यानी CDN बदलते ही app का behaviour बदल जाता। JWT `localStorage` में है, इसलिए XSS के ख़िलाफ़ CSP सबसे ज़रूरी बचाव है (R22)।
8. **AI tools के tests:** Calculator और web search का coverage 19% था। Tests लिखते ही नया memory DoS bug मिला (R16)।
9. **Production settings check:** HSTS, cookies और static files की गलत settings deployment से पहले ही CI में पकड़ी जाएँ।
10. **SECURITY, CONTRIBUTING, CHANGELOG:** बिकने वाले product के लिए vulnerability reporting का तरीका, Definition of Done और release history ज़रूरी हैं।

**Scope से बाहर:** Docker और Celery (`010.1`), architecture और multi-tenancy (`010.3`), RBAC और backups (`010.4`)।

**Branch पूरी कब मानी जाएगी:** GitHub पर CI के चारों jobs green हों, `pre-commit` pass हो, templates में कोई CDN या inline code न हो, license और security docs मौजूद हों, और यहाँ fix हुई हर finding का test या automated check हो।

**CI pipeline (हर push और PR पर):**
- **lint:** ruff, mypy और JavaScript syntax check।
- **test:** Python 3.13 और 3.14 पर SQLite के साथ, और असली MySQL 8.4 पर भी।
- **deploy-check:** production settings पर `check --deploy`, `migrate` और `collectstatic`।
- **security:** पूरी git history में secrets की जाँच (gitleaks), dependencies में known vulnerabilities (pip-audit), और license policy।

**Security fixes:**
- `pypdf` की 3 CVEs ठीक कीं। Crafted PDF से server हमेशा के लिए अटक सकता था या memory भर सकती थी।
- Calculator में नया DoS bug मिला: `"a" * 10**10` से 10 GB memory माँगी जा सकती थी। अब सिर्फ numbers allow हैं।
- Strict Content-Security-Policy लगाई। CDN हटाया और सारी libraries pinned versions के साथ `static/vendor/` में रखीं। `marked` पहले बिना version के load होती थी।
- Root की `test_ratelimit.py` में hardcoded password था। अब वह script environment से credentials पढ़ती है।

**Legal:**
- README में **MIT** license लिखा था, जिससे कोई भी code मुफ़्त में इस्तेमाल करके बेच सकता था। अब `LICENSE` **proprietary** है।
- `THIRD_PARTY_LICENSES.md`, `SECURITY.md`, `CONTRIBUTING.md` और `CHANGELOG.md` जोड़े गए।

**Tests:** अब 51 tests हैं (24 नए) और coverage 56% है। CI coverage 55% से नीचे गिरने नहीं देगा। Browser में CSP के साथ app चलाकर जाँचा गया, कोई error नहीं आया।

**⚠️ आपके लिए ज़रूरी बातें:**
1. Django 6.1 को **MySQL 8.4+** चाहिए। MySQL 8.0 पर app चलेगा ही नहीं। अपना version जाँचें।
2. `mysqlclient` का license GPL है। SaaS में यह चल जाता है, पर on-prem बेचने से पहले PyMySQL पर जाना होगा।
3. पहले code MIT license में था। GitHub repo को अभी **private** कर दें।
4. `LICENSE`, `SECURITY.md` और `CODEOWNERS` में owner का नाम, email और GitHub username भरें।
5. GitHub पर `main` branch protection और Dependabot alerts चालू करें।

**अगला कदम:** Phase B (`010.3-architecture`)। इसमें layered modules, multi-tenancy (Organization, Membership, Roles), `LLMGateway` और `VectorStore` interfaces, ChromaDB से Qdrant पर जाना, typed settings, standard error model, `/api/v1`, health checks और structured logging आएँगे।

</details>
