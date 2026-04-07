"""
embedder.py
Uses sentence-transformers to embed commit messages and extract
semantic patterns (dominant themes, tone clusters).
"""

from typing import List, Dict
import numpy as np


def embed_commits(commit_messages: List[str], model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    """
    Embed commit messages using a lightweight sentence-transformer model.
    Returns an array of shape (n_commits, embedding_dim).
    """
    # Lazy import to avoid slow startup when not needed
    from sentence_transformers import SentenceTransformer

    if not commit_messages:
        return np.array([])

    model = SentenceTransformer(model_name)
    # Truncate messages to first line only for cleaner signal
    first_lines = [m.split("\n")[0][:200] for m in commit_messages]
    embeddings = model.encode(first_lines, show_progress_bar=False, normalize_embeddings=True)
    return embeddings


def cluster_commits(embeddings: np.ndarray, n_clusters: int = 4) -> Dict:
    """
    K-Means cluster commit embeddings. Returns cluster stats.
    """
    if embeddings is None or len(embeddings) < n_clusters:
        return {"n_clusters": 0, "cluster_sizes": [], "avg_intra_similarity": 0.0}

    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    # Clamp clusters to available samples
    k = min(n_clusters, len(embeddings))
    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(embeddings)

    cluster_sizes = [int(np.sum(labels == i)) for i in range(k)]

    # Silhouette score measures how tightly clustered commits are
    # High score → consistent commit style; low → diverse/chaotic
    sil = 0.0
    if k > 1 and len(embeddings) > k:
        try:
            sil = float(silhouette_score(embeddings, labels, sample_size=min(500, len(embeddings))))
        except Exception:
            sil = 0.0

    # Average cosine similarity within each cluster (measure of focus)
    intra_sims = []
    for i in range(k):
        cluster_embs = embeddings[labels == i]
        if len(cluster_embs) > 1:
            # All pairs cosine sim (embeddings already normalized)
            sim_matrix = cluster_embs @ cluster_embs.T
            upper = sim_matrix[np.triu_indices(len(cluster_embs), k=1)]
            intra_sims.append(float(np.mean(upper)))

    avg_intra_sim = float(np.mean(intra_sims)) if intra_sims else 0.0

    return {
        "n_clusters": k,
        "cluster_sizes": cluster_sizes,
        "silhouette_score": sil,
        "avg_intra_similarity": avg_intra_sim,
        # Consistency: high sil + high intra_sim = very consistent commit style
        "commit_consistency_score": round((max(sil, 0) + avg_intra_sim) / 2, 3),
    }


def get_embedding_features(commit_messages: List[str]) -> Dict:
    """
    Full pipeline: embed → cluster → return feature dict.
    Gracefully degrades if sentence-transformers unavailable.
    """
    if not commit_messages:
        return {"commit_consistency_score": 0.5, "n_clusters": 0}

    try:
        embeddings = embed_commits(commit_messages)
        cluster_stats = cluster_commits(embeddings)
        return cluster_stats
    except Exception as e:
        # Fallback: return neutral values so the app still works
        return {"commit_consistency_score": 0.5, "n_clusters": 0, "error": str(e)}
