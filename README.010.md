# Branch 010: `genai-chat-010-devops` 🚀

**Goal:**
To make the application ready for real-world deployment and fix the remaining architectural issues identified in the Enterprise Review. This branch focuses on **Security Hardening**, **critical bug fixes** and a first **automated test suite**.

> **Scope change (2026-11-20):** Dockerization and Celery background tasks were planned for this branch but were **not implemented**. They move to a separate branch, **`010.1-docker-celery`**. See [ROADMAP.md](ROADMAP.md).

---

## 📦 Release Notes: Branch 010 (2026-11-20)

### Summary
This release fixes bugs that broke the app for real users (downloads returned 404, users were logged out when the access token expired, a fresh clone had no chat tables), hardens authentication and logging, and adds the project's first `pytest` suite (27 tests). Finding IDs (H*, M*, R*) refer to the review tracker in [ROADMAP.md](ROADMAP.md#-review-findings-status-tracker).

### 🐞 Bug fixes
- **R2: Document download returned 404.** The owner-checked `DownloadDocumentAPIView` had no URL route. Added `GET /api/download/<document_id>`.
- **R3: Users were logged out after the access token expired.** The frontend had no refresh logic. `fetchWithAuth` now refreshes the token on 401 and retries once; parallel requests share a single refresh call.
- **M4: `chunk_count` was always about 1.** The RAG engine now returns `(message, chunk_count)` and the real count is saved.
- **R13: A fresh clone had no chat tables.** `chat/migrations/0001_initial.py` was never committed; it is now in Git.
- **R15: Failed or empty uploads left files on disk.** The DB row *and* the file are now deleted when processing fails or nothing could be indexed (the API returns `422`).
- **R15: The upload success message linked to `/media/…`,** which is not served in production. It now uses the authenticated download API.
- Rate limiter: two requests in the same instant overwrote each other in the Redis sorted set; both are now counted.
- Frontend: a wrong argument in `addMessage()` for the upload "typing" bubble.

### 🔐 Security
- **H6: Chat history is no longer trusted from the client.** The non-stream `POST /api/chat` now loads history from the DB, like the streaming endpoint already did. The `history` field was removed from `ChatRequest`.
- **H8: No user text in logs.** Prompts, search queries, tool arguments and cache keys are logged only as `<length + short hash>` via `chat/utilities/log_safety.redact()`. Set `LOG_USER_CONTENT=1` to see the real text (only works when `DEBUG` is on).
- **M5: JWT and Django hardening.**
  - `SIMPLE_JWT`: 30-minute access tokens, 7-day refresh tokens, refresh-token rotation with blacklisting.
  - New `POST /api/auth/logout` blacklists the refresh token.
  - `AUTH_PASSWORD_VALIDATORS` are enforced on register, and the email format is checked.
  - `X-Frame-Options: DENY`, `nosniff`, `same-origin` referrer policy.
  - Secure cookies when `DEBUG` is off; HTTPS redirect and HSTS can be switched on by env var.
- **R11: Brute-force protection.** Per-IP rate limit on login, register and token refresh (`AUTH_RATE_LIMIT`, default 10 per window). `X-Forwarded-For` is trusted only when `TRUST_X_FORWARDED_FOR=1`.
- **R4: XSS through file names.** File names are now inserted with DOM APIs (`textContent`), never as HTML.
- **R14: User uploads could be committed.** `media/` was missing from `.gitignore`; it is now ignored.
- **R1: Secrets in shared zips.** New `scripts/make_release_zip.sh` builds the zip with `git archive`, so `.env`, `db.sqlite3`, `media/`, `logs/` and ChromaDB data are never included. ⚠️ **The OpenRouter and Tavily keys that were in an earlier zip must be rotated by hand.**

### ✨ Improvements
- **R5: Duplicate upload detection.** Each upload gets a SHA-256 `file_hash`. Uploading the same content again returns `409 Conflict` with the existing document, and the UI shows it as information with a download link. A data migration fills in hashes for existing uploads.
- Chat history for the LLM is loaded from only the 20 most recent messages instead of the whole session.
- `local_settings.py` is optional: if it is missing (fresh clone, CI), the committed `local_settings_example.py` is used.

### 🧪 Tests (new)
- `pytest` + `pytest-django` with `fakeredis`; the LLM is mocked, and tests use SQLite in memory (`config/settings_test.py`), so no MySQL, Redis, Ollama or API key is needed.
- 27 tests in `tests/`:
  - download route and ownership
  - duplicate upload, chunk count, and cleanup on failure
  - DB-only history and session ownership
  - token refresh, rotation and logout
  - password validation and auth rate limits
  - log redaction and the rate limiter

