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
| H3 | High | `requirements.txt` misses `rank-bm25` and the MySQL driver | read | ⏳ Open |
| H4 | High | Web search: indirect prompt injection and private data sent out | read | ⏳ Open |
| H5 | High | Tool-call protocol is incomplete (one round, missing `type`) | read | ⏳ Open |
| H6 | High | Chat history is trusted from the client | read | ✅ Fixed in this branch |
| H7 | High | No token accounting or daily quota | read | ⏳ Open |
| H8 | High | Real user text is written to the logs | read | ⏳ Open |
| H9 | Medium | Rate limiter fails open when Redis is down | read | ⏳ Open |
| M1 | Medium | No reranker | read | ⏳ Open |
| M2 | Medium | No cache | read | ⏳ Planned in this branch |
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

---

### ⏳ Still open, with the proposed solution

**High priority**

| ID | Problem | Proposed solution |
|----|---------|-------------------|
| H3 | A fresh machine cannot start the app: `rank-bm25` and the MySQL driver are missing from `requirements.txt`. | Add both to `requirements.txt` and test a clean install. |
| H4 | Web search results go into the prompt without delimiters (indirect prompt injection). The user's query goes straight to a third party (Tavily), so private data can leave. The sync `TavilyClient` is created on every call and runs inside the async path without `to_thread`. | Redact personal data from the query before sending. Wrap results in an `<untrusted>` block and drop pages that contain injection patterns. Create the client once and run it with `asyncio.to_thread`. |
| H5 | The tool-call protocol is incomplete: the assistant's `tool_calls` lack `type: function` (the OpenAI API expects it), only one tool round is supported, and `json.loads(arguments)` is unguarded. | Build the assistant tool message correctly, use a bounded loop of tool rounds, answer every tool call, and handle bad JSON. |
| H7 | No token accounting and no daily quota; only the history is trimmed. | Add a budget module: check before the request, charge after it, per request and per user per day. |
| H8 | The user's real text is written to the INFO log (`[STREAM START] User: ...`, rewritten queries, in four places). | Log without personal data (structured JSON logs), and keep prompt logging off in production. |

**Medium priority**

| ID | Problem | Proposed solution |
|----|---------|-------------------|
| H9 | If Redis goes down, the rate limiter lets every request through (**fail-open**), so LLM costs become unlimited. | Fail closed by default, with a setting to change it. |
| M1 | No reranker (it was carried over from Branch 006). | Add a cross-encoder reranker and keep it only if the evaluation score improves. |
| M2 | No cache. | Exact, semantic and retrieval caches in Redis. |
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

## 🛠️ What Changed in this Branch?

### 1. UI/UX Polish ✅
- **Dark Mode:** Implemented a theme switcher using CSS variables (`--bg-color`, etc.) and `localStorage` to remember the user's choice. The toggle button is in the navbar.
- **Loading Spinner:** Replaced the simple text "Uploading..." with a Bootstrap spinner to give clear visual feedback during PDF processing.
- **Better Error Handling:** (Planned)

*(Screenshot: docs/screenshot_009_dark_mode.png)*

### 2. Review fixes ✅
- H1 (Hindi tokenizer), H2 (calculator limits) and H6 (server-side history), described above.

---

## 🚀 Next Steps for this Branch
- [ ] **Redis Semantic Caching** (M2): Cache LLM responses to save API costs and improve speed.
- [ ] **Celery Background Tasks:** Move document embedding to a background worker so the UI does not freeze.
- [ ] **Docker Compose** (M6): Containerize the app for easy deployment.
- [ ] **Quick review wins:** H3 (`requirements.txt`), H9 (fail-closed rate limiter) and M4 (real `chunk_count`).
- [ ] **Remaining high-priority review items:** H4 (web search safety), H5 (tool-call protocol), H7 (token budget) and H8 (PII-free logs).

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
ऐप को असली users के लिए तैयार करना, उसका UI बेहतर बनाना, और production architecture review में मिली गंभीर समस्याओं को ठीक करना।

**Review क्या कहता है:**
पूरे project की production के नज़रिए से जाँच हुई। नींव अच्छी है (ownership checks, secure download, hard delete, per-user rate limit, hybrid search, tool calling), पर कई समस्याएँ मिलीं। हर समस्या का एक ID है: **H** यानी high priority और **M** यानी medium। Evidence में **ran** का मतलब है कि reviewer ने code चलाकर साबित किया, और **read** का मतलब code पढ़कर पुष्टि की। Docker build, असली cluster, load test और penetration test इस review में शामिल नहीं थे।

