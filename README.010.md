# Branch 010: `genai-chat-010-devops` 🚀

**Goal:** 
To make the application ready for real-world deployment and fix the remaining architectural issues identified in the Enterprise Review. This branch focuses on **Dockerization**, **Celery Background Tasks**, and **Security Hardening**.

---

## 🚨 Remaining Security Fixes (From Enterprise Review)

### 1. Missing Dependencies (H3) ✅
- **The Issue:** A fresh machine could not start the app because `rank-bm25` and the MySQL driver (`mysqlclient`) were missing from `requirements.txt`.
- **The Solution:** Pinned all dependencies (including `rank-bm25`, `mysqlclient`, `redis`, `tavily-python`) in `requirements.txt` and tested a clean install.

### 2. Web Search Prompt Injection (H4) ✅
- **The Issue:** Search results from Tavily were injected directly into the prompt. A malicious webpage could contain instructions to hijack the AI.
- **The Solution:** 
  - Wrapped the search results in `<untrusted_web_data>` tags.
  - Added a basic filter to drop pages containing obvious injection patterns (e.g., "ignore previous instructions").

### 3. Rate Limiter Fail-Open (H9) ✅
- **The Issue:** If Redis went down, the rate limiter let every request through, allowing unlimited LLM API calls (cost explosion).
- **The Solution:** The rate limiter now **fails closed**. If Redis is unavailable, it blocks requests and returns a `503 Service Unavailable` or `429 Too Many Requests`.

---

## 🛠️ What Changed in this Branch?

### 1. Docker Compose (M6) 🐳
We containerized the entire stack so it can be started with a single command.
- **`Dockerfile`**: Multi-stage build for the Django app.
- **`docker-compose.yml`**: Orchestrates Django, MySQL, Redis, and Ollama.

### 2. Celery Background Tasks (M6) ⏳
- **The Issue:** Uploading a large PDF froze the UI because the embedding process ran synchronously.
- **The Solution:** Moved the PDF processing (chunking and embedding) to a **Celery worker**. The API returns instantly, and the UI shows a "Processing..." status.

### 3. Basic Tests (M6) 🧪
- Added `tests.py` with basic unit tests for the Calculator tool and the Rate Limiter.

---

## 🚀 Next Steps for Branch 011
- [ ] **H5 (Tool Call Protocol):** Fix the missing `type: function` in the assistant's tool_calls.
- [ ] **H7 (Token Budget):** Implement daily token quotas to control API costs.
- [ ] **H8 (PII Logs):** Remove user text from INFO logs.
- [ ] **M1 (Reranker):** Add a cross-encoder reranker for better RAG retrieval.
- [ ] **M3 (BM25 Cache):** Cache the BM25 index to avoid rebuilding it on every query.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
ऐप को डिप्लॉयमेंट (Production) के लिए तैयार करना और एंटरप्राइज रिव्यू में बची हुई सुरक्षा खामियों को ठीक करना।

**मुख्य सुरक्षा सुधार:**
1. **गायब पैकेज (H3):** `requirements.txt` में `rank-bm25` और MySQL driver जोड़े गए, ताकि नई मशीन पर ऐप बिना एरर के चले।
2. **वेब सर्च में Prompt Injection (H4):** Tavily के रिज़ल्ट्स को अब `<untrusted_web_data>` टैग में रखा जाता है, ताकि कोई गलत वेबसाइट AI को हैक न कर सके।
3. **रेट लिमिटर (H9):** अगर Redis डाउन हो जाए, तो अब रेट लिमिटर सभी रिक्वेस्ट्स को रोक देगा (Fail-Closed), ताकि API का बिल अनलिमिटेड न बढ़े।

**नए फीचर्स:**
1. **Docker Compose:** पूरे प्रोजेक्ट (Django, MySQL, Redis, Ollama) को एक कमांड से चलाया जा सकता है।
2. **Celery:** PDF अपलोड करते समय अब UI फ्रीज़ नहीं होगी, क्योंकि PDF प्रोसेसिंग बैकग्राउंड में होगी।
3. **Basic Tests:** कैलकुलेटर और रेट लिमिटर के लिए कुछ बुनियादी टेस्ट जोड़े गए।

**अगला कदम:**
Branch 011 में हम टूल कॉलिंग प्रोटोकॉल (H5), टोकन बजट (H7), और Reranker (M1) पर काम करेंगे।

</details>