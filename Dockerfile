FROM python:3.11-slim

# Hugging Face Spaces runs containers as UID 1000
RUN useradd -m -u 1000 user && mkdir -p /home/user/app && chown -R user:user /home/user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /home/user/app
USER user

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user src ./src
COPY --chown=user scripts ./scripts
COPY --chown=user config ./config

# Build the index inside the image, and cache the re-ranker model
RUN python scripts/download_pdfs.py && python -m src.ingest
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')" || exit 1
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "7860"]