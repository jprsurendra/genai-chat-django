# Branch 009: `genai-chat-009-production-ui` 🚧

**Goal:** 
To prepare the application for real-world users by improving the User Interface (UI) and User Experience (UX), and by fixing the most critical problems found in a production architecture review. This branch also introduces production-level features like Redis caching and background processing.

---

## 🔍 Production Architecture Review: findings and solutions

The whole project was reviewed against production standards. The review found a good foundation (ownership checks, secure downloads, hard delete, per-user rate limiting, hybrid search, tool calling), but also a list of problems that would hurt in production. Each finding has an ID: **H** for high priority, **M** for medium.

How to read the evidence column:

- **ran** = the reviewer ran the code and proved the behaviour.
- **read** = confirmed by reading the code.

What the review did *not* cover: Docker image builds and scans, applying manifests to a real cluster, CI on GitHub, load tests, a real LLM or vector database, a real Redis, and penetration testing. Treat the findings as strong guidance, not as a complete security audit.

### All findings at a glance

| ID | Severity | Finding | Evidence | Status |
|----|----------|---------|----------|--------|
| H1 | High | BM25 is blind to Hindi and can crash the RAG engine | ran | ✅ Fixed in this branch |
| H2 | High | Calculator accepts unlimited exponents (DoS) | ran | ✅ Fixed in this branch |
| H3 | High | `requirements.txt` misses `rank-bm25` and the MySQL driver | read | ✅ Fixed in this branch |
| H4 | High | Web search: indirect prompt injection and private data sent out | read | 🟡 Partly fixed |
| H5 | High | Tool-call protocol is incomplete (one round, missing `type`) | read | ⏳ Open |
| H6 | High | Chat history is trusted from the client | read | ✅ Fixed in this branch |
| H7 | High | No token accounting or daily quota | read | ⏳ Open |
| H8 | High | Real user text is written to the logs | read | ⏳ Open |
| H9 | Medium | Rate limiter fails open when Redis is down | read | ✅ Fixed in this branch |
| M1 | Medium | No reranker | read | ⏳ Open |
| M2 | Medium | No cache | read | ✅ Implemented in this branch (semantic cache) |
| M3 | Medium | BM25 index rebuilt on every query; chunks beyond 1000 silently ignored | read | ⏳ Open |
| M4 | Medium | `chunk_count` is wrong (always about 1) | read | ⏳ Open |
| M5 | Medium | `SIMPLE_JWT`, `SECURE_*` headers and password validators not configured | read | ⏳ Open |
| M6 | Medium | No Docker, CI, Kubernetes or tests | read | ⏳ Docker Compose planned in this branch |

---

### ✅ Fixed in this branch

#### H1: Hindi BM25 tokenizer crash

- **Issue:** the tokenizer used `re.findall(r'\w+')` and then dropped words of 2 characters or fewer. Python's `\w` does not match Devanagari vowel signs (matras), so Hindi words are cut into pieces or disappear.
- **Proof (ran):** all three Hindi test sentences produced an **empty** token list. When every chunk of a user has no tokens, `BM25Okapi(...)` raises a `ZeroDivisionError`, so a Hindi question could crash the RAG engine. A side effect is that Hindi questions got no keyword score at all and depended on vector search alone.
- **Solution:**
  - Include the Devanagari Unicode block in the token pattern: `r'[\w\u0900-\u097F]+'`.
  - Add a guard that returns a score of `0.0` when the token list is empty, so nothing can crash.
- **Note:** the Devanagari block also contains the danda (`।`, U+0964 and U+0965), which is punctuation, not a word. The reviewer's reference tokenizer leaves it out. If you want the same, use `r'[\w\u0900-\u0963\u0966-\u097F]+'`.

#### H2: Calculator DoS

- **Issue:** the `calculate` tool allowed `ast.Pow` with no limits. An input such as `9**9**9` makes Python compute an enormous number, using 100% CPU and memory until the server is unusable. This is a denial of service that any logged-in user (or a prompt-injected document) could trigger. It follows directly from allowing `**` when we fixed the `^` problem in Branch 008.
- **Proof (ran):** without a guard, `9**9**9` never returned (the test hit its timeout); with a guard it was rejected in about 0.1 ms.
- **Solution:** a limit inside the `ast.Pow` handler: the base may be at most `10,000` and the exponent at most `10`. Anything larger returns a safe error message immediately.
- **Note:** this closes the "limit the exponent" item that was left open in [README.008.md](README.008.md).

