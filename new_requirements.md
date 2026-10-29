# Project Vision & Requirements: GenAI Agent 🚀

## 1. Overview
This project is evolving from a basic local RAG (Retrieval-Augmented Generation) chatbot into a **Professional, Production-Ready AI Agent**. This document outlines the technical requirements, features, and architectural roadmap required to achieve that goal.

---

## 2. Immediate Priorities: Quick Wins & Clean-up
Before adding new features, we must fix technical debt and implement high-impact, low-effort features.
- **Code Clean-up:** Implement all fixes from the code review (correct `requirements.txt`, remove debug calls, fix JS SSE error swallowing, ensure `DEBUG=False` by default).
- **Show Sources (Citations):** Modify RAG metadata to include `filename` and `page number`. Display this to the user so they can verify the AI's answer.
- **Stop Generation:** Use `AbortController` in the frontend to stop SSE streaming mid-generation.
- **Copy Button:** Add syntax highlighting and a "Copy" button for code blocks.
- **Token-based History Trimming:** Replace the "last 10 messages" logic with token-count-based trimming to prevent context window overflow.
- **Uploaded Documents List:** Allow users to see which documents are indexed and delete them individually (currently, only a global clear is possible).

---

## 3. Advanced RAG (Retrieval Quality)
To improve accuracy, we must move beyond basic vector similarity search.
- **Query Rewriting:** Use the LLM to rewrite follow-up questions (e.g., "What is its price?") into standalone queries before retrieving.
- **Hybrid Search & Reranking:** Combine Vector search with Keyword search (BM25). Use a cross-encoder model (reranker) to re-rank the top results for exact matches (names, IDs, numbers).
- **Multilingual Embeddings:** Switch from `nomic-embed-text` (English-focused) to a multilingual model like `BAAI/bge-m3` for better Hindi/Hinglish retrieval.
- **Smarter Chunking:** Split text based on structure (headings, paragraphs, pages) instead of a fixed 500-character limit.
- **LLM Memory Extraction:** Replace the current "doesn't end with a question mark" heuristic. Use the LLM to extract structured facts (e.g., `{"favorite_color": "blue"}`) and update existing memories.
- **Evaluation Set:** Create a set of 20-30 Q&A pairs to test retrieval accuracy. Tune `RAG_MAX_DISTANCE` based on data, not guesses.

---

## 4. Database, Security & Performance
- **Authentication & Authorization:** Implement JWT-based login (using `djangorestframework-simplejwt`). Replace `X-Session-Id` with user-specific scoping.
- **MySQL Database:** Use MySQL as the primary database for User profiles, Chat History, and Document Metadata.
- **Caching (Redis):** Implement Redis for rate limiting (across multiple workers) and Semantic Caching (caching frequent answers).
- **Background Indexing (Celery):** Move heavy PDF embedding tasks to a Celery background worker so the API doesn't block.
- **Vector DB Strategy:** Keep ChromaDB for local dev, but plan to migrate to **PostgreSQL + pgvector** for production to unify SQL and Vector data.

---

## 5. Agentic Capabilities (Not just a Chatbot)
The ultimate goal is to build an Agent that can "think" and "act".
- **Tool Calling (Function Calling):** Give the LLM tools such as:
  - Web Search (e.g., Tavily API).
  - Database Querying (e.g., "How many users registered today?").
  - Calculators for math.
- **Structured Output:** Enforce JSON schema responses when the AI needs to output data for the frontend.
- **Model Routing & Fallback:** Route simple questions to fast/local models (Ollama) and complex ones to cloud models (OpenAI GPT-4o, Claude 3.5). Implement fallback if one provider fails.
- **LLM Provider Alternatives:** Support OpenAI, Anthropic, OpenRouter, and Ollama Cloud for higher accuracy and larger context windows.

---

## 6. Production Readiness & Observability
- **Docker Compose:** Containerize Django, MySQL, Redis, and Ollama for one-command setup.
- **Observability:** Add structured logging with Request IDs, latency tracking, token counts, and retrieval hits. Consider integrating Langfuse for LLM tracing.
- **Security Hardening:** Implement CSP headers, SRI (Subresource Integrity) hashes for CDN scripts, file size limits, and data retention policies.
- **Feedback Mechanism:** Add 👍/👎 buttons on chat responses to collect data for future evaluation and fine-tuning.

---

## 7. Roadmap (Branch Strategy)

| Branch | Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| `004-clean-up` | **Stability & UX** | Fix review bugs, Show Sources, Stop Button, Copy Button, Token-based history. |
| `005-database-auth` | **Product Features** | MySQL setup, JWT Authentication, Chat History DB, Document List/Delete. |
| `006-rag-quality` | **Advanced RAG** | Evaluation set, Query Rewriting, Hybrid Search, Multilingual Embeddings. |
| `007-agent-tools` | **Agentic AI** | Tool Calling (Web Search/Calculator), Switch to larger LLMs (GPT-4o/Claude). |
| `008-production` | **Scale & Deploy** | Redis Caching, Celery Background Indexing, Docker Compose, Observability. |