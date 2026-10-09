from fastapi.testclient import TestClient

from src.api import create_app
from src.security import RateLimiter, UserStore, hash_key

NO_ANSWER = "No answer found in the provided policy documents."
DOCS = [
    {"id": "1", "text": "Dental treatment is excluded.", "source": "a.pdf", "page": 1},
    {"id": "2", "text": "Maternity has a waiting period.", "source": "b.pdf", "page": 2},
]


class FakeRetriever:
    def __init__(self):
        self.last_allowed = "unset"

    def retrieve(self, q, allowed=None, **kw):
        self.last_allowed = allowed
        return [d for d in DOCS if allowed is None or d["source"] in allowed]


def fake_answer(q, chunks):
    if not chunks:
        return {"answer": NO_ANSWER, "sources": []}
    return {"answer": "See [1].", "sources": [
        {"file": c["source"], "page": c["page"], "snippet": c["text"]} for c in chunks]}


def make_client(limit=20, answer_fn=fake_answer):
    users = UserStore({
        "admin": {"key_hash": hash_key("k-admin"), "sources": ["*"], "rate_limit_per_min": limit},
        "alice": {"key_hash": hash_key("k-alice"), "sources": ["a.pdf"], "rate_limit_per_min": limit},
        "guest": {"key_hash": hash_key("k-guest"), "sources": [], "rate_limit_per_min": limit},
    })
    retriever = FakeRetriever()
    app = create_app(retriever=retriever, users=users, answer_fn=answer_fn,
                     limiter=RateLimiter())
    return TestClient(app), retriever


def ask(client, key=None, q="Is dental covered?"):
    headers = {"X-API-Key": key} if key else {}
    return client.post("/ask", json={"question": q}, headers=headers)


def test_health_and_ready():
    c, _ = make_client()
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/ready").status_code == 200


def test_missing_key_is_401():
    c, _ = make_client()
    assert ask(c).status_code == 401


def test_wrong_key_is_401():
    c, _ = make_client()
    assert ask(c, "nope").status_code == 401


def test_valid_key_returns_answer_and_request_id():
    c, _ = make_client()
    r = ask(c, "k-admin")
    assert r.status_code == 200
    body = r.json()
    assert body["user"] == "admin" and len(body["sources"]) == 2
    assert r.headers["X-Request-ID"] == body["request_id"]


def test_user_only_sees_allowed_documents():
    c, retriever = make_client()
    body = ask(c, "k-alice").json()
    assert {s["file"] for s in body["sources"]} == {"a.pdf"}
    assert retriever.last_allowed == frozenset({"a.pdf"})


def test_guest_sees_nothing():
    c, _ = make_client()
    body = ask(c, "k-guest").json()
    assert body["answer"] == NO_ANSWER and body["sources"] == []


def test_validation_rejects_short_and_long_questions():
    c, _ = make_client()
    assert ask(c, "k-admin", q="hi").status_code == 422
    assert ask(c, "k-admin", q="x" * 1001).status_code == 422


def test_rate_limit_returns_429_with_retry_after():
    c, _ = make_client(limit=2)
    assert ask(c, "k-admin").status_code == 200
    assert ask(c, "k-admin").status_code == 200
    r = ask(c, "k-admin")
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert ask(c, "k-alice").status_code == 200  # limits are per user


def test_llm_failure_is_503_not_a_crash():
    def boom(q, chunks):
        raise RuntimeError("groq down")
    c, _ = make_client(answer_fn=boom)
    assert ask(c, "k-admin").status_code == 503



def test_claim_assessment_requires_api_key():
    c, _ = make_client()

    response = c.post(
        "/claims/assess",
        json={
            "items": [
                {
                    "category": "hospital",
                    "description": "Hospital charges",
                    "amount": 10000,
                    "payable": True,
                }
            ],
            "required_facts_complete": True,
        },
    )

    assert response.status_code == 401


def test_claim_assessment_requires_review_without_policy_evidence():
    c, _ = make_client()

    response = c.post(
        "/claims/assess",
        headers={"X-API-Key": "k-admin"},
        json={
            "items": [
                {
                    "category": "hospital",
                    "description": "Hospital charges",
                    "amount": 10000,
                    "payable": True,
                }
            ],
            "required_facts_complete": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["eligibility_status"] == "requires_review"
    assert body["payout_status"] == "not_estimated"
    assert body["estimate"] is None
    assert body["request_id"]


def test_claim_assessment_rejects_invalid_amount():
    c, _ = make_client()

    response = c.post(
        "/claims/assess",
        headers={"X-API-Key": "k-admin"},
        json={
            "items": [
                {
                    "category": "hospital",
                    "description": "Hospital charges",
                    "amount": -100,
                    "payable": True,
                }
            ],
            "required_facts_complete": True,
        },
    )

    assert response.status_code == 422


def test_claim_assessment_only_returns_authorized_policy_evidence():
    c, _ = make_client()

    response = c.post(
        "/claims/assess",
        headers={"X-API-Key": "k-alice"},
        json={
            "items": [
                {
                    "category": "hospital",
                    "description": "Hospital charges",
                    "amount": 10000,
                    "payable": True,
                }
            ],
            "required_facts_complete": True,
        },
    )

    assert response.status_code == 200

    body = response.json()
    evidence = body["evidence"]

    assert evidence
    assert {item["source"] for item in evidence} == {"a.pdf"}
    assert all(item["verified"] is False for item in evidence)
    assert body["payout_status"] == "not_estimated"
    assert body["estimate"] is None



def test_claim_assessment_with_no_document_access():
    c, _ = make_client()

    response = c.post(
        "/claims/assess",
        headers={"X-API-Key": "k-guest"},
        json={
            "items": [
                {
                    "category": "hospital",
                    "description": "Hospital charges",
                    "amount": 10000,
                    "payable": True,
                }
            ],
            "required_facts_complete": True,
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["eligibility_status"] == "requires_review"
    assert body["evidence"] == []
    assert body["payout_status"] == "not_estimated"
    assert body["estimate"] is None
