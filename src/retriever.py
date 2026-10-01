import re

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from src.config import (
    CANDIDATES,
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    RERANK_MODEL,
    TOP_K,
)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
 
 
def tokenize(text):
    return re.findall(r"\w+", text.lower())
 
 
class Retriever:
    """Hybrid retriever with optional per-user document filtering.
 
    `allowed` is a set of source file names the caller may see.
    None means unrestricted; an empty set means nothing is visible.
    """
 
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.reranker = CrossEncoder(RERANK_MODEL)
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.col = client.get_collection(COLLECTION_NAME)
 
        data = self.col.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.docs = data["documents"]
        self.metas = data["metadatas"]
        self.bm25 = BM25Okapi([tokenize(d) for d in self.docs])
 
    @staticmethod
    def _item(id_, text, meta):
        return {"id": id_, "text": text,
                "source": meta["source"], "page": meta["page"]}
 
    def semantic(self, query, k=TOP_K, allowed=None):
        kwargs = {}
        if allowed is not None:
            kwargs["where"] = {"source": {"$in": list(allowed)}}
        emb = self.model.encode(QUERY_PREFIX + query,
                                normalize_embeddings=True).tolist()
        res = self.col.query(query_embeddings=[emb], n_results=k, **kwargs)
        return [self._item(i, d, m) for i, d, m in
                zip(res["ids"][0], res["documents"][0], res["metadatas"][0])]
 
    def keyword(self, query, k=TOP_K, allowed=None):
        scores = self.bm25.get_scores(tokenize(query))
        idx = [i for i in range(len(scores))
               if allowed is None or self.metas[i]["source"] in allowed]
        top = sorted(idx, key=lambda i: scores[i], reverse=True)[:k]
        return [self._item(self.ids[i], self.docs[i], self.metas[i]) for i in top]
 
    def hybrid(self, query, k=CANDIDATES, allowed=None):
        """Reciprocal Rank Fusion of semantic + keyword results."""
        fused, items = {}, {}
        for results in (self.semantic(query, k, allowed),
                        self.keyword(query, k, allowed)):
            for rank, item in enumerate(results):
                fused[item["id"]] = fused.get(item["id"], 0) + 1 / (60 + rank + 1)
                items[item["id"]] = item
        order = sorted(fused, key=fused.get, reverse=True)[:k]
        return [items[i] for i in order]
 
    def rerank(self, query, candidates):
        if not candidates:
            return []
        scores = self.reranker.predict([(query, c["text"]) for c in candidates])
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked]
 
    def retrieve(self, query, mode="hybrid_rerank", k=TOP_K, allowed=None):
        if allowed is not None:
            allowed = set(allowed)
            if not allowed:
                return []
        if mode == "semantic":
            return self.semantic(query, k, allowed)
        candidates = self.hybrid(query, CANDIDATES, allowed)
        if mode == "hybrid":
            return candidates[:k]
        return self.rerank(query, candidates)[:k]
 