# GenAI Chat: Roadmap

This document tracks what has been built so far and what is planned next. The project started as a small streaming chatbot and has grown into a multi-user app with login, a database, hybrid RAG, file upload, tool calling and a semantic cache. Each step lives in its own branch (see [Branch History](README.md#13-branch-history) in the main README for the Git workflow).

> The plan below is a working plan, not a promise. Branches may be reordered or split as we learn what actually matters.

_Last updated: 2026-11-19, after the code review of branch `010-devops` (see "Review findings" below)._

---

## At a glance

| Branch | Main feature | Status |
|--------|--------------|--------|
| `001-basic` | Streaming chatbot (Django + Ollama) | ✅ Done |
| `002-system-prompt` | System prompt and the AI's identity | ✅ Done |
| `003-rag` | Embeddings, ChromaDB, PDF upload | ✅ Done |
| `004-clean-up` | Session isolation, show sources | ✅ Done |
| `005-db-auth` | MySQL, JWT login, file storage | ✅ Done |
| `006-rag-quality` | Hybrid search, query rewriting, evaluation (reranking carried over) | ✅ Done |
| `007-security-hardening` | Owner-checked downloads, prompt injection defense, Redis rate limiting, complete data erasure | ✅ Done |
| `008-agent-tools` | Function calling: calculator + web search (Tavily), OpenRouter support | ✅ Done (single tool round; see H5) |
| `009-production-ui` | Production UI, dark mode, semantic cache (Redis), review fixes H1/H2/H3/H6/H9 | ✅ Done |
| `010-devops` | Critical bug fixes, Docker Compose, Celery, first tests | 🚧 In progress |
| `011-tool-registry` | Tool registry, multi-round tool loop, streamed tool answers | ⏭️ Next up |
| `012-mcp-client` | Connect external MCP servers (web search, read-only DB, drive) | ⏳ Upcoming |
| `013-multi-agent` | Supervisor + specialist agents, critic, memory agent, token budget | ⏳ Upcoming |
| `014-mcp-server` | Expose our RAG as an MCP server (Claude Desktop, IDEs) | ⏳ Upcoming |
| `015-eval-observability` | Larger eval set, CI evals, Langfuse tracing, feedback | ⏳ Upcoming |
| `016-voice-ui` | Voice, vision, Hindi UI | 💭 Future (optional) |

> **Renumbering note:** the old plan had `009-production` and `010-voice-ui`. Production work was split between `009-production-ui` and `010-devops`, and voice/vision moves to `016`.

---

## Where we are now

The app has login, chat history in MySQL, document upload, a hybrid RAG engine (vector + BM25, Hindi-aware tokenizer), query rewriting, a Redis rate limiter that fails closed, a Redis semantic cache, and two tools (calculator and Tavily web search).

**Current task:** Branch 010. The code review found that some items described in `README.010.md` are **not in the code yet**: there is no `Dockerfile`, no `docker-compose.yml`, no Celery worker, and the `tests.py` files are empty. The review also found several bugs that must be fixed before deployment (see Branch 010 below).

After Branch 010, the work moves from "chatbot with tools" to **agents**: a proper tool registry (011), MCP (012), multi-agent orchestration (013), our own MCP server (014), and measurement (015).

---

## 🔍 Review findings (status tracker)

IDs H1 to M6 come from the Production Architecture Review in `README.009.md`. IDs R1 onwards are new findings from the 2026-11-19 code review.

| ID | Severity | Finding | Status / Branch |
|----|----------|---------|-----------------|
| H1 | High | BM25 blind to Hindi, could crash | ✅ Fixed (009) |
| H2 | High | Calculator exponent DoS | ✅ Fixed (009) |
| H3 | High | Missing `rank-bm25` / MySQL driver | ✅ Fixed (009) |
| H4 | High | Web search: prompt injection + private data sent to Tavily; sync client in async path | 🟡 Partly fixed → finish in 012 (MCP + redaction) |
| H5 | High | Tool-call protocol incomplete (one round, missing `type`, unguarded `json.loads`) | ⏳ 011 |
| H6 | High | Chat history trusted from client | 🟡 Fixed in streaming view only; non-stream `ChatAPIView` still uses `req.history` → 010 |
| H7 | High | No token accounting or daily quota | ⏳ 013 |
| H8 | High | Real user text written to INFO logs | ⏳ 010 |
| H9 | Medium | Rate limiter fail-open | ✅ Fixed (009) |
| M1 | Medium | No reranker | ⏳ 013 |
| M2 | Medium | No cache | 🟡 Semantic cache done; its risks (R6) → 011 / 013 |
| M3 | Medium | BM25 rebuilt per query; >1000 chunks silently ignored | ⏳ 013 |
| M4 | Medium | `chunk_count` always about 1 | ⏳ 010 |
| M5 | Medium | `SIMPLE_JWT`, `SECURE_*` headers, password validators | ⏳ 010 |
| M6 | Medium | No Docker, CI or tests | ⏳ 010 (Docker, tests), 015 (CI evals) |
| R1 | Critical | Real API keys inside the shared `.env` in the project zip | ⏳ 010: rotate keys, package with `git archive` |
| R2 | High | `DownloadDocumentAPIView` has no URL route, so downloads return 404 | ⏳ 010 |
| R3 | High | No JWT refresh in the frontend; users are logged out when the access token expires | ⏳ 010 |
| R4 | Medium | Filename inserted into `innerHTML` without escaping (`app.js`) | ⏳ 010 |
| R5 | Medium | Same file can be uploaded many times (no hash dedup) | ⏳ 010 |
| R6 | Medium | Semantic cache ignores conversation context, caches web-search answers for 24h, is not invalidated on upload, and scans all entries (O(n)) | ⏳ 011 (tool answers, invalidation), 013 (key on standalone query) |
| R7 | Medium | Documents and memories are user-wide, so a PDF uploaded in chat A appears in chat B | ⏳ 013 |
| R8 | Medium | Memory stores every non-question message ("ok", "thanks") | ⏳ 013 (memory agent) |
| R9 | Medium | Hybrid score uses arbitrary `bm25/5.0` normalization and a hardcoded `0.35` threshold | ⏳ 013 (Reciprocal Rank Fusion) |
| R10 | Medium | Sync RAG / embedding / Tavily calls block the async event loop | ⏳ 011 (`asyncio.to_thread`) |
| R11 | Low | No rate limit on login/register | ⏳ 010 |
| R12 | Low | Housekeeping: stray `=0.3.0` file, duplicate `redis` in `requirements.txt`, unused `pydantic-settings`, repeated `extra_headers` | ⏳ 010 |

---

## ✅ Branch 007: `genai-chat-007-security-hardening` (done)

- **Secure media files:** ✅ the public `/media/` route is removed (only served when `DEBUG`), and a download API checks the file's owner. ⚠️ Its URL route is missing (R2), fixed in 010.
- **Prompt injection defense:** ✅ retrieved text is treated as data only.
- **Redis rate limiting:** ✅ per user for chat, upload and clear, and fails closed. Login/register limits move to 010 (R11).
- **Data erasure:** ✅ "Clear All" deletes from MySQL, disk and ChromaDB.

## ✅ Branch 008: `genai-chat-008-agent-tools` (done)

- **Calculator** and **web search (Tavily)** tools with function calling.
- OpenRouter support through `OPENAI_BASE_URL`.
- Limits carried forward: only one tool round, the final answer after a tool call is not streamed, and tools exist only in the streaming path (H5, fixed in 011). The **database query** tool was not built; it moves to 012 as a read-only MCP server.

## ✅ Branch 009: `genai-chat-009-production-ui` (done)

- Production UI with dark mode, chat sidebar, rename/delete chats.
- Redis **semantic cache**.
- Review fixes H1, H2, H3, H6 (streaming path), H9.

---

## 🚧 Branch 010: `genai-chat-010-devops` (in progress)

**Goal:** fix what is broken today and make the app deployable with one command.

**Scope**

- **R1:** rotate the OpenRouter and Tavily keys; add a packaging script that uses `git archive`, so `.env`, `db.sqlite3`, `media/`, `logs/`, `.idea/` and `chroma_db/` never leave the machine.
- **R2:** add `path("download/<int:document_id>", DownloadDocumentAPIView.as_view())` to `chat/urls.py`.
- **R3 + M5:** add `SIMPLE_JWT` settings (for example 30 min access, 7 days refresh), a `TokenRefreshView` route, and refresh-then-retry on 401 in `fetchWithAuth`; add `SECURE_*` headers and `AUTH_PASSWORD_VALIDATORS`; call `validate_password()` on register.
- **H6:** the non-stream `ChatAPIView` loads history from the DB; remove `history` from `ChatRequest`.
- **H8:** remove user text from INFO logs (structured logs without personal data).
- **M4:** `process_and_store_file` returns `(message, chunk_count)`.
- **R4:** escape `filename` in `renderDocumentBubble`.
- **R5:** add `UploadedDocument.file_hash` (SHA-256, unique per user) and reject duplicates.
- **R11:** per-IP rate limit on login and register.
- **R12:** remove `=0.3.0`, clean and pin `requirements.txt`.
- **M6:** `Dockerfile` + `docker-compose.yml` (Django on uvicorn, MySQL, Redis, Ollama); Celery worker for PDF ingestion with a "Processing…" status; first tests with `pytest-django`.

**Acceptance criteria**

- The download button returns the file, not 404.
- A user stays logged in after 30+ minutes of idle time.
- Uploading the same PDF twice says "already uploaded".
- `docker compose up` starts the whole stack.
- `pytest` passes: download ownership, login rate limit, duplicate upload, history comes from the DB.

---

## ⏭️ Branch 011: `genai-chat-011-tool-registry` (next)

**Goal:** replace the single-round, `if/elif` tool code with an extensible registry. This is the base for MCP and agents.

**Scope**

- `chat/tools/registry.py`: `Tool` dataclass (name, description, JSON schema, async handler, `requires_approval`, timeout) and a `ToolRegistry` with safe `execute()` (bad JSON, unknown tool, timeout, output size cap).
- Move `calculate` and `web_search` to `chat/tools/local/` and register them.
- `chat/agents/base.py`: a bounded multi-round tool loop (`max_iterations=5`) with correct `{"type": "function"}` assistant messages (**H5**).
- Stream the final answer after tool calls too; new SSE events `tool_start` / `tool_end`, with a "🔍 Searching…" chip in the UI.
- Use tools in the non-stream path as well, through the same loop.
- Wrap sync RAG, embedding and Tavily calls in `asyncio.to_thread` (**R10**).
- `ToolCallLog` model (user, tool, status, duration).
- Semantic cache (**R6**, part 1): do not cache web-search answers; invalidate the user's cache on upload.

**Acceptance criteria**

- "What is the weather in Delhi, and what is 25 × 17?" runs **both** tools in one turn.
- Malformed tool JSON or an unknown tool never crashes the stream.
- Adding a new local tool needs one file and one `register()` call, with no change to `llm.py`.

**Tests:** unknown tool, bad JSON, timeout, multi-round loop (mocked LLM), max-iterations stop.

---

## ⏳ Branch 012: `genai-chat-012-mcp-client`

**Goal:** discover and use tools from external **MCP (Model Context Protocol)** servers at runtime, configured instead of coded.

**Scope**

- Add the `mcp` Python SDK (pinned version).
- `config/mcp_servers.yaml`: list of servers (transport `stdio` or `streamable-http`, URL or command, headers from env vars, tool allowlist).
- `chat/tools/mcp/adapter.py`: convert MCP tool schemas to OpenAI function schemas and register them as namespaced tools (`server__tool`); wrap their output as untrusted data.
- `chat/tools/mcp/client_manager.py`: long-lived MCP sessions started at ASGI lifespan, with reconnect and backoff; MCP status in `/api/health`.
- Replace the local Tavily tool with a web-search MCP server (keep the local one as fallback); redact personal data from outgoing queries (**H4**).
- **Database query tool** (from the old Branch 008 plan) as a **read-only** MySQL MCP server, using a `genai_readonly` user that can only `SELECT` from chosen views.
- Basic `requires_approval` handling (refuse for now; the UI arrives in 013).

**Acceptance criteria**

- Adding a server to the YAML and restarting makes its tools available, with no Python change.
- If one MCP server is down, the app and the other tools keep working.
- `DELETE` / `UPDATE` through the DB tool fail.

**Candidate MCP servers:** web search and fetch, read-only MySQL/Postgres, filesystem (bulk ingestion), Google Drive / Notion / Confluence (company docs into RAG), GitHub (code Q&A), Slack / email (only with human approval).

**MCP security rules**

- Per-user tool allowlist.
- Human approval for any tool with side effects.
- Timeout, output size cap and audit log on every call.
- MCP output is always untrusted data in the `tool` role, never in the system prompt.
- Third-party servers run in containers.

---

## ⏳ Branch 013: `genai-chat-013-multi-agent`

**Goal:** a supervisor routes each request to a specialist agent, and a critic checks the answer.

```
User ─► Supervisor / Router (fast model: intent + standalone query)
          ├─► RAG Agent        (hybrid retrieve + rerank + citations)
          ├─► Research Agent   (web MCP, fetch, sources; parallel searches)
          ├─► SQL Agent        (read-only DB MCP, SELECT only)
          ├─► Math/Tool Agent
          └─► Chat Agent
                 ▼
          Critic / Verifier (groundedness + citations) ─► Answer
                 ▼
          Memory Agent (Celery, after the turn: extract facts only)
```

**Scope**

- Agents: `supervisor`, `rag_agent`, `research_agent`, `sql_agent`, `chat_agent`, `critic`; shared `AgentState` (pydantic).
- Start with a custom router; move to **LangGraph** in this branch if approvals, checkpoints or parallel fan-out are needed. (Alternatives considered: Pydantic AI, OpenAI Agents SDK.)
- Separate models per role: `ROUTER_MODEL`, `AGENT_MODEL`, `CRITIC_MODEL`, with a LiteLLM fallback chain. Small 1B models are not reliable here; the supervisor needs a tool-capable 7–8B model or a cloud model.
- **RAG upgrades:** Reciprocal Rank Fusion (**R9**), cached BM25 index (**M3**), cross-encoder reranker kept only if eval improves (**M1**), `chat_session_id` metadata with a "this chat only" filter (**R7**).
- **Memory agent** replaces "store every statement" (**R8**).
- Semantic cache keyed on the router's standalone query + route (**R6**, part 2).
- **Token budget and daily quota** per user (**H7**); `AgentRun` model (route, agents, tokens, cost, latency).
- UI: steps timeline (`route`, `agent_start` events), clickable citations, Approve/Reject card for `requires_approval` tools.

**Acceptance criteria**

- Routing accuracy ≥ 90% on a 20-query fixture.
- Document answers include citations; if the answer is not in the documents, the app says so instead of guessing.
- "Compare the policy in my PDF with today's RBI guideline" runs the RAG and Research agents together.
- With the filter on, a PDF from chat A does not appear in chat B.

---

## ⏳ Branch 014: `genai-chat-014-mcp-server`

**Goal:** expose our RAG as an MCP server, so Claude Desktop, Cursor, IntelliJ and other MCP clients can search a user's documents.

**Scope**

- `mcp_server/server.py` (FastMCP) with tools `search_documents`, `list_documents`, `get_chat_history`, `ask_with_rag`; resources `doc://{doc_id}`; prompts `summarize_document`, `qa_with_citations`.
- Transports: `stdio` for local IDEs, `streamable-http` for remote use behind Nginx.
- Auth: per-user API keys for the PoC (`UserAPIKey`, hashed, revocable); OAuth 2.1 for production.
- Audit log and per-key rate limit (reusing the Redis limiter); README config examples for Claude Desktop and IntelliJ.

**Acceptance criteria:** correct chunks and page numbers from Claude Desktop; one user's key never returns another user's data; a revoked key stops working at once.

---

## ⏳ Branch 015: `genai-chat-015-eval-observability`

**Goal:** prove every change with data.

**Scope**

- Grow the eval set to 30+ cases: document QA, negative cases (no answer in the document), routing, tool use, mixed Hindi and English.
- Metrics:
  - Retrieval: Hit@1, Hit@3, MRR.
  - Answers: faithfulness and answer relevancy (RAGAS or DeepEval).
  - Agents: routing accuracy, tool success rate.
- `python manage.py run_evals` in GitHub Actions on PRs to `main`; fail if a score drops more than 5%.
- Tracing with Langfuse (self-hosted) or OpenTelemetry: route → agent → tool → LLM spans, tokens and cost.
- 👍 / 👎 feedback (`MessageFeedback`); thumbs-down answers feed the eval set.
- Admin view: tokens and cost per user, failing tools, cache hit rate.

---

## 💬 Branch 016: `genai-chat-016-voice-ui` (future, optional)

- **Voice input and output** with the browser's Speech API (or Whisper).
- **Vision:** upload an image and ask about it.
- **Hindi UI:** translate the whole interface.

---

## 🎓 Deep Learning Track (learning goals, in parallel)

This project is meant to teach GenAI engineering, not only to ship features. Each topic is tied to the branch where it is most useful.

### 1. 🧠 Inside the LLM (core math and architecture)
- **Transformers:** how self-attention works (*Attention Is All You Need*).
- **Tokenization:** BPE, and how tokens affect arithmetic, rare words and Hindi text.
- **Embeddings:** how text becomes numbers, and the different similarity metrics.
- **Resource:** Andrej Karpathy's *Let's build GPT from scratch*.

### 2. 🛠️ Fine-tuning and training
- **PEFT / LoRA:** fine-tune a model on a small GPU.
- **Hugging Face:** the `transformers` and `peft` libraries.
- **Data preparation:** JSONL datasets for training (thumbs-down data from 015 is a good source).

### 3. 📚 Advanced RAG (Branch 013)
- **Reranking:** cross-encoders such as `bge-reranker`.
- **Fusion:** Reciprocal Rank Fusion for hybrid search.
- **Graph RAG:** storing data as a knowledge graph.
- **Multi-vector retrieval:** several vectors per document (question, answer, summary).

### 4. 🤖 AI agents and MCP (Branches 011–014)
- **ReAct pattern** and bounded tool loops (011).
- **MCP:** client side (012) and server side (014); tools, resources, prompts, transports, auth.
- **Multi-agent systems:** router, supervisor with handoffs, plan-and-execute, critic (013); LangGraph, Pydantic AI, OpenAI Agents SDK.

### 5. ⚡ Production and scaling (Branches 010 and 015)
- **LLMOps:** Langfuse or LangSmith.
- **Evaluation:** RAGAS / DeepEval in CI.
- **High-performance serving:** vLLM or TGI.

### 6. 🎨 Multimodal and vision (Branch 016)
- **Vision models:** LLaVA or GPT-4o Vision.
- **Speech:** Whisper and text to speech.

---

## 🗂️ Ideas not yet scheduled

- A **Stop generation** button (`AbortController` in the frontend).
- JWT in an httpOnly cookie instead of `localStorage`.
- A guard model (for example Llama Guard) for prompt-injection and safety checks.
- A retention policy for soft-deleted chats and their documents and vectors.
- Move settings to a typed `pydantic-settings` class and make `local_settings.py` optional.

---

## 💡 Suggested next step

Finish Branch 010 first, starting with **R1 (rotate the keys)**, then **R2 (download route)** and **R3 (JWT refresh)**, because these break the app for real users today. Then build the tool registry (011): MCP and agents both sit on top of it. Keep local Ollama as the default, but use a tool-capable model (7–8B or cloud) from Branch 013 onwards. Keep growing the evaluation set as you go, so RAG quality does not quietly get worse while the app gains new features.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

अब तक project में login, MySQL में chat history, document upload, hybrid RAG (vector + BM25), query rewriting, Redis rate limiting, semantic cache और दो tools (calculator और web search) बन चुके हैं। Branch 007, 008 और 009 पूरी हो गई हैं।

**Branch 010: DevOps + Critical Fixes (अभी चल रही है)**
Code review में पता चला कि `README.010.md` में लिखी कुछ चीज़ें अभी code में नहीं हैं। Dockerfile, docker-compose, Celery और tests बाकी हैं। इसके अलावा ये fixes इसी branch में होंगे:
- **R1:** `.env` में असली API keys zip के साथ चली गई थीं, इसलिए keys बदलें (rotate करें)।
- **R2:** download का URL route नहीं है, जिसकी वजह से download 404 देता है।
- **R3:** JWT refresh नहीं होता, इसलिए user कुछ देर बाद logout हो जाता है।
- **H6:** non-stream API अभी भी client की भेजी history पर भरोसा करती है।
- **H8:** logs में user का text लिखा जाता है।
- **M4:** `chunk_count` गलत आता है।
- **R5:** एक ही file बार-बार upload हो जाती है।

**Branch 011: Tool Registry**
Tools के लिए एक registry, जिसमें एक turn में कई tool rounds चल सकें (H5)। Tool के बाद का जवाब भी streaming में आएगा, और UI में "🔍 Searching…" दिखेगा।

**Branch 012: MCP Client**
बाहरी MCP servers (web search, read-only database, Drive आदि) के tools config से जुड़ेंगे, code बदलने की ज़रूरत नहीं होगी। पुराना "Database query" tool यहाँ read-only MCP के रूप में आएगा।

**Branch 013: Multi-Agent**
एक Supervisor हर सवाल को सही agent तक भेजेगा: RAG, Research, SQL या Chat। Critic जवाब जाँचेगा, और Memory Agent सिर्फ याद रखने लायक facts रखेगा। इसी branch में reranker, RRF, हर chat के अलग documents और token budget (H7) भी आएँगे।

**Branch 014: MCP Server**
हमारा RAG खुद एक MCP server बनेगा, ताकि Claude Desktop या IntelliJ से user के documents में search हो सके।

**Branch 015: Eval + Observability**
30+ सवालों का eval set, CI में automatic evals, Langfuse tracing और 👍/👎 feedback।

**Branch 016: Voice / Vision / Hindi UI (optional)**

**मेरी सलाह:** पहले Branch 010 पूरी कीजिए। शुरुआत keys rotate करने से करें, फिर download route और JWT refresh ठीक करें। उसके बाद 011 की tool registry बनाइए, क्योंकि MCP और agents दोनों उसी पर बनेंगे।

</details>
