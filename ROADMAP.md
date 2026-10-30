# GenAI Chat: Roadmap

This document tracks what has been built so far and what is planned next. The project started as a small streaming chatbot and has grown into a multi-user app with login, a database, RAG and file upload. Each step lives in its own branch (see [Branch History](README.md#13-branch-history) in the main README for the Git workflow).

> The plan below is a working plan, not a promise. Branches may be reordered or split as we learn what actually matters.

---

## At a glance

| Branch | Main feature | Status |
|--------|--------------|--------|
| `001-basic` | Streaming chatbot (Django + Ollama) | ✅ Done |
| `002-system-prompt` | System prompt and the AI's identity | ✅ Done |
| `003-rag` | Embeddings, ChromaDB, PDF upload | ✅ Done |
| `004-clean-up` | Session isolation, show sources | ✅ Done |
| `005-db-auth` | MySQL, JWT login, file storage | ✅ Done |
| `006-rag-quality` | Hybrid search, query rewriting, reranking, evaluation | 🚧 In progress |
| `007-agent-tools` | Function calling, bigger models | ⏳ Upcoming |
| `008-production` | Redis, Celery, Docker, observability | ⏳ Upcoming |
| `009-voice-ui` | Voice, vision, Hindi UI | 💭 Future (optional) |

---

## Where we are now

The app now has login, chat history in MySQL, document upload and RAG. The weak spot is **answer quality**: retrieval sometimes returns the wrong or duplicated chunks, and we have only checked it with a handful of questions. That is why Branch 006 comes before anything new and shiny.

**First task in Branch 006:** build a proper evaluation set, so every later change can be measured instead of judged by feel.

---

## 🚧 Branch 006: `genai-chat-006-rag-quality` (in progress)

**Goal:** make retrieval accurate, so the AI answers from the right context and stops guessing.

- **Hybrid search:** combine vector search with BM25 keyword search. Work on this has already started.
- **Query rewriting:** when the user asks a follow-up such as *"उसका दाम क्या है?"* ("what is its price?"), the AI first rewrites it into a complete question using the earlier conversation, and only then searches.
- **Reranking:** take the results of the search and re-rank them with a reranker model.
- **Evaluation:** build a test set of 20 to 30 questions and measure a real score. So far we have only tried 5 questions.

---

## 🚀 Branch 007: `genai-chat-007-agent-tools` (upcoming)

**Goal:** turn the chatbot into an agent that can do things, not only answer.

- **Tool calling (function calling):** give the AI tools such as:
  - **Web search** for fresh information from the internet.
  - **Calculator** for maths questions (the classic `2+2`).
  - **Database query** against MySQL (for example "how many users registered today?").
- **Multi-step reasoning:** the AI decides which tool to use and when.
- **Bigger LLMs:** small models (1.5B) are weak at tool calling, so this branch moves to a larger model, either OpenAI (GPT-4o) or a hosted Llama 3 70B.

> ⚠️ This is the first time the app may depend on something that is not fully local. The `LLM_PROVIDER` setting already allows switching between Ollama and OpenAI, so the plan is to keep local Ollama as the default and make the larger model an option.

---

## ⚡ Branch 008: `genai-chat-008-production` (upcoming)

**Goal:** get the app ready for real users: scalable and safer.

- **Redis caching:** cache answers to frequently asked questions, so there are fewer LLM calls and responses are faster.
- **Background indexing (Celery):** process large PDF uploads in the background, so the UI does not freeze.
- **Docker Compose:** run the whole stack (Django, MySQL, Redis, Ollama) with one command.
- **Observability:** logs and tracing (for example Langfuse), so we can see how the AI is actually performing.
- **UI/UX polish:** dark mode, loading spinners and clearer error messages.

---

## 💬 Branch 009: `genai-chat-009-voice-ui` (future, optional)

**Goal:** go beyond text.

- **Voice input and output:** ask questions by speaking and listen to the answers, using the browser's Speech API.
- **Vision (image upload):** upload an image and ask about it (for example "what is in this photo?").
- **Hindi UI:** translate the whole interface into Hindi.

---

## 🗂️ Ideas not yet scheduled

These came up in earlier branch notes and are not placed in a branch yet:

- 👍 / 👎 feedback buttons on answers, to collect data for evaluation.
- A **Stop generation** button (using `AbortController` in the frontend) to interrupt a response mid-way.

---

## 💡 Suggested next step

Stay in Branch 006 and finish the **evaluation set** first. Without a trustworthy score we cannot tell whether hybrid search, query rewriting or reranking actually help. Once the RAG quality is measured and good enough, move on to Branch 007 and start giving the AI tools.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

अब तक हमारा project एक छोटे chatbot से बढ़कर एक पूरा GenAI application बन गया है, जिसमें login, database, RAG और file upload हैं। आगे की योजना यह है:

**Branch 006: RAG Quality (अभी चल रही है)**
लक्ष्य: retrieval को ज़्यादा सटीक बनाना, ताकि AI सही context से जवाब दे।
- **Hybrid Search:** Vector Search के साथ BM25 (keyword search)।
- **Query Rewriting:** follow-up सवाल (जैसे "उसका दाम क्या है?") को पहले पिछली बातचीत से पूरा सवाल बनाना, फिर search करना।
- **Reranking:** search के results को Reranker model से दोबारा rank करना।
- **Evaluation:** 20-30 सवालों का test set बनाकर असली score नापना (अभी सिर्फ़ 5 सवाल आज़माए हैं)।

**Branch 007: Agent Tools**
लक्ष्य: chatbot को ऐसा Agent बनाना जो काम भी कर सके।
- **Tool Calling:** Web Search, Calculator और MySQL से data निकालना।
- **Multi-Step Reasoning:** AI खुद तय करे कि कौन सा tool कब इस्तेमाल करना है।
- **Bigger LLMs:** छोटे model (1.5B) tool calling में कमज़ोर हैं, इसलिए बड़े model (GPT-4o या Llama 3 70B) पर switch करना। Local Ollama default रहेगा।

**Branch 008: Production**
लक्ष्य: ऐप को असली users के लिए तैयार करना।
- **Redis Caching**, **Celery** (बड़े PDF का background processing), **Docker Compose** (एक command में पूरा app), **Observability** (Langfuse जैसे tools) और UI polish (dark mode, loading spinner, बेहतर error messages)।

**Branch 009: Voice / UI (optional)**
- Voice input/output, Image upload (Vision) और पूरा Hindi UI।

**मेरी सलाह:** अभी Branch 006 में रहें और पहले Evaluation set ठीक से बनाएँ, ताकि पता चले कि हमारा RAG कितना सही है। फिर Branch 007 पर जाकर AI को tools देना सीखें।

</details>