**इस branch में ठीक हुईं तीन समस्याएँ:**

1. **H1: Hindi में BM25 का crash।**
   - समस्या: Tokenizer `\w+` इस्तेमाल करता था, जो Devanagari की मात्राएँ नहीं पकड़ता। इसलिए Hindi वाक्यों के token list **ख़ाली** आते थे। जब किसी user के सारे chunks ख़ाली हों, तो `BM25Okapi` `ZeroDivisionError` से crash करता है। (Reviewer ने चलाकर साबित किया।)
   - समाधान: Pattern में Devanagari block जोड़ा (`[\w\u0900-\u097F]+`), और token list ख़ाली हो तो score `0.0` लौटाने की जाँच लगाई।
   - ध्यान: इस block में दंड (`।`) भी आता है, जो विराम चिह्न है। चाहें तो उसे बाहर रखें।
2. **H2: Calculator पर DoS।**
   - समस्या: `9**9**9` जैसा input Python को विशाल संख्या निकालने में लगा देता है, CPU और memory जाम हो जाती है। यह तब आया जब हमने Branch 008 में `^` ठीक करते समय `**` allow किया। (बिना guard के यह कभी वापस नहीं आया; guard के साथ लगभग 0.1 ms में reject हुआ।)
   - समाधान: `ast.Pow` में base अधिकतम `10,000` और exponent अधिकतम `10`। इससे बड़ा हो तो तुरंत सुरक्षित error मिलता है।
3. **H6: Client से आने वाली History।**
   - समस्या: API browser से भेजी `history` पर भरोसा करता था, इसलिए कोई भी नकली `assistant` messages भेजकर model को बहका सकता था (prompt injection)।
   - समाधान: `ChatRequest` से `history` हटाई। अब `ChatStreamAPIView` बातचीत MySQL से लोड करता है, और client सिर्फ़ `message` और `session_id` भेजता है।

**अभी खुली समस्याएँ और प्रस्तावित समाधान:**

- **H3:** `requirements.txt` में `rank-bm25` और MySQL driver नहीं हैं, नई machine पर app शुरू नहीं होगा। इन्हें जोड़ें।
- **H4:** Web search के नतीजे prompt में बिना delimiter जाते हैं (indirect prompt injection), और user का query सीधे Tavily को जाता है। Query से निजी जानकारी हटाएँ, नतीजे `<untrusted>` में रखें, और client को `asyncio.to_thread` से चलाएँ।
- **H5:** Tool-call protocol अधूरा है (सिर्फ़ एक round, `type: function` नहीं, `json.loads` बिना जाँच)। सीमित loop और सही message बनाएँ।
- **H7:** Token का हिसाब या daily quota नहीं है। Budget module जोड़ें।
- **H8:** User का असली text log में लिखा जाता है। बिना निजी जानकारी वाले JSON logs रखें।
- **H9:** Redis बंद हो तो rate limiter सब request निकल जाने देता है (fail-open), यानी LLM का ख़र्च बेकाबू। Default रूप से fail-closed रखें।
- **M1 से M6:** Reranker नहीं; cache नहीं; BM25 index हर query पर दोबारा बनता है और 1000 से ऊपर के chunks चुपचाप छूट जाते हैं; `chunk_count` हमेशा लगभग 1 आता है; JWT और security settings नहीं हैं; Docker, CI, Kubernetes और tests नहीं हैं।

**Hybrid score का गणित:**
`hybrid = 0.5 * (1 - distance) + 0.5 * min(bm25 / 5, 1)`, और threshold `0.35`। सिर्फ़ vector से पास होने के लिए distance <= 0.30 चाहिए, और सिर्फ़ BM25 से पास होने के लिए raw BM25 >= 3.5। BM25 का score corpus के आकार पर निर्भर है, इसलिए `/5` और `0.35` "जादुई संख्याएँ" हैं। Reciprocal Rank Fusion (RRF) इसका बेहतर हल है, क्योंकि वह scores की जगह सिर्फ़ rank जोड़ता है।

**UI सुधार:**
1. **Dark Mode:** Navbar में बटन, और user की पसंद `localStorage` में सेव।
2. **Loading Spinner:** PDF upload के दौरान सिर्फ़ text की जगह spinner।

**अगला कदम:**
Redis Caching और Celery (background processing) और Docker Compose, साथ में review की बाकी समस्याएँ: पहले आसान वाली (H3, H9, M4), फिर H4, H5, H7, H8।

</details>