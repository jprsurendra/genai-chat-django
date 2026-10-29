# Project Vision & Requirements: GenAI Agent 🚀

## 1. Overview
This project is evolving from a basic local RAG (Retrieval-Augmented Generation) chatbot into a **Professional, Production-Ready AI Agent**. This document outlines the technical requirements, features, and architectural roadmap required to achieve that goal.

---

## 2. Core Architectural Requirements (Your Vision)

### 🔐 1. Authentication & Authorization (Security)
- **Current State:** Uses client-side `X-Session-Id` which only separates data but does not verify identity.
- **Requirement:** Implement a robust, secure login system.
- **Implementation:**
  - Use **Django REST Framework SimpleJWT** for token-based authentication.
  - Implement User Registration, Login, and Logout APIs.
  - Migrate from `session_id` to `user_id` for all RAG scoping.
  - Restrict all chat, memory, and document endpoints to authenticated users only.

### 🗄️ 2. Database & Vector Store (Data Persistence)
- **Current State:** Data is stored locally in ChromaDB and lost if the server restarts (in-memory/volatile).
- **Requirement:** We need a hybrid storage architecture.
- **Implementation:**
  - **MySQL (Relational DB):** Store User profiles, Chat Sessions, Chat History, and Document Metadata.
  - **ChromaDB / Vector DB:** Keep a dedicated Vector Database strictly for embeddings (RAG).
  - **Data Deletion:** Ensure "Clear Chat" or "Delete Account" wipes data from both MySQL and the Vector DB.

### ⚡ 3. Caching (Performance)
- **Requirement:** Reduce LLM costs and response times.
- **Implementation:**
  - Use **Redis** for high-speed caching.
  - Implement **Semantic Caching:** If a user asks a question very similar to a recently asked one, return the cached answer.
  - Cache RAG retrieval results to avoid repeated queries to the Vector DB.

### 🤖 4. Agentic Capabilities (Not just a Chatbot)
- **Requirement:** The system must "think" and "act", not just answer.
- **Implementation:**
  - Implement **Tool Calling (Function Calling)**.
  - Agents should be able to use tools like: Web Search (Tavily), Database Querying, and Calculators.
  - Support **Multi-step reasoning** (Chain of Thought) to break down complex tasks.

### 🌐 5. LLM Provider & Scalability (Alternatives)
- **Requirement:** Small local models (1.5B/8B) are good for learning but fail at complex reasoning.
- **Implementation:**
  - **Provider Agnostic:** Keep the `openai` SDK wrapper.
  - **Local (Dev):** Ollama (Zero cost).
  - **Production (Accuracy):** OpenAI (GPT-4o), Anthropic (Claude 3.5), OpenRouter, or Ollama Cloud (for large open-source models).
  - **Model Routing:** Send simple queries to fast models, complex ones to smart models.

---

## 3. RAG Quality & Advanced Features

- **Query Rewriting:** Rewrite follow-up questions (e.g., "What is its price?") into standalone queries before retrieval.
- **Hybrid Search & Reranking:** Combine Vector search with Keyword search (BM25) and use a reranker for exact matches (names, IDs).
- **Multilingual Embeddings:** Switch from `nomic-embed-text` to a model like `BAAI/bge-m3` for better Hindi/Hinglish retrieval.
- **Smarter Chunking:** Split text based on structure (pages/headings) instead of fixed 500-character limits.
- **Show Sources (Citations):** Display the `filename` and `page number` in the UI so users can verify the AI's answer.
- **Evaluation Set:** Create 20-30 Q&A pairs to test retrieval accuracy and tune `RAG_MAX_DISTANCE`.
- **LLM Memory Extraction:** Use the LLM to extract structured facts (e.g., `{"favorite_color": "blue"}`) instead of simple string matching.

---

## 4. UI/UX & Quick Wins
- **Stop Generation:** Add an `AbortController` to stop SSE streaming.
- **Copy Button:** Add syntax highlighting and a "Copy" button for code blocks.
- **Document Management:** List uploaded documents in the UI and allow individual deletion.
- **Token-based History:** Replace "last 10 messages" with token-count-based trimming to prevent context overflow.
- **Feedback:** Add 👍/👎 buttons on responses for future model evaluation.
- **Voice & Hindi UI:** Use the browser's Speech API for voice input/output.

---

## 5. Production Readiness & DevOps
- **Background Indexing (Celery):** Move PDF embedding to a background worker so the API doesn't block.
- **Docker Compose:** Containerize Django, MySQL, Redis, and Ollama for one-command setup.
- **Observability:** Add structured logging (Request ID, latency, token count) and consider Langfuse for LLM tracing.
- **Security Hardening:** Implement CSP headers, SRI hashes for CDN, and file size limits.
- **CI/CD:** Add GitHub Actions to run `manage.py test` and `ruff` on every push.

---

## 6. Implementation Roadmap (Branch Strategy)

| Branch | Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| `004-clean-up` | **Stability & UX** | Fix review bugs, Show Sources, Stop Button, Copy Button, Token-based history. |
| `005-database-auth` | **Product Features** | MySQL setup, JWT Authentication, Chat History DB, Document List/Delete. |
| `006-rag-quality` | **Advanced RAG** | Evaluation set, Query Rewriting, Hybrid Search, Multilingual Embeddings. |
| `007-agent-tools` | **Agentic AI** | Tool Calling (Web Search/Calculator), Switch to larger LLMs (GPT-4o/Claude). |
| `008-production` | **Scale & Deploy** | Redis Caching, Celery Background Indexing, Docker Compose, Observability. |