#### H6: Client-supplied history

- **Issue:** the API accepted the `history` array straight from the browser (`ChatRequest.history`, up to 50 messages). A malicious user could forge earlier `assistant` messages and steer the model, which is a form of prompt injection.
- **Solution:**
  - Removed `history` from the Pydantic `ChatRequest` model.
  - `ChatStreamAPIView` now loads the conversation from MySQL on the server before calling the LLM.
  - The client sends only the new `message` and the `session_id`.

#### H3: Missing packages in `requirements.txt`

- **Issue:** a fresh machine could not start the app, because `rank-bm25` and the MySQL driver were not listed.
- **Solution:** added these lines to `requirements.txt`:

  ```text
  rank-bm25>=0.2.2
  mysqlclient>=2.2.0
  redis>=5.0.1
  ```

- **Note:** `tools.py` also imports `tavily`, and other modules import packages such as `chromadb`, `pypdf` and `langchain-text-splitters`. Check that every imported package is listed, ideally by installing into a brand-new virtual environment and starting the app.

#### H9: Rate limiter fails open

- **Issue:** when Redis was down, the limiter let every request through, so LLM costs became unlimited.
- **Solution:** the limiter now **fails closed**. If Redis is unavailable, or a Redis command fails, the request is blocked with `PermissionDenied("Service temporarily unavailable...")`.
- **Note:** creating `redis.Redis(...)` does not open a connection, so a down Redis normally shows up as a `RedisError` while the pipeline runs, not as `redis_client is None`. Both paths are now handled. The response is a 403; a 503 would describe the situation more accurately.

#### H4: Web search safety (partly fixed)

- **Issue:** search results went into the prompt as plain text, so a web page could carry instructions aimed at the model (indirect prompt injection).
- **What was done:**
  - All results are wrapped in an `<untrusted_web_data> ... </untrusted_web_data>` block, so the model can tell data from instructions.
  - Results that contain obvious injection phrases (`ignore previous instructions`, `system prompt`, `you are now`) are skipped, and a warning is logged.
- **Still open:** the keyword filter is easy to bypass by rephrasing, so treat it as an extra layer, with the "treat retrieved text as data" rule from Branch 007 as the main defence. Also not done yet: removing personal data from the query before it goes to Tavily, creating the Tavily client once, and running the synchronous client with `asyncio.to_thread`.

---

### ⏳ Still open, with the proposed solution

**High priority**

| ID | Problem | Proposed solution |
|----|---------|-------------------|
| H4 (rest) | The user's query goes straight to a third party (Tavily), so private data can leave. The sync `TavilyClient` is created on every call and runs inside the async path without `to_thread`. | Redact personal data from the query before sending. Create the client once and run it with `asyncio.to_thread`. |
| H5 | The tool-call protocol is incomplete: the assistant's `tool_calls` lack `type: function` (the OpenAI API expects it), only one tool round is supported, and `json.loads(arguments)` is unguarded. | Build the assistant tool message correctly, use a bounded loop of tool rounds, answer every tool call, and handle bad JSON. |
| H7 | No token accounting and no daily quota; only the history is trimmed. | Add a budget module: check before the request, charge after it, per request and per user per day. |
| H8 | The user's real text is written to the INFO log (`[STREAM START] User: ...`, rewritten queries, in four places). | Log without personal data (structured JSON logs), and keep prompt logging off in production. |

**Medium priority**

| ID | Problem | Proposed solution |
|----|---------|-------------------|
| M1 | No reranker (it was carried over from Branch 006). | Add a cross-encoder reranker and keep it only if the evaluation score improves. |
| M2 (rest) | Only the semantic cache exists. | Add an exact-match cache and a retrieval cache, and fix the cache risks listed in the discussion section below. |
| M3 | Every query calls `collection.get(limit=1000)` and rebuilds the BM25 index, which is slow, and chunks beyond 1000 are silently ignored. | Build the BM25 index once, cache it, and rebuild it only when documents change. |
| M4 | `chunk_count = result_message.count('chunks')` is always about 1. | Return the real count from the RAG engine. |
| M5 | Missing `SIMPLE_JWT` settings (token lifetime), `SECURE_*` headers and password validators. | Configure short token lifetimes and the security settings. In production, prefer asymmetric signing (RS256/EdDSA). |
| M6 | No Docker, CI, Kubernetes or tests. | Docker Compose in this branch, then CI and automated tests. |

