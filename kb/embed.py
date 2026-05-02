"""
PackGuard — Knowledge Base Embedder (offline TF-IDF version)
No internet / HuggingFace required.
Uses sklearn TfidfVectorizer + FAISS for similarity search.

Run once:  python kb/embed.py
Re-run every time cases.json is updated.
"""

import json, os, sys, pickle
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KB_DIR     = os.path.dirname(os.path.abspath(__file__))
CASES_PATH = os.path.join(KB_DIR, "cases.json")
INDEX_PATH = os.path.join(KB_DIR, "index.faiss")
META_PATH  = os.path.join(KB_DIR, "cases_meta.pkl")
VECT_PATH  = os.path.join(KB_DIR, "tfidf_vectorizer.pkl")


def build_index():
    try:
        import faiss
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
    except ImportError:
        print("Run: pip install faiss-cpu scikit-learn")
        sys.exit(1)

    with open(CASES_PATH) as f:
        cases = json.load(f)
    print(f"Loaded {len(cases)} cases")

    texts = []
    for c in cases:
        text = " ".join(filter(None, [
            c.get("defect_observed",""), c.get("root_cause",""),
            c.get("recommended_action",""), c.get("application",""),
            c.get("package_type",""), c.get("physics_model",""),
            f"checkpoint {c.get('checkpoint','')}", c.get("outcome",""),
        ]))
        texts.append(text)

    vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=4096, sublinear_tf=True)
    X = vectorizer.fit_transform(texts).toarray().astype("float32")
    # L2-normalise → inner product == cosine similarity
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1
    X = X / norms

    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)

    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f: pickle.dump(cases, f)
    with open(VECT_PATH, "wb") as f: pickle.dump(vectorizer, f)

    print(f"✓ FAISS index built: {X.shape[0]} cases, dim={X.shape[1]}")
    return len(cases)


if __name__ == "__main__":
    build_index()
