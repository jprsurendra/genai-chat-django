### Branch 003: `genai-chat-003-rag` 🚧

**Goal:** 
To understand the mathematical foundation of RAG (Retrieval-Augmented Generation) by implementing **Embeddings** and calculating **Cosine Similarity** between different sentences (English and Hindi). This branch serves as the educational foundation before building a full Vector Database.

---

### Part 1: Understanding Embeddings & Similarity

Before we can build a smart document assistant, we need to understand how AI converts text into numbers (Vectors). We integrated Ollama's `nomic-embed-text` model to generate embeddings for our sentences and calculate their "Cosine Similarity".

**How it works:**
1. **Embedding:** Text is converted into a high-dimensional vector (an array of numbers).
2. **Cosine Similarity:** We calculate the angle between two vectors. A score of `1.0` means the sentences are identical, while `0.0` means they are completely unrelated.

#### Implementation Details

**1. `chat/utilities/rags/rag_engine.py`**
We created a `RAGEngine` class that uses `chromadb.utils.embedding_functions.OllamaEmbeddingFunction` and `numpy` to calculate the similarity.

**2. `chat/utilities/llms/llm.py`**
We added a `debug_embeddings` method to our `LLMService` to print these scores directly to the terminal whenever a user sends a message.

**3. `chat/views/chat_api_views.py`**
We hooked the `debug_embeddings` method into the `ChatAPIView` so every incoming message triggers the similarity check.

---

### Testing & Observations

We tested the system with the following test sentences to understand cross-language and contextual similarity:
- `"मुझे चाय पसंद है"` (Hindi)
- `"I love tea"` (English)
- `"मुझे कॉफ़ी बहुत पसंद है"` (Hindi)
- `"The weather is nice today"` (English)

#### Test Results (Terminal Output)

| User Input | Highest Similarity Match | Score | Observation |
|------------|--------------------------|-------|-------------|
| `I love tea` | `I love tea` | **1.0000** | Perfect match. |
| `is tea good for helth` | `I love tea` | **0.7045** | The model correctly linked the word "tea". |
| `I like softdrink` | `I love tea` | **0.4720** | Low score. The model correctly identified that a "softdrink" is not closely related to "tea" or "coffee". |

#### AI Chat Response vs. Embedding Score

We noticed an interesting difference between the **Embedding Score** and the **LLM Response**:
1. **Prompt:** `I love tea` → **AI Response:** *"I'm sorry, but I'm not sure what you're asking for..."*
   - **Why?** Small models (1.5B) get confused by statements. They expect a question.
2. **Prompt:** `is tea good for helth` → **AI Response:** A detailed explanation of tea's health benefits (antioxidants, caffeine, etc.).
   - **Why?** This was a clear question. Note that this answer came from the LLM's pre-trained knowledge, **not** from our RAG database (since we haven't stored anything in ChromaDB yet).

---

### Educational Takeaways

1. **Embeddings are Language-Agnostic (to an extent):** `"मुझे चाय पसंद है"` and `"I love tea"` had a similarity score of **0.4186**. The model knows they are related, even though the words are completely different.
2. **Statements vs. Questions:** Local LLMs are trained to be assistants. If you just say "I love tea", they don't know how to reply. You must ask a question (e.g., "Tell me about tea").
3. **The Power of Similarity:** RAG works by finding the highest similarity scores. If a user asks a question, the system will search the database for the sentence with the highest score and feed it to the LLM as context.

---

### Next Steps for Branch 003

- [ ] **Full Vector Store:** Use ChromaDB to store chunks of data (like our chat history) instead of just calculating similarity on the fly.
- [ ] **Retrieval & Augmentation:** Update `_build_messages` in `llm.py` to inject the retrieved context into the System Prompt.
- [ ] **UI Update:** Add a "File Upload" button to the frontend so users can upload PDFs/text files for the AI to read.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**ब्रांच 003 का मकसद:**
RAG (Retrieval-Augmented Generation) को गहराई से समझने के लिए हमने पहले **Embeddings** और **Cosine Similarity** (समानता) को लागू किया। यह एक एजुकेशनल बेस है ताकि हम समझ सकें कि AI टेक्स्ट को नंबरों में कैसे बदलता है।

**कैसे काम करता है?**
1. **Embedding:** जब हम कोई वाक्य भेजते हैं, तो Ollama का `nomic-embed-text` मॉडल उसे नंबरों की एक बड़ी लिस्ट (Vector) में बदल देता है।
2. **Similarity:** हम दो वाक्यों के वेक्टर के बीच का एंगल (Angle) निकालते हैं। स्कोर `1.0` का मतलब दोनों वाक्य एक जैसे हैं, और `0.0` का मतलब कोई संबंध नहीं है।

**हमारे टेस्ट के कुछ दिलचस्प नतीजे:**
- जब हमने `I love tea` भेजा, तो उसका खुद के साथ स्कोर **1.0000** आया (परफेक्ट मैच)।
- जब हमने `is tea good for helth` पूछा, तो उसने `I love tea` के साथ **0.70** का स्कोर दिया (क्योंकि दोनों में 'tea' है)।
- जब हमने `I like softdrink` भेजा, तो स्कोर कम आया, क्योंकि सॉफ्ट ड्रिंक और चाय में कोई खास समानता नहीं है।

**एक और दिलचस्प बात (AI का जवाब):**
- जब हमने सिर्फ `I love tea` (बिना सवाल के) लिखा, तो AI कन्फ्यूज हो गया और बोला *"I'm not sure what you're asking"*।
- लेकिन जब हमने `is tea good for helth` पूछा, तो AI ने चाय के फायदे और नुकसान बहुत अच्छे से बताए। (ध्यान दें: यह जवाब AI के अपने दिमाग से आया है, RAG से नहीं, क्योंकि हमने अभी डेटाबेस में कुछ सेव नहीं किया है)।

**अगला कदम:**
अब हम ChromaDB में डेटा को सेव करना (Vector Store) और फिर उसे AI के जवाब में इस्तेमाल करना (Retrieval) सीखेंगे।

</details>