---

### 📐 How the hybrid score works, and why it is fragile

The hybrid search computes:

```text
hybrid = 0.5 * (1 - distance) + 0.5 * min(bm25 / 5, 1)      threshold = 0.35
```

That has two consequences:

- A chunk can pass on **vector similarity alone** only if `0.5 * (1 - distance) >= 0.35`, which means **distance <= 0.30**.
- A chunk can pass on **BM25 alone** only if the **raw BM25 score is at least 3.5**.

The BM25 score depends on the size of the corpus and the length of the chunks, so the `/5` and the `0.35` are magic numbers that must be retuned whenever the data changes. A better method is **Reciprocal Rank Fusion (RRF)**: it combines only the *ranks* from the two searches, not their scores, so it needs no such tuning.

Until H1 was fixed, Hindi BM25 returned zero, so Hindi questions depended on vector search alone and needed a distance of 0.30 or less to pass the threshold.

---

## 🧠 Discussion summary: Redis semantic caching (M2)

This section records what we built, what broke and what to watch out for, so the idea is easy to learn from later.

### The idea

An LLM call is slow and costs money (or free-tier quota). If a user asks something that was already answered, the app can return the stored answer instead of calling the model.

- An **exact cache** only matches identical text. `What is 2+2?` and `what's 2+2` would be different keys.
- A **semantic cache** compares the *meaning*: it turns the question into an embedding (a vector) and checks whether a stored question is similar enough. Similar enough means a cosine similarity at or above a threshold.

### How it works here

1. A question arrives. Before anything else, `stream_reply` calls `check_cache`.
2. `check_cache` embeds the question and compares it with the embeddings of the questions this user asked before (stored in the Redis hash `cache:semantic:<session_id>`).
3. If the best similarity is at least `SIMILARITY_THRESHOLD`, the stored answer is returned, with no RAG lookup and no LLM call. It is streamed character by character so the chat window behaves as before.
4. Otherwise the normal flow runs (query rewriting, hybrid retrieval, tools, LLM). When an answer exists, `save_to_cache` stores the question, its embedding and the answer as JSON, and sets an expiry.
5. Answers produced after a tool call (calculator, web search) are cached too.

Settings in `local_settings.py`:

```python
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))                       # 24 hours
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95"))
```

Where the code lives: `check_cache` and `save_to_cache` in `chat/utilities/rags/rag_engine.py`, and the cache check at the start of `stream_reply` in `chat/utilities/llms/llm.py`. If Redis is unavailable, the cache is skipped silently and the app works as before.

### The bug we hit

The first test showed this in the log:

```text
[ERROR] Cache save failed: Object of type ndarray is not JSON serializable
```

- **Cause:** the embedding comes back as a NumPy array, and `json.dumps()` cannot serialise NumPy types.
- **Fix:** convert it to a plain list of floats before saving:

```python
query_vec = self._get_query_embedding(query)
query_vec_list = [float(x) for x in query_vec]   # numpy array -> plain Python list
cache_data = json.dumps({"embedding": query_vec_list, "answer": answer})
```

### The result

After the fix the log showed both halves of the cache working:

```text
💾 Saved to Cache: '...'
⚡ Cache Hit! Similarity: 0.9525     # the repeated "2+2?" question
⚡ Cache Hit! Similarity: 1.0000     # the repeated UK Prime Minister question
```

The second question was an exact repeat (similarity 1.0). The first scored 0.9525, only just above the 0.95 threshold, which shows how sensitive that setting is.

### Things to watch (from reading the code)

