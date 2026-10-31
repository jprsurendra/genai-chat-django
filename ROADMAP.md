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
| `006-rag-quality` | Hybrid search, query rewriting, evaluation (reranking carried over) | ✅ Done |
| `007-agent-tools` | Function calling, bigger models | ⏭️ Next up |
| `008-production` | Redis, Celery, Docker, observability | ⏳ Upcoming |
| `009-voice-ui` | Voice, vision, Hindi UI | 💭 Future (optional) |

---

## Where we are now

The app now has login, chat history in MySQL, document upload and an **improved RAG engine**:

- **Hybrid search** (vector + BM25 keyword search) is implemented.
- **Query rewriting** turns follow-up questions (such as *"उसका दाम क्या है?"*) into complete questions before searching.
- `evaluate_rag.py` measures retrieval, but so far with only a handful of questions, so treat its score as a rough signal, not a guarantee.
- **Reranking** is not done yet and is carried over (see Branch 006 below).

**Next task:** Branch 007. Merge Branch 006 into `main`, then turn the chatbot into an agent by adding tool calling.

---

## ✅ Branch 006: `genai-chat-006-rag-quality` (done)

**Goal:** make retrieval accurate, so the AI answers from the right context and stops guessing.

- **Hybrid search:** ✅ implemented (vector search combined with BM25 keyword search).
- **Query rewriting:** ✅ implemented. A follow-up question is rewritten into a complete question using the earlier conversation, and only then searched.
- **Evaluation:** ✅ `evaluate_rag.py` built (5 test cases so far).
- **Reranking:** ⏳ not done. Carried over (see below).

**Carried over from this branch**

- Grow the evaluation set to 20 to 30 questions, including *negative* questions the document cannot answer (the app should return nothing relevant for them), and report Hit@1, Hit@3 and MRR instead of a single percentage.
- Add reranking with a cross-encoder model, and keep it only if the evaluation score improves.

---

## 🚀 Branch 007: `genai-chat-007-agent-tools` (next)

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

## 🎓 Deep Learning Track (learning goals, in parallel)

This project is meant to teach GenAI engineering, not only to ship features. These topics can be studied alongside the branches. Each one is tied to the branch where it is most useful.

### 1. 🧠 Inside the LLM (core math and architecture)
- **Transformers:** how self-attention works (*Attention Is All You Need*).
- **Tokenization:** BPE (Byte-Pair Encoding), and how tokens affect arithmetic and rare words.
- **Embeddings:** how text becomes numbers, and the different similarity metrics.
- **Resource:** Andrej Karpathy's *Let's build GPT from scratch*.

### 2. 🛠️ Fine-tuning and training
- **PEFT / LoRA:** fine-tune a model on a small GPU without training from scratch.
- **Hugging Face:** the `transformers` and `peft` libraries.
- **Data preparation:** formatting JSONL datasets for training.

### 3. 📚 Advanced RAG (builds on Branch 006)
- **Reranking:** cross-encoders such as `bge-reranker` (the item carried over from Branch 006).
- **Graph RAG:** storing data as a knowledge graph (nodes and edges).
- **Multi-vector retrieval:** several vectors per document (question, answer, summary).

### 4. 🤖 AI agents (Branch 007)
- **ReAct pattern:** reasoning and acting, so the model thinks before each step.
- **Multi-agent systems:** frameworks such as AutoGen, CrewAI or LangGraph.
- **MCP (Model Context Protocol):** an open standard for connecting AI to tools.

### 5. ⚡ Production and scaling (Branch 008)
- **LLMOps:** observability with Langfuse or LangSmith.
- **Evaluation:** RAGAS to measure RAG quality automatically.
- **High-performance serving:** vLLM or TGI (Text Generation Inference).

### 6. 🎨 Multimodal and vision (Branch 009)
- **Vision models:** LLaVA or GPT-4o Vision for image understanding.
- **Speech:** Whisper (speech to text) and text to speech.

---

## 🗂️ Ideas not yet scheduled

These came up in earlier branch notes and are not placed in a branch yet:

- 👍 / 👎 feedback buttons on answers, to collect data for evaluation.
- A **Stop generation** button (using `AbortController` in the frontend) to interrupt a response mid-way.

---

## 💡 Suggested next step

Merge Branch 006 into `main`, then start Branch 007 with the simplest tool first: the **calculator**. After that add **web search**, and the **database query** last, because it needs the most care with permissions. Keep local Ollama as the default and make the larger model an option. In parallel, keep growing the evaluation set, so the RAG quality does not quietly get worse while the app gains new features.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

अब तक हमारा project एक छोटे chatbot से बढ़कर एक पूरा GenAI application बन गया है, जिसमें login, database, RAG और file upload हैं। आगे की योजना यह है:

**Branch 006: RAG Quality (पूरी हुई ✅)**
लक्ष्य: retrieval को ज़्यादा सटीक बनाना, ताकि AI सही context से जवाब दे।
- **Hybrid Search:** ✅ Vector Search के साथ BM25 (keyword search)।
- **Query Rewriting:** ✅ follow-up सवाल (जैसे "उसका दाम क्या है?") को पहले पिछली बातचीत से पूरा सवाल बनाना, फिर search करना।
- **Evaluation:** ✅ `evaluate_rag.py` बना (अभी 5 सवाल)।
- **Reranking:** ⏳ अभी नहीं हुआ, आगे के लिए बचा है।
- **आगे के लिए बचा काम:** test set को 20-30 सवालों तक बढ़ाना (ऐसे सवाल भी जिनका जवाब document में नहीं है), और Hit@1, Hit@3, MRR नापना।

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

**🎓 Deep Learning Track (साथ-साथ सीखने के विषय):** LLM के अंदर (Transformers, Tokenization, Embeddings), Fine-tuning (LoRA/PEFT), Advanced RAG (Reranking, Graph RAG), AI Agents (ReAct, MCP), Production (Langfuse, RAGAS, vLLM) और Multimodal (Vision, Whisper)।

**मेरी सलाह:** Branch 006 को main में merge कीजिए, फिर Branch 007 में सबसे आसान tool (Calculator) से शुरू कीजिए। उसके बाद Web Search, और सबसे आख़िर में Database query। साथ-साथ evaluation set बढ़ाते रहिए, ताकि नए features जुड़ने पर RAG की गुणवत्ता चुपचाप न गिरे।

</details>