import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine


def get_embedding(text: str) -> list:
    # 텍스트 자체를 저장 (TF-IDF는 검색 시점에 계산)
    return [text]


def find_similar_cases(query_text: str, cases: list, top_k: int = 3, threshold: float = 0.08) -> list:
    if not cases:
        return []

    valid_cases = [c for c in cases if c[7]]  # embedding 필드가 있는 것만
    if not valid_cases:
        return []

    # approval_summary 기반으로 TF-IDF 유사도 계산
    corpus = [query_text] + [c[4] for c in valid_cases]  # c[4] = approval_summary

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
    try:
        tfidf = vectorizer.fit_transform(corpus)
    except Exception:
        return []

    sims = sk_cosine(tfidf[0:1], tfidf[1:]).flatten()

    results = []
    for case, sim in zip(valid_cases, sims):
        if sim >= threshold:
            c_id, ts, name, dept, summary, article, line, _ = case
            results.append({
                "id": c_id,
                "timestamp": ts,
                "department": dept,
                "approval_summary": summary,
                "adopted_article": article,
                "approval_line": line,
                "similarity": round(float(sim) * 100, 1),
            })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]