- **Similar text is not always the same question.** Questions that differ by one number, such as `2+2` and `2+3`, can produce very similar embeddings. With a threshold this low, the cache could return the wrong answer. Test pairs like these, and consider a higher threshold or skipping the cache for short or numeric questions.
- **Stale answers.** Answers from the web search tool (weather, news) are cached for 24 hours, so "weather in Mumbai" could return yesterday's weather. Do not cache time-sensitive tool answers, or give them a short expiry.
- **Clearing data does not clear the cache.** `delete_session` removes documents and memories, but not the `cache:semantic:<session_id>` key, so cached answers survive "Clear All" until they expire. That conflicts with the complete-erasure goal of Branch 007.
- **Old answers after a new upload.** A cached answer ignores a document the user uploaded afterwards. Clear the user's cache when a document is added or removed.
- **It scans everything.** `check_cache` reads the whole hash and compares the question with every entry, so it slows down as the cache grows. A vector index (for example Redis search) would fix that later.

---

## 🛠️ What Changed in this Branch?

### 1. UI/UX Polish ✅
- **Dark Mode:** Implemented a theme switcher using CSS variables (`--bg-color`, etc.) and `localStorage` to remember the user's choice. The toggle button is in the navbar.
- **Loading Spinner:** Replaced the simple text "Uploading..." with a Bootstrap spinner to give clear visual feedback during PDF processing.
- **Better Error Handling:** (Planned)

*(Screenshot: docs/screenshot_009_dark_mode.png)*

### 2. Review fixes ✅
- H1 (Hindi tokenizer), H2 (calculator limits), H3 (requirements), H6 (server-side history), H9 (fail-closed rate limiter) and part of H4 (web search safety), described above.

### 3. Redis semantic caching ✅
- Repeated or very similar questions are answered from Redis without calling the LLM (M2).

---

## 🚀 Next Steps for this Branch
- [x] **Redis Semantic Caching** (M2).
- [x] **Quick review wins:** H3 (`requirements.txt`) and H9 (fail-closed rate limiter). M4 (real `chunk_count`) is still open.
- [ ] **Fix the cache risks:** clear the user's cache on "Clear All" and on document upload, and do not cache time-sensitive tool answers.
- [ ] **Celery Background Tasks:** Move document embedding to a background worker so the UI does not freeze.
- [ ] **Docker Compose** (M6): Containerize the app for easy deployment.
- [ ] **Remaining high-priority review items:** the rest of H4, H5 (tool-call protocol), H7 (token budget) and H8 (PII-free logs).

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
ऐप को असली users के लिए तैयार करना, UI बेहतर बनाना, production architecture review की समस्याएँ ठीक करना, और Redis semantic caching जोड़ना।

**Review क्या कहता है:**
नींव अच्छी है, पर कई समस्याएँ मिलीं। हर समस्या का ID है: **H** यानी high priority और **M** यानी medium। Evidence में **ran** का मतलब reviewer ने code चलाकर साबित किया, और **read** का मतलब code पढ़कर पुष्टि की। Docker build, असली cluster, load test और penetration test शामिल नहीं थे।

**इस branch में ठीक हुईं समस्याएँ:**

1. **H1: Hindi में BM25 का crash:** Tokenizer `\w+` Devanagari की मात्राएँ नहीं पकड़ता था, इसलिए Hindi वाक्यों के token list ख़ाली आते और `BM25Okapi` `ZeroDivisionError` से crash करता। समाधान: pattern में Devanagari block जोड़ा (`[\w\u0900-\u097F]+`) और ख़ाली token list पर score `0.0`। (दंड `।` इस block में आता है; चाहें तो बाहर रखें।)
2. **H2: Calculator पर DoS:** `9**9**9` जैसा input server जाम कर देता था। समाधान: `ast.Pow` में base अधिकतम `10,000` और exponent अधिकतम `10`।
3. **H3: `requirements.txt`:** `rank-bm25`, `mysqlclient` और `redis` जोड़े। ध्यान रहे, `tools.py` में `tavily` भी import होता है, इसलिए सारे imported packages नए virtual environment में जाँच लें।
4. **H6: Client से आने वाली History:** `ChatRequest` से `history` हटाई; अब बातचीत MySQL से लोड होती है, और client सिर्फ़ `message` और `session_id` भेजता है।
5. **H9: Rate limiter fail-open:** अब Redis बंद होने पर या Redis command फ़ेल होने पर request रोक दी जाती है (fail-closed)।
6. **H4 (आंशिक):** Web search के सारे नतीजे `<untrusted_web_data>` block में जाते हैं, और साफ़ injection वाले वाक्यांश (`ignore previous instructions`, `system prompt`, `you are now`) वाले नतीजे छोड़ दिए जाते हैं। यह filter आसानी से बचाया जा सकता है, इसलिए Branch 007 का "data मानो, निर्देश नहीं" नियम ही मुख्य बचाव है। Query से निजी जानकारी हटाना और `asyncio.to_thread` अभी बाकी है।

