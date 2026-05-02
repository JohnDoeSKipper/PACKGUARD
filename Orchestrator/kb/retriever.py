"""
PackGuard — Knowledge Base Retriever (offline TF-IDF + FAISS)
"""

import os, sys, pickle
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KB_DIR     = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(KB_DIR, "index.faiss")
META_PATH  = os.path.join(KB_DIR, "cases_meta.pkl")
VECT_PATH  = os.path.join(KB_DIR, "tfidf_vectorizer.pkl")

_index = _cases = _vectorizer = None


def _load():
    global _index, _cases, _vectorizer
    if _index is not None:
        return
    import faiss
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(f"Run: python kb/embed.py  to build the index first.")
    _index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f: _cases = pickle.load(f)
    with open(VECT_PATH, "rb") as f: _vectorizer = pickle.load(f)


def retrieve(query: str, k: int = 3, min_similarity: float = 0.05) -> list:
    _load()
    X = _vectorizer.transform([query]).toarray().astype("float32")
    norm = np.linalg.norm(X)
    if norm > 0: X = X / norm
    scores, ids = _index.search(X, k)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0 or float(score) < min_similarity:
            continue
        case = dict(_cases[idx])
        case["similarity"] = round(float(score), 4)
        results.append(case)
    return results


def retrieve_for_lot(lot_state: dict, k: int = 3) -> list:
    app  = lot_state.get("target_application", "")
    pkg  = lot_state.get("package_type", "")
    modes, decisions = [], []
    for chk in lot_state.get("checkpoints", []):
        if not chk.get("skipped"):
            po = chk.get("physics_outputs", {})
            m = po.get("failure_mode", "")
            if m: modes.append(m)
            decisions.append(chk.get("decision", ""))
    query = f"{app} {pkg} {' '.join(modes)} {' '.join(set(decisions))}".strip()
    return retrieve(query, k=k)


if __name__ == "__main__":
    import sys as _sys
    q = _sys.argv[1] if len(_sys.argv) > 1 else "solder fatigue automotive BGA"
    print(f"Query: {q!r}\n")
    for r in retrieve(q, k=3):
        print(f"  [{r['id']}] sim={r['similarity']:.3f}  {r['defect_observed']}")
        print(f"       → {r['recommended_action'][:80]}...")
