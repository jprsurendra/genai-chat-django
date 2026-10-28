### Branch 003: `genai-chat-003-rag` 🚧

**Goal:** 
To understand the mathematical foundation of RAG (Retrieval-Augmented Generation) by implementing **Embeddings**, calculating **Cosine Similarity**, and finally building a **Local Vector Store (ChromaDB)** to give the AI external knowledge.

---

### Part 1: Understanding Embeddings & Similarity

Before we can build a smart document assistant, we need to understand how AI converts text into numbers (Vectors). We integrated Ollama's `nomic-embed-text` model to generate embeddings for our sentences and calculate their "Cosine Similarity".

**How it works:**
1. **Embedding:** Text is converted into a high-dimensional vector (an array of numbers).
2. **Cosine Similarity:** We calculate the angle between two vectors. A score of `1.0` means the sentences are identical, while `0.0` means they are completely unrelated.

#### Testing & Observations (Part 1)

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
2. **Prompt:** `is tea good for helth` → **AI Response:** A detailed explanation of tea's health benefits.
   - **Why?** This was a clear question. Note that this answer came from the LLM's pre-trained knowledge, **not** from our RAG database.

---

### Part 2: Simple Vector Store (Manual) & RAG Integration

**Goal:** 
To store manual documents in a local Vector Database (ChromaDB) and retrieve them to answer user queries accurately.

**How it works:**
1. **Store:** We created a manual knowledge base (e.g., "Delhi भारत की राजधानी है") and stored it in ChromaDB using the `store_documents()` method.
2. **Retrieve:** When a user asks a question, the `retrieve_similar()` method searches ChromaDB for the most relevant document.
3. **Augment:** The retrieved document is injected into the `SYSTEM_PROMPT` in `_build_messages()`.
4. **Generate:** The LLM uses this context to generate an accurate answer.

#### The "Delhi" Test & The Hallucination

When we asked **"Delhi कहाँ है?"** without RAG, the small model (1.5B) hallucinated and answered: *"Delhi अमेरिका में है।"* (Delhi is in America). 

After integrating ChromaDB and injecting the context, the retrieval system successfully found: *"Delhi भारत की राजधानी है।"* 

**The "Hertz" Hallucination (Model Limitation):**
Even after providing the correct context, we encountered a funny hallucination. The AI generated:
> **"Delhi हार्ट्ज की राजधानी है।"** (Delhi is the capital of Hertz).

**Why did this happen?**
Our RAG engine successfully retrieved the exact text ("Delhi भारत की राजधानी है।"). However, the small language model failed to read the word "भारत" (Bharat) correctly and hallucinated "हार्ट्ज" (Hertz) due to its limited vocabulary and tokenizer. 

**The Final Fix:**
We updated the System Prompt to be stricter, instructing the model to *"Read the following context carefully and copy the exact words"*. 

**Final Result:**
- **User Query:** `Delhi कहाँ है?`
- **Vector Store Retrieval:** `"Delhi भारत की राजधानी है।"`
- **LLM Output:** **"Delhi भारत की राजधानी है।"** (No hallucination!)

*(Screenshot: `docs/screenshot_003_rag.png`)*

---

### Educational Takeaways

1. **Embeddings are Language-Agnostic:** `"मुझे चाय पसंद है"` and `"I love tea"` had a similarity score of **0.4186**. The model knows they are related, even though the words are completely different.
2. **Statements vs. Questions:** Local LLMs are trained to be assistants. If you just say "I love tea", they don't know how to reply. You must ask a question.
3. **The Power of Similarity:** RAG works by finding the highest similarity scores. If a user asks a question, the system searches the database and feeds the top results to the LLM.
4. **RAG vs. Model Size:** RAG provides the correct context, but the final generation still depends on the model's ability to read that context. For perfect Hindi/English generation, larger models (8B+) are recommended.

---

### Next Steps for Branch 003

- [ ] **Full Document Upload:** Create an API endpoint and UI button to upload PDFs/text files directly.
- [ ] **Chunking Strategy:** Implement a text splitter to break large documents into smaller chunks before embedding.
- [ ] **Chat History Embedding:** Embed previous conversations so the AI remembers older sessions.

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**ब्रांच 003 का मकसद:**
RAG (Retrieval-Augmented Generation) को गहराई से समझने के लिए हमने पहले **Embeddings** और **Cosine Similarity** (समानता) को लागू किया, और फिर एक **लोकल वेक्टर डेटाबेस (ChromaDB)** बनाया।