### 🧹 Housekeeping
- `requirements.txt`: every package is pinned, and the duplicate `redis` entry is removed. New `requirements-dev.txt` for test tools.
- The stray `=0.3.0` file (created by an unquoted `pip install x>=0.3.0`) is removed and ignored in `.gitignore`.
- The chat history API no longer returns the internal storage path of documents.

### ⚠️ Breaking changes (API)

| Change | Who is affected | What to do |
|---|---|---|
| `history` removed from `POST /api/chat` and `/api/chat/stream` | API clients that sent history | Nothing; it is ignored. Send `session_id` to continue a chat. |
| `POST /api/upload` response: `file_url` removed; `document_id` and `chunk_count` added | Clients that used `file_url` | Download through `GET /api/download/<document_id>` with the JWT. |
| Upload of identical content now returns `409` | Clients that re-upload files | Treat `409` as "already uploaded"; the body contains `document_id`. |
| Upload that indexes nothing now returns `422` (previously `200`) | Clients | Show the `detail` message. |
| Weak passwords are rejected on register | New users | Use at least 8 characters, not only numbers, not a common password. |
| Refresh tokens rotate: each refresh returns a **new** refresh token, and the old one stops working | Custom clients | Store the new `refresh` from every refresh response. |

### 🔧 Upgrade steps
1. Rotate the OpenRouter and Tavily API keys and update `.env`.
2. Delete the stray `=0.3.0` file from the project root, if present.
3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt   # optional, for tests
   ```

4. Apply the migrations. This adds `file_hash`, backfills it, and creates the token blacklist tables:

   ```bash
   python manage.py migrate
   ```

5. Optional new environment variables:

   | Variable | Default | Purpose |
   |---|---|---|
   | `JWT_ACCESS_MINUTES` | `30` | Access token lifetime |
   | `JWT_REFRESH_DAYS` | `7` | Refresh token lifetime |
   | `AUTH_RATE_LIMIT` | `10` | Login / register / refresh attempts per IP per window |
   | `LOG_USER_CONTENT` | `0` | Log real user text (DEBUG only) |
   | `DJANGO_SECURE_SSL_REDIRECT` | `0` | Redirect HTTP to HTTPS (when `DEBUG` is off) |
   | `DJANGO_SECURE_HSTS_SECONDS` | `0` | HSTS (when `DEBUG` is off) |

6. Run the tests:

   ```bash
   pytest
   ```

7. Hard-refresh the browser (Ctrl+Shift+R) so the new `app.js` is loaded.

### 🧭 Known issues / not in this release
- **Docker Compose and Celery** → `010.1-docker-celery`. PDF processing is still synchronous, so a large PDF can still make the upload request slow.
- The tests run on SQLite. Verify the migrations once on MySQL.
- The JWT is still stored in `localStorage` (httpOnly cookie is listed under "Ideas not yet scheduled" in the ROADMAP).
- **H4** is only partly fixed: web results are wrapped in `<untrusted_web_data>`, but the keyword filter is easy to bypass, and the user's query (which may contain personal data) is still sent to Tavily. This continues in 012.

---

## 🚨 Security fixes carried over from the Enterprise Review

### 1. Missing Dependencies (H3) ✅
- **The Issue:** A fresh machine could not start the app because `rank-bm25` and the MySQL driver (`mysqlclient`) were missing from `requirements.txt`.
- **The Solution:** Added and pinned all dependencies (including `rank-bm25`, `mysqlclient`, `redis`, `tavily-python`) in `requirements.txt`.

### 2. Web Search Prompt Injection (H4) 🟡 Partly fixed
- **The Issue:** Search results from Tavily were injected directly into the prompt. A malicious webpage could contain instructions to hijack the AI.
- **The Solution so far:**
  - Search results are wrapped in `<untrusted_web_data>` tags.
  - A basic filter drops pages containing obvious injection patterns (for example "ignore previous instructions").
- **Still open:** the keyword filter is weak, and private data in queries still goes to Tavily → Branch 012.

### 3. Rate Limiter Fail-Open (H9) ✅
- **The Issue:** If Redis went down, the rate limiter let every request through, allowing unlimited LLM API calls (cost explosion).
- **The Solution:** The rate limiter now **fails closed**. If Redis is unavailable, requests are blocked with `429 Too Many Requests`.

---

## 🛠️ Planned for this branch, moved to `010.1-docker-celery`

### 1. Docker Compose (M6) 🐳 ⏳
- **`Dockerfile`**: multi-stage build for the Django app (served with uvicorn).
- **`docker-compose.yml`**: Django, MySQL, Redis and Ollama, started with one command.

### 2. Celery Background Tasks (M6) ⏳
- **The Issue:** Uploading a large PDF blocks the request, because chunking and embedding run synchronously.
- **The Plan:** move PDF processing to a **Celery worker**. The API returns at once, and the UI shows a "Processing…" status until the document is ready.

### 3. Tests (M6) ✅ (done in 010, see Release Notes)

---

## 🚀 Next Steps (Branch 011: `genai-chat-011-tool-registry`)
- [ ] **H5 (Tool Call Protocol):** add the missing `type: function`, guard `json.loads`, and support multiple tool rounds through a tool registry.
- [ ] **R6 (Semantic cache, part 1):** do not cache web-search answers; invalidate a user's cache after an upload.
- [ ] **R10 (Async):** stop blocking the event loop with sync RAG / embedding / Tavily calls.
- [x] ~~**H8 (PII Logs)**~~: done in 010.
- Moved to Branch 013: **H7** (token budget), **M1** (reranker), **M3** (BM25 cache).

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस branch का मकसद:**
App को deployment के लिए तैयार करना, Enterprise Review में बची security खामियाँ ठीक करना और पहला automated test suite जोड़ना।

**Scope में बदलाव:** Docker Compose और Celery इस branch में नहीं बन पाए। ये अब अलग branch `010.1-docker-celery` में होंगे।

**Release Notes (2026-11-20): मुख्य बदलाव**

*Bug fixes:*
- **R2:** Document download पर 404 आता था, क्योंकि URL route नहीं था। अब `GET /api/download/<id>` काम करता है।
- **R3:** Access token expire होते ही user logout हो जाता था। अब frontend अपने आप token refresh करता है।
- **M4:** `chunk_count` हमेशा लगभग 1 आता था, अब सही संख्या save होती है।
- **R13:** `0001_initial.py` migration git में commit ही नहीं हुई थी, इसलिए fresh clone पर chat tables नहीं बनती थीं। अब यह commit है।
- **R15:** Upload fail होने पर file disk पर पड़ी रह जाती थी। अब DB row के साथ file भी delete होती है।

*Security:*
- **H6:** Chat history अब हमेशा DB से आती है, client की भेजी history पर भरोसा नहीं किया जाता।
- **H8:** Logs में user का text नहीं जाता, सिर्फ उसकी length और hash।
- **M5:**
  - 30 मिनट का access token और 7 दिन का refresh token, rotation और blacklist के साथ
  - नया logout endpoint
  - मज़बूत password की जाँच
  - security headers
- **R11:** Login, register और refresh पर per-IP rate limit, ताकि brute force न हो सके।
- **R4:** File के नाम से XSS का रास्ता बंद।
- **R14:** `media/` अब `.gitignore` में है।
- **R1:** Zip बनाने के लिए `scripts/make_release_zip.sh`। ⚠️ पुरानी API keys हाथ से rotate करनी होंगी।

*Improvements:*
- **R5:** एक ही file दोबारा upload करने पर `409` मिलता है (SHA-256 hash से पहचान)।
- `local_settings.py` न हो तो `local_settings_example.py` इस्तेमाल होती है।

*Tests:* 27 `pytest` tests जोड़े गए। इनके लिए MySQL, Redis या LLM की ज़रूरत नहीं है।

**⚠️ Breaking changes:**
- API में `history` field अब ignore होती है।
- Upload response से `file_url` हट गया; अब download `document_id` से होता है।
- Duplicate upload पर `409` आता है।
- कमज़ोर password reject होते हैं।
- हर refresh पर नया refresh token मिलता है।

**Upgrade के steps:**
1. API keys rotate करें।
2. `=0.3.0` file delete करें।
3. `pip install -r requirements.txt` चलाएँ।
4. `python manage.py migrate` चलाएँ।
5. `pytest` चलाएँ।
6. Browser को hard-refresh करें।

**अभी बाकी:**
- Docker और Celery (`010.1` में)।
- MySQL पर migration की जाँच।
- H4 का बाकी हिस्सा (012 में)।

**अगला कदम (Branch 011):** Tool registry, tool-call protocol (H5), semantic cache के सुधार (R6) और async fixes (R10)।

</details>
