import os
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from src.config import (RAW_DATA_DIR, CHROMA_DIR, COLLECTION_NAME,
                        EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP)


def load_pdfs(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    pages = []
    for f in files:
        try:
            reader = PdfReader(os.path.join(folder, f))
            for i, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append({"text": text, "source": f, "page": i})
        except Exception as e:
            print(f"  Skipping {f}: {e}")
    return files, pages


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    step = size - overlap
    chunks = []
    for start in range(0, len(text), step):
        piece = text[start:start + size].strip()
        if len(piece) >= 50:
            chunks.append(piece)
    return chunks


def build_chunks(pages):
    chunks = []
    for p in pages:
        for i, piece in enumerate(chunk_text(p["text"])):
            chunks.append({
                "id": f"{p['source']}-p{p['page']}-c{i}",
                "text": piece,
                "source": p["source"],
                "page": p["page"],
            })
    return chunks


def main():
    files, pages = load_pdfs(RAW_DATA_DIR)
    print(f"Loaded {len(files)} PDFs, {len(pages)} pages")
    chunks = build_chunks(pages)
    print(f"Created {len(chunks)} chunks")

    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    col = client.get_or_create_collection(COLLECTION_NAME)

    batch = 64
    for i in range(0, len(chunks), batch):
        b = chunks[i:i + batch]
        embeddings = model.encode([c["text"] for c in b],
                                  normalize_embeddings=True).tolist()
        col.add(
            ids=[c["id"] for c in b],
            documents=[c["text"] for c in b],
            embeddings=embeddings,
            metadatas=[{"source": c["source"], "page": c["page"]} for c in b],
        )
        print(f"  embedded {min(i + batch, len(chunks))}/{len(chunks)}")
    print(f"Stored in {CHROMA_DIR}/")


if __name__ == "__main__":
    main()