import os
import re
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chat.utilities.rags.rag_engine import RAGEngine

# ==========================================
# 1. TEST DATASET
# ==========================================
TEST_CASES = [
    {
        "query": "Who wrote the famous book The Guide?",
        "pattern": r"R\.\s?K\.\s?Narayan"
    },
    {
        "query": "What is the capital of South Korea?",
        "pattern": r"\bSeoul\b"
    },
    {
        "query": "Complete the proverb: It's better to be safe than...",
        "pattern": r"\bSorry\b"
    },
    {
        "query": "Who is the Prime Minister of the United Kingdom?",
        "pattern": r"Keir Starmer"
    },
    {
        # NEGATIVE TEST: This question is NOT in the PDF.
        # The RAG should return 0 documents (if distance cutoff works).
        "query": "What is the answer to 2+2?",
        "pattern": None
    }
]


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def first_hit_rank(docs, pattern):
    """
    Returns the rank (1, 2, 3...) of the first document that matches the regex pattern.
    If no match is found, returns None.
    """
    for rank, d in enumerate(docs, 1):
        if re.search(pattern, d["text"], re.IGNORECASE):
            return rank
    return None


# ==========================================
# 3. EVALUATION LOGIC
# ==========================================
def evaluate_retrieval(user_id: str):
    rag = RAGEngine()

    # Metrics
    hit1 = 0
    hit3 = 0
    n_pos = 0
    neg_ok = 0
    n_neg = 0
    mrr = 0.0

    print(f"\n{'=' * 60}")
    print(f"🚀 STARTING RAG EVALUATION (User ID: {user_id})")
    print(f"{'=' * 60}\n")

    for i, case in enumerate(TEST_CASES, 1):
        query = case["query"]
        pattern = case["pattern"]

        # Only retrieve from documents (we exclude memories to keep the test clean)
        docs = rag.retrieve_documents(query, user_id, top_k=3)

        print(f"Test {i}: {query}")

        # --- Negative Test Logic ---
        if pattern is None:
            n_neg += 1
            ok = len(docs) == 0  # Pass only if NO irrelevant documents are returned
            if ok:
                neg_ok += 1
            status = "✅ PASS" if ok else "❌ FAIL"
            print(f"Status: {status} (Expected: 0 docs, Found: {len(docs)})")
            print("-" * 60)
            continue

        # --- Positive Test Logic ---
        n_pos += 1
        rank = first_hit_rank(docs, pattern)

        if rank == 1:
            hit1 += 1
            hit3 += 1
            mrr += 1.0
            status = "✅ PASS (Rank 1)"
        elif rank in (2, 3):
            hit3 += 1
            mrr += 1 / rank
            status = f"🟡 PASS (Rank {rank})"
        else:
            status = "❌ FAIL"

        print(f"Status: {status}")
        print(f"Expected Pattern: {pattern}")

        # Show the top match for debugging
        if docs:
            print(f"Top Match: [{docs[0]['filename']}, Page {docs[0]['page']}]")
            print(f"Text snippet: {docs[0]['text'][:100]}...")
        else:
            print("Top Match: None")
        print("-" * 60)

    # --- Final Results ---
    accuracy_hit1 = (hit1 / n_pos) * 100 if n_pos > 0 else 0
    accuracy_hit3 = (hit3 / n_pos) * 100 if n_pos > 0 else 0
    avg_mrr = mrr / n_pos if n_pos > 0 else 0

    print(f"\n📊 FINAL SCORE")
    print(f"Positive Tests: {n_pos}")
    print(f"Hit@1 (Top result is correct): {hit1}/{n_pos} ({accuracy_hit1:.1f}%)")
    print(f"Hit@3 (Top 3 results contain answer): {hit3}/{n_pos} ({accuracy_hit3:.1f}%)")
    print(f"MRR (Mean Reciprocal Rank): {avg_mrr:.2f}")
    print(f"Negative Test (Rejected irrelevant): {neg_ok}/{n_neg}\n")


if __name__ == "__main__":
    # Replace "1" with the ID of the user who uploaded the PDF
    evaluate_retrieval(user_id="1")