# Branch 004: `genai-chat-004-clean-up`

# Project Vision & Requirements: GenAI Agent 🚀

## 1. Overview
The goal of this project is to transition from a basic, local RAG (Retrieval-Augmented Generation) chatbot into a **Professional AI Agent**. This requires robust security, reliable data storage, high performance, and the ability to perform complex tasks (Agentic behavior).

---

## 2. Core Requirements

### 🔐 1. Authentication & Authorization (Security)
- **Requirement:** Replace the current client-side `X-Session-Id` header with a proper user authentication system.
- **Implementation:**
  - Use **Django REST Framework SimpleJWT** for token-based authentication.
  - Implement User Registration, Login, and Logout endpoints.
  - Restrict all chat, memory, and document upload endpoints to authenticated users only.
  - Scope all RAG data (memory/documents) strictly to the `user_id`.

### 🗄️ 2. Database & Vector Store (Data Persistence)
- **Requirement:** Do not rely solely on in-memory or local file-based storage. We need a robust relational database for user data and a dedicated vector store for AI memory.
- **Implementation:**
  - **MySQL:** Use MySQL as the primary relational database to store User profiles, Chat Sessions, Chat History, and Document Metadata.
  - **ChromaDB (or alternatives like PGVector):** Keep a dedicated Vector Database to store embeddings for RAG. Do not store raw chat logs here, only the embeddings.
  - **Data Deletion:** Ensure a "Clear Chat" or "Delete Account" action actually deletes records from both MySQL and the Vector Database.

### ⚡ 3. Caching (Performance)
- **Requirement:** Improve response times and reduce LLM/DB load by implementing caching.
- **Implementation:**
  - Use **Redis** as the caching backend.
  - Implement **Semantic Caching:** If a user asks a question that is very similar to a recently asked question, return the cached answer instead of calling the LLM again.
  - Cache the RAG retrieval results to avoid querying ChromaDB repeatedly for identical queries.

### 🤖 4. Agentic Capabilities (Not just a Chatbot)
- **Requirement:** The system must evolve from a simple Q&A bot into an Agent that can perform actions.
- **Implementation:**
  - Implement **Function Calling / Tool Calling**.
  - The Agent should be able to use tools such as:
    - Web Search (e.g., Tavily API).
    - Database Querying (e.g., "How many users registered today?").
    - Calculator for math problems.
  - The architecture must support **multi-step reasoning** (Chain of Thought).

### 🌐 5. LLM Provider & Scalability (Alternatives)
- **Requirement:** Acknowledge the limitations of small local models (1.5B/8B) and support cloud providers for professional accuracy.
- **Implementation:**
  - Maintain a provider-agnostic approach using the `openai` SDK.
  - Default local dev: **Ollama** (for zero cost).
  - Production/Advanced: Support **OpenAI (GPT-4o)**, **Anthropic (Claude 3.5)**, or **OpenRouter** by just changing environment variables.
  - Support for larger Ollama models via **Ollama Cloud** (e.g., 70B+ models).

---

## 3. Immediate Roadmap (Branch 004 Clean-up)
Before adding new features, we must fix the technical debt identified in the code review:
- [ ] Fix `requirements.txt` to include all actual dependencies.
- [ ] Remove debug print statements and move them to a management command.
- [ ] Fix the JS SSE error-swallowing bug.
- [ ] Implement `asyncio.to_thread` for blocking RAG calls.
- [ ] Ensure RAG only stores User statements (no AI hallucinations).
- [ ] Set `DEBUG=False` by default and enforce `SECRET_KEY`.