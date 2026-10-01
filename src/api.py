import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator

from src.observability import log, log_event, setup_logging
from src.security import RateLimiter, User, UserStore

USERS_PATH = os.getenv("USERS_PATH", "config/users.json")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

    @field_validator("question")
    @classmethod
    def not_blank(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("question too short")
        return v


class Source(BaseModel):
    file: str
    page: int
    snippet: str


class Answer(BaseModel):
    answer: str
    sources: list[Source]
    user: str
    latency_ms: int
    request_id: str


def authenticate(request: Request, key: str | None = Depends(api_key_header)) -> User:
    if not key:
        raise HTTPException(401, "Missing API key", headers={"WWW-Authenticate": "ApiKey"})
    user = request.app.state.users.authenticate(key)
    if user is None:
        raise HTTPException(401, "Invalid API key", headers={"WWW-Authenticate": "ApiKey"})
    request.state.user = user.name
    return user


def create_app(retriever=None, users: UserStore | None = None,
               answer_fn=None, limiter: RateLimiter | None = None) -> FastAPI:
    setup_logging()

    @asynccontextmanager
    async def lifespan(app):
        if app.state.retriever is None:
            from src.retriever import Retriever  # heavy import, only at real startup
            app.state.retriever = Retriever()
        if app.state.users is None:
            app.state.users = UserStore.from_file(USERS_PATH)
        if app.state.answer_fn is None:
            from src.generator import answer
            app.state.answer_fn = answer
        log_event("startup complete")
        yield

    app = FastAPI(title="Policy RAG Assistant", version="1.0.0", lifespan=lifespan)
    app.state.retriever = retriever
    app.state.users = users
    app.state.answer_fn = answer_fn
    app.state.limiter = limiter or RateLimiter()

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error", extra={"fields": {"request_id": rid}})
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        response.headers["X-Request-ID"] = rid
        log_event("request", request_id=rid, method=request.method,
                  path=request.url.path, status=response.status_code,
                  latency_ms=int((time.perf_counter() - start) * 1000),
                  user=getattr(request.state, "user", None))
        return response

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        if app.state.retriever is None or app.state.users is None:
            raise HTTPException(503, "Not ready")
        return {"status": "ready"}

    @app.post("/ask", response_model=Answer)
    def ask(body: Question, request: Request, user: User = Depends(authenticate)):
        allowed, retry_after = app.state.limiter.check(user.name, user.rate_limit_per_min)
        if not allowed:
            raise HTTPException(429, "Rate limit exceeded",
                                headers={"Retry-After": str(retry_after)})

        start = time.perf_counter()
        try:
            chunks = app.state.retriever.retrieve(body.question, allowed=user.allowed)
        except Exception:
            log.exception("retrieval failed",
                          extra={"fields": {"request_id": request.state.request_id}})
            raise HTTPException(500, "Retrieval failed")
        t_retrieval = time.perf_counter()

        try:
            result = app.state.answer_fn(body.question, chunks)
        except Exception:
            log.exception("generation failed",
                          extra={"fields": {"request_id": request.state.request_id}})
            raise HTTPException(503, "Answer service temporarily unavailable")
        t_done = time.perf_counter()

        # Log metadata only, never the raw question text
        log_event("ask", request_id=request.state.request_id, user=user.name,
                  question_chars=len(body.question), chunks=len(chunks),
                  sources_returned=len(result["sources"]),
                  retrieval_ms=int((t_retrieval - start) * 1000),
                  generation_ms=int((t_done - t_retrieval) * 1000))

        return Answer(answer=result["answer"], sources=result["sources"],
                      user=user.name, latency_ms=int((t_done - start) * 1000),
                      request_id=request.state.request_id)

    return app


app = create_app()