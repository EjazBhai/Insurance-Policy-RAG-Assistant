import json
import os

import requests
import streamlit as st

st.set_page_config(
    page_title="PolicyGuard AI",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ PolicyGuard AI")
st.caption("Insurance Policy RAG Assistant")
st.markdown(
    "Ask questions about insurance policies and review claim "
    "assessments grounded in retrieved policy evidence."
)

# Configuration: keep API keys in environment variables, not source code.
DEFAULT_API_URL = os.getenv("POLICY_API_URL", "http://localhost:8000")
DEFAULT_API_KEY = os.getenv("POLICY_API_KEY", "")

with st.sidebar:
    st.header("Connection")
    api_url = st.text_input("Backend URL", value=DEFAULT_API_URL).rstrip("/")
    api_key = st.text_input(
        "API key",
        value=DEFAULT_API_KEY,
        type="password",
        help="Sent to the backend as X-API-Key.",
    )
    st.caption("The backend enforces authentication and document permissions.")

def api_post(path: str, payload: dict) -> dict:
    headers = {"X-API-Key": api_key}
    response = requests.post(
        f"{api_url}{path}",
        json=payload,
        headers=headers,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()

def show_api_error(exc: Exception) -> None:
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        if exc.response.status_code in (401, 403):
            st.error("Authentication failed or access was denied. Check your API key and permissions.")
            return
        st.error(
            f"Backend returned HTTP {exc.response.status_code}: "
            f"{exc.response.text[:1000]}"
        )
        return
    if isinstance(exc, requests.RequestException):
        st.error(f"Could not connect to the backend: {exc}")
        return
    st.error(f"Unexpected error: {exc}")

def show_sources(sources: list) -> None:
    if not sources:
        st.info("No source citations were returned.")
        return

    st.subheader("Policy sources")
    for index, source in enumerate(sources, start=1):
        with st.expander(
            f"{index}. {source.get('file', 'Unknown file')} — "
            f"page {source.get('page', '?')}"
        ):
            st.write(source.get("snippet", "No excerpt provided."))

tab_qa, tab_claim = st.tabs(["💬 Policy Q&A", "📋 Claim assessment"])

with tab_qa:
    st.subheader("Ask your policy")
    question = st.text_area(
        "Question",
        placeholder="Example: What exclusions apply to hospitalisation?",
        max_chars=1000,
        height=110,
    )

    if st.button("Ask question", type="primary", key="ask_question"):
        if not api_url:
            st.warning("Enter the backend URL in the sidebar.")
        elif not api_key:
            st.warning("Enter your API key in the sidebar.")
        elif len(question.strip()) < 3:
            st.warning("Enter a question containing at least 3 characters.")
        else:
            try:
                with st.spinner("Searching policy evidence..."):
                    result = api_post("/ask", {"question": question.strip()})

                st.subheader("Answer")
                st.write(result.get("answer", "No answer returned."))
                show_sources(result.get("sources", []))

                with st.expander("Request details"):
                    st.write(f"User: {result.get('user', 'N/A')}")
                    st.write(f"Latency: {result.get('latency_ms', 'N/A')} ms")
                    st.write(f"Request ID: {result.get('request_id', 'N/A')}")
            except Exception as exc:
                show_api_error(exc)

with tab_claim:
    st.subheader("Assess an insurance claim")
    st.caption(
        "This is a preliminary evidence-based assessment, not a guarantee "
        "of coverage or payment."
    )

    with st.form("claim_form"):
        category = st.text_input(
            "Expense category",
            placeholder="e.g. Hospitalisation",
            max_chars=100,
        )
        description = st.text_area(
            "Expense description",
            placeholder="Describe the treatment or expense",
            max_chars=500,
        )
        amount = st.number_input(
            "Claim amount",
            min_value=0.0,
            value=10000.0,
            step=500.0,
        )
        payable = st.checkbox("Mark expense as payable for calculation", value=True)
        facts_complete = st.checkbox(
            "Required claim facts are complete",
            value=False,
            help="Only check this if you have verified the required facts.",
        )
        missing_text = st.text_input(
            "Missing information (optional)",
            placeholder="e.g. Waiting-period details, admission date",
        )
        submitted = st.form_submit_button("Assess claim", type="primary")

    if submitted:
        if not api_url:
            st.warning("Enter the backend URL in the sidebar.")
        elif not api_key:
            st.warning("Enter your API key in the sidebar.")
        elif not category.strip() or not description.strip():
            st.warning("Enter both an expense category and description.")
        else:
            payload = {
                "items": [
                    {
                        "category": category.strip(),
                        "description": description.strip(),
                        "amount": amount,
                        "payable": payable,
                    }
                ],
                "required_facts_complete": facts_complete,
                "missing_information": (
                    [item.strip() for item in missing_text.split(";") if item.strip()]
                ),
            }

            try:
                with st.spinner("Assessing claim against available policy evidence..."):
                    result = api_post("/claims/assess", payload)

                st.subheader("Assessment result")
                status = result.get("eligibility_status", "unknown")
                if status == "likely_covered":
                    st.success(f"Eligibility: {status}")
                elif status == "likely_excluded":
                    st.error(f"Eligibility: {status}")
                else:
                    st.warning(f"Eligibility: {status}")

                st.write("**Payout status:**", result.get("payout_status", "unknown"))

                reasons = result.get("reasons", [])
                if reasons:
                    st.write("**Reasons**")
                    for reason in reasons:
                        st.write(f"- {reason}")

                missing = result.get("missing_information", [])
                if missing:
                    st.write("**Missing information**")
                    for item in missing:
                        st.write(f"- {item}")

                evidence = result.get("evidence", [])
                if evidence:
                    st.write("**Evidence**")
                    st.json(evidence)

                estimate = result.get("estimate")
                if estimate is not None:
                    st.write("**Estimate**")
                    st.json(estimate)
                else:
                    st.info(
                        "No payout estimate was returned. The backend may require "
                        "verified policy terms or additional evidence."
                    )

                st.caption(f"Request ID: {result.get('request_id', 'N/A')}")
            except Exception as exc:
                show_api_error(exc)

with st.expander("About this application"):
    st.write(
        "The interface sends requests to your existing FastAPI backend. "
        "Eligibility and payout decisions are made by the backend, not by "
        "the frontend. Insufficient or conflicting policy evidence should "
        "be referred for human review."
    )