**Redis Semantic Caching (M2): चर्चा का सार**

- **विचार:** अगर वही (या मिलता-जुलता) सवाल पहले पूछा जा चुका है, तो LLM को call किए बिना Redis से जवाब दे दें। इससे API ख़र्च बचता है और जवाब तुरंत आता है।
- **Exact बनाम Semantic cache:** Exact cache सिर्फ़ एक जैसे text पर चलता है। Semantic cache सवाल का embedding बनाकर देखता है कि कोई पुराना सवाल threshold (`SIMILARITY_THRESHOLD = 0.95`) तक मिलता है या नहीं।
- **कैसे चलता है:** `stream_reply` सबसे पहले `check_cache` चलाता है। मिलान हो तो पुराना जवाब (character-by-character stream करके) लौटता है। वरना सामान्य flow चलता है और जवाब मिलने पर `save_to_cache` सवाल, उसका embedding और जवाब Redis hash `cache:semantic:<session_id>` में रखता है (`CACHE_TTL = 86400`, यानी 24 घंटे)। Tool से आए जवाब भी cache होते हैं। Redis न चले तो cache चुपचाप छोड़ दिया जाता है।
- **जो bug आया:** log में `Cache save failed: Object of type ndarray is not JSON serializable`। कारण: embedding NumPy array है, और `json.dumps()` उसे नहीं समझता। समाधान: `[float(x) for x in query_vec]` से सामान्य list बनाएँ।
- **नतीजा:** `⚡ Cache Hit! Similarity: 0.9525` (दोहराया गया `2+2?`) और `⚡ Cache Hit! Similarity: 1.0000` (दोहराया गया UK PM का सवाल)। 0.9525, threshold 0.95 से बस थोड़ा ऊपर था, यानी यह setting कितनी नाज़ुक है, यह दिखता है।
- **ध्यान रखने वाली बातें:**
  - `2+2` और `2+3` जैसे सवालों के embeddings बहुत मिलते-जुलते हो सकते हैं, इसलिए cache ग़लत जवाब दे सकता है। ऐसे जोड़े test करें।
  - Web search के जवाब (मौसम, खबर) 24 घंटे cache रहते हैं, इसलिए पुराना मौसम मिल सकता है। समय-संवेदनशील जवाब cache न करें, या छोटा expiry दें।
  - `delete_session` cache key नहीं हटाता, इसलिए "Clear All" के बाद भी cached जवाब बचे रहते हैं। Branch 007 के पूरे erasure लक्ष्य से यह टकराता है।
  - नया document upload करने के बाद भी पुराना cached जवाब मिल सकता है।
  - `check_cache` पूरा hash पढ़कर हर entry से तुलना करता है, इसलिए cache बढ़ने पर धीमा होगा।

**अभी खुली समस्याएँ:** H4 का बाकी हिस्सा, H5 (tool-call protocol अधूरा), H7 (token budget नहीं), H8 (log में user का असली text), M1 (reranker), M3 (BM25 index हर query पर दोबारा), M4 (`chunk_count` ग़लत), M5 (JWT और security settings), M6 (Docker, CI, tests)।

**Hybrid score का गणित:**
`hybrid = 0.5 * (1 - distance) + 0.5 * min(bm25 / 5, 1)` और threshold `0.35`। सिर्फ़ vector से पास होने के लिए distance <= 0.30, और सिर्फ़ BM25 से पास होने के लिए raw BM25 >= 3.5। `/5` और `0.35` "जादुई संख्याएँ" हैं; Reciprocal Rank Fusion (RRF) बेहतर हल है, क्योंकि वह scores की जगह rank जोड़ता है।

**UI सुधार:** Dark Mode (पसंद `localStorage` में सेव) और PDF upload के दौरान Loading Spinner।

**अगला कदम:**
Cache के जोखिम ठीक करना (Clear All और upload पर cache साफ़ करना), फिर Celery, Docker Compose, और review की बाकी समस्याएँ (H4 का शेष, H5, H7, H8)।

</details>