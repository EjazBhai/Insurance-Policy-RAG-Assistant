import re
import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from src.config import (CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL,
                        RERANK_MODEL, TOP_K, CANDIDATES)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class Retriever:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        ##self.reranker = None  # loaded only when needed
        self.reranker = CrossEncoder(RERANK_MODEL)
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.col = client.get_collection(COLLECTION_NAME)

        data = self.col.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.docs = data["documents"]
        self.metas = data["metadatas"]
        self.bm25 = BM25Okapi([tokenize(d) for d in self.docs])

    def _item(self, id_, text, meta):
        return {"id": id_, "text": text,
                "source": meta["source"], "page": meta["page"]}

    def semantic(self, query, k=TOP_K):
        emb = self.model.encode(QUERY_PREFIX + query,
                                normalize_embeddings=True).tolist()
        res = self.col.query(query_embeddings=[emb], n_results=k)
        return [self._item(i, d, m) for i, d, m in
                zip(res["ids"][0], res["documents"][0], res["metadatas"][0])]

    def keyword(self, query, k=TOP_K):
        scores = self.bm25.get_scores(tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self._item(self.ids[i], self.docs[i], self.metas[i]) for i in top]

    def hybrid(self, query, k=CANDIDATES):
        """Reciprocal Rank Fusion of semantic + keyword results."""
        fused, items = {}, {}
        for results in (self.semantic(query, k), self.keyword(query, k)):
            for rank, item in enumerate(results):
                fused[item["id"]] = fused.get(item["id"], 0) + 1 / (60 + rank + 1)
                items[item["id"]] = item
        order = sorted(fused, key=fused.get, reverse=True)[:k]
        return [items[i] for i in order]

    def rerank(self, query, candidates):
        if self.reranker is None:
            self.reranker = CrossEncoder(RERANK_MODEL)
        scores = self.reranker.predict([(query, c["text"]) for c in candidates])
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked]

    def retrieve(self, query, mode="hybrid_rerank", k=TOP_K):
        if mode == "semantic":
            return self.semantic(query, k)
        candidates = self.hybrid(query, CANDIDATES)
        if mode == "hybrid":
            return candidates[:k]
        return self.rerank(query, candidates)[:k]