import os
import django

# Setup Django environment to access models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chat.utilities.rags.rag_engine import RAGEngine

# ==========================================
# 1. TEST DATASET
# ==========================================
# You can add 20-30 questions here based on the PDF you uploaded.
# Format: {"query": "Your question", "expected_keywords": ["keyword1", "keyword2"]}
TEST_CASES = [
    {
        "query": "Who wrote the famous book The Guide?",
        "expected_keywords": ["R.K. Narayan", "R. K. Narayan"]
    },
    {
        "query": "What is the capital of South Korea?",
        "expected_keywords": ["Seoul"]
    },
    {
        "query": "Complete the proverb: It's better to be safe than...",
        "expected_keywords": ["Sorry"]
    },
    {
        "query": "Who is the Prime Minister of the United Kingdom?",
        "expected_keywords": ["Keir Starmer"]
    },
    {
        "query": "What is the answer to 2+2?",
        "expected_keywords": ["4", "four"]
    }
]


# ==========================================
# 2. EVALUATION LOGIC
# ==========================================
def evaluate_retrieval(user_id: str):
    rag = RAGEngine()
    total_queries = len(TEST_CASES)
    hits = 0

    print(f"\\n{'=' * 60}")
    print(f"🚀 STARTING RAG EVALUATION (User ID: {user_id})")
    print(f"{'=' * 60}\\n")

    for i, case in enumerate(TEST_CASES, 1):
        query = case["query"]
        expected = case["expected_keywords"]

        # Fetch top 3 documents/memories
        docs = rag.retrieve_documents(query, user_id, top_k=3)
        memories = rag.retrieve_memories(query, user_id, top_k=3)

        # Combine retrieved texts
        retrieved_text = " ".join([d["text"] for d in docs]).lower()
        retrieved_text += " " + " ".join([m["text"] for m in memories]).lower()

        # Check if any expected keyword is in the retrieved text
        match_found = any(keyword.lower() in retrieved_text for keyword in expected)

        if match_found:
            hits += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        print(f"Test {i}: {query}")
        print(f"Status: {status}")
        print(f"Expected: {expected}")

        if docs:
            print(f"Top Match: [{docs[0]['filename']}, Page {docs[0]['page']}]")
            print(f"Text: {docs[0]['text'][:100]}...")
        else:
            print("Top Match: None")
        print("-" * 60)

    # Calculate Accuracy
    accuracy = (hits / total_queries) * 100
    print(f"\\n📊 FINAL SCORE: {hits}/{total_queries} ({accuracy:.1f}% Accuracy)\\n")


if __name__ == "__main__":
    # You must pass the user_id of the user who uploaded the documents
    # For testing, if you uploaded the PDF as user 1, pass "1"
    evaluate_retrieval(user_id="1")
