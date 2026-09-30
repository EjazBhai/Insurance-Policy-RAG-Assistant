import json
import os
import time
from contextlib import asynccontextmanager
from typing import Optional
 
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
 
from src.generator import answer
from src.retriever import Retriever
 
USERS_PATH = os.getenv("USERS_PATH", "config/users.json")
state = {}
 
 
@asynccontextmanager
async def lifespan(app):
    state["retriever"] = Retriever()
    with open(USERS_PATH, encoding="utf-8") as f:
        state["users"] = json.load(f)
    yield
 
 
app = FastAPI(title="Policy RAG Assistant", lifespan=lifespan)
 
 
class Question(BaseModel):
    question: str
 
 
def current_user(x_user_id: Optional[str] = Header(default=None)):
    """Demo-level auth: the X-User-Id header selects a permission set.
    A real deployment would verify a signed token instead."""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    perms = state["users"].get(x_user_id)
    if perms is None:
        raise HTTPException(status_code=403, detail="Unknown user")
    allowed = None if "*" in perms else set(perms)
    return x_user_id, allowed
 
 
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
 
 
@app.post("/ask")
def ask(body: Question, user=Depends(current_user)):
    user_id, allowed = user
    start = time.time()
    chunks = state["retriever"].retrieve(body.question, allowed=allowed)
    result = answer(body.question, chunks)
    result["user"] = user_id
    result["latency_ms"] = int((time.time() - start) * 1000)
    return result
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
 