**भाग 1: Embeddings और Similarity**
- **कैसे काम करता है?** AI टेक्स्ट को नंबरों की लिस्ट (Vector) में बदल देता है। हम दो वाक्यों के वेक्टर के बीच का एंगल निकालते हैं। स्कोर `1.0` का मतलब दोनों वाक्य एक जैसे हैं।
- **हमारे टेस्ट:** `I love tea` का खुद के साथ स्कोर **1.0000** आया। जब हमने सिर्फ बयान (Statement) दिया, तो AI कन्फ्यूज हो गया। जब सवाल पूछा, तो उसने अपने ज्ञान से जवाब दिया।

**भाग 2: Vector Store और RAG Integration**
- **RAG का जादू:** जब हमने पूछा **"Delhi कहाँ है?"**, तो RAG से पहले AI ने गलत बोला *"Delhi अमेरिका में है"*।
- **डेटाबेस में सेव करने के बाद:** हमने ChromaDB में *"Delhi भारत की राजधानी है"* सेव किया। जब यूज़र ने सवाल पूछा, तो सिस्टम ने सही डॉक्यूमेंट ढूँढ निकाला और AI को दिया।
- **"हार्ट्ज" वाली मज़ेदार गलती:** छोटे मॉडल ने "भारत" को पढ़ने के बजाय "हार्ट्ज" (Hertz) लिख दिया। 
- **समाधान:** हमने Prompt को सख्त किया और AI ने आखिरकार सही जवाब दिया: **"Delhi भारत की राजधानी है।"**

**अंतिम सीख:**
RAG सही कॉन्टेक्स्ट देता है, लेकिन उसे सही से पढ़ने के लिए बड़े मॉडल (जैसे 8B) की ज़रूरत होती है। छोटे मॉडल्स (1.5B) कभी-कभी शब्दों को गलत पढ़ सकते हैं।

</details>


---

### Under the Hood: What is the `chroma_db` folder?

When you run the application and store documents (like our manual knowledge base), you will notice a new folder created at `rag/rag_data/chroma_db`. 

This folder is the **Local Vector Database** created by ChromaDB. It is the "brain" or "memory" of our RAG system. It ensures that your data is saved to your hard drive and persists even if you restart the server.

#### What's inside the folder?
1. **`chroma.sqlite3`**: This is the main relational database. It stores the metadata, such as which vector belongs to which text document and its unique ID. (Similar to an index page of a book).
2. **Long UID Folders (e.g., `ff72dbe1-33d1-4ce5-970c-8fdcd31af542`)**: These folders contain the actual **Vector Embeddings** (arrays of numbers) stored in a binary format. (Similar to the actual content pages of the book).

#### How is it used?
Whenever a user asks a question, the `RAGEngine` queries this database. ChromaDB calculates the similarity between the user's query vector and the millions of vectors stored in this folder to find the most relevant context.

#### ⚠️ Important Maintenance Rules:
- **Never commit this folder to Git/GitHub:** Because this is local binary data, it will bloat your repository. Add `rag/rag_data/chroma_db/` to your `.gitignore` file.
- **How to reset the database:** If you want to wipe the AI's memory and start fresh, simply stop the server, delete the `chroma_db` folder, and restart the server. ChromaDB will automatically create a new, empty one.

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**`chroma_db` फोल्डर क्या है?**
यह फोल्डर ChromaDB द्वारा बनाया गया एक **लोकल वेक्टर डेटाबेस** है। इसे आप हमारे RAG सिस्टम का "दिमाग" या "मेमोरी" समझ सकते हैं। यह आपके डेटा को आपकी हार्ड डिस्क पर सेव करता है, ताकि सर्वर रीस्टार्ट होने पर भी डेटा गायब न हो।

**इसके अंदर क्या होता है?**
1. **`chroma.sqlite3`**: यह मुख्य डेटाबेस है जो यह बताता है कि कौन सा वेक्टर किस टेक्स्ट से जुड़ा है (जैसे किताब का इंडेक्स)।
2. **लंबे नाम वाले फोल्डर (UUID)**: इनके अंदर आपके टेक्स्ट के असली **Vectors** (नंबरों की लिस्ट) बाइनरी फॉर्मेट में सेव होते हैं।

**इसका इस्तेमाल कैसे होता है?**
जब भी आप कोई सवाल पूछते हैं, तो `RAGEngine` इसी फोल्डर में जाकर सबसे मिलता-जुलता वेक्टर ढूंढता है और उसे AI को भेजता है।

**ध्यान रखने वाली बातें:**
- **GitHub पर पुश न करें:** इसे अपनी `.gitignore` में जोड़ लें (`rag/rag_data/chroma_db/`), क्योंकि यह लोकल डेटा है।
- **डेटा रीसेट कैसे करें:** अगर आप AI की मेमोरी साफ करना चाहते हैं, तो सर्वर बंद करें, इस फोल्डर को डिलीट करें, और सर्वर दोबारा चालू करें। ChromaDB अपने आप एक नया खाली डेटाबेस बना लेगा।

</details>

---