# Branch 006: `genai-chat-006-rag-quality` ✅

**Goal:** 
To improve the accuracy and reliability of the RAG (Retrieval-Augmented Generation) system. This branch focused on moving beyond basic Vector Search by implementing **Hybrid Search (BM25 + Vector)**, **Query Rewriting**, and a proper **Evaluation Framework**.

---

## 🚨 Problem Statement (Before Branch 006)

In Branch 005, the chatbot had a basic RAG setup using only Vector Search (Cosine Similarity). We discovered two major flaws during testing:

1. **The "2+2" Problem (Negative Test Failure):**
   When asked a question not present in the PDF (like "2+2"), the AI still returned random document chunks because Vector Search only looks at "meaning", not exact keywords.
   
2. **The "Follow-up" Problem (Pronoun Confusion):**
   If a user asked *"Who is the PM of UK?"* and then followed up with *"How old is he?"*, the RAG engine would search for the word "he" and fail to find the correct context.

---

## 🛠️ What Changed in this Branch?

### 1. Hybrid Search (BM25 + Vector)
We replaced the pure Vector Search with a Hybrid approach.
- **Vector Search:** Finds documents based on semantic meaning (Cosine Similarity).
- **BM25 (Keyword Search):** Finds documents based on exact keyword matches using the `rank_bm25` library.
- **Improved Tokenizer:** We wrote a custom tokenizer (`_tokenize`) that converts text to lowercase, removes punctuation, and ignores short words (like "2", "+", "is", "the"). This fixed the "2+2" issue.
- **Combined Score:** `(0.5 * Vector Score) + (0.5 * BM25 Score)`. If the score is below `0.35`, the document is rejected.

### 2. Query Rewriting
We added a new method `_rewrite_query` in `LLMService`.
- Before searching the database, the AI now looks at the last 4 messages of chat history.
- It rewrites the user's follow-up question into a **Standalone Question** (e.g., "How old is he?" becomes "How old is Keir Starmer?").
- This rewritten query is then sent to the Hybrid Search engine.

### 3. Evaluation Script (`evaluate_rag.py`)
We created a Python script to measure the RAG engine's accuracy.
- **Metrics Used:** Hit@1, Hit@3, MRR (Mean Reciprocal Rank), and Negative Test.
- **Test Cases:** 5 questions (4 positive from the PDF, 1 negative not in the PDF).
- **Result:** After fixing the tokenizer and adding Hybrid Search, the Negative Test passed (0 docs returned for "2+2").

---

## 📊 Test Results (After Fixes)

| Metric | Score |
|--------|-------|
| Hit@1 (Top result is correct) | 4/4 (100%) |
| Hit@3 (Top 3 results contain answer) | 4/4 (100%) |
| MRR (Mean Reciprocal Rank) | 1.00 |
| Negative Test (Rejected irrelevant) | 1/1 (PASSED) |

---

## 🎓 Educational Takeaways

1. **Vector Search is not enough:** It is great for semantic meaning, but terrible for exact matches (names, numbers). Hybrid Search is required for a robust system.
2. **Tokenization matters:** A simple `.split()` is not enough. Removing punctuation and stopwords is crucial for BM25 to work correctly.
3. **Query Rewriting improves UX:** Users shouldn't have to type full sentences every time. Query Rewriting makes the AI feel much more natural to talk to.

---

## 🚀 Next Steps for Branch 007
- [ ] **Security Hardening:** Fix media access, prompt injection, and rate limiting.
- [ ] **Agent Tools:** Implement Function Calling (Calculator, Web Search).

---

<details>
<summary><b>🇮🇳 हिंदी में समझें (Click to expand Hindi Explanation)</b></summary>

<br>

**इस ब्रांच का मकसद:**
RAG की सटीकता को बढ़ाना। हमने पहले देखा कि "2+2" पूछने पर हमारा RAG गलत जवाब दे रहा था। इस ब्रांच में हमने उसे ठीक किया।

**मुख्य बदलाव:**
1. **Hybrid Search:** हमने सिर्फ Vector Search (मतलब) की जगह **BM25 (कीवर्ड)** भी जोड़ा। अब स्कोर `(50% Vector + 50% BM25)` होता है।
2. **Improved Tokenizer:** हमने छोटे शब्दों (जैसे "2", "+") और विराम चिह्नों को इग्नोर करना सीखा। इससे "2+2" का स्कोर 0 हो गया और वह रिजेक्ट हो गया।
3. **Query Rewriting:** अब अगर आप पूछेंगे *"How old is he?"*, तो AI पहले पुरानी चैट से समझेगा कि "he" कौन है, और फिर सवाल को पूरा बनाकर सर्च करेगा।

**नतीजा:**
अब हमारा RAG सही सवालों को 100% ढूँढ रहा है और गलत सवालों (2+2) को रिजेक्ट कर रहा है